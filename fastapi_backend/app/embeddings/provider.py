"""
Embedding provider abstraction for the RAG pipeline.

Supports multiple embedding providers (SentenceTransformers, Google Gemini, OpenAI, etc.)
with caching, batching, and retry logic.
"""

import hashlib
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings
from app.core.logging import logger

_RETRY_HINT_RE = re.compile(r"retry in\s+([\d.]+)\s*s", re.IGNORECASE)
_QUERY_TIMEOUT_S = 30.0
_DOC_TIMEOUT_S = 60.0
_QUERY_DEADLINE_S = 30.0
_DOC_DEADLINE_S = 120.0
_MAX_RETRY_SLEEP = 60.0


def _retry_delay(exc: Exception, attempt: int, base_delay: float) -> float:
    """Compute retry sleep, honoring the provider's suggested wait when present.

    The suggested wait is capped so a single backoff can never stall the
    request (or the event loop) for minutes.
    """
    delay = base_delay * (2**attempt)
    server_delay = getattr(exc, "retry_delay", None)
    if server_delay is not None:
        delay = max(delay, server_delay.total_seconds())
    match = _RETRY_HINT_RE.search(str(exc))
    if match:
        delay = max(delay, float(match.group(1)))
    return min(delay, _MAX_RETRY_SLEEP)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding provider."""

    model_name: str = "text-embedding-004"
    dimension: int = 768
    batch_size: int = 32
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_enabled: bool = True
    cache_size: int = 10000
    normalize: bool = True


@dataclass
class EmbeddingResult:
    """Result of embedding operation."""

    embeddings: list[list[float]]
    model: str
    dimension: int
    tokens_used: int = 0
    duration_ms: float = 0.0


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: EmbeddingConfig | None = None):
        self.config = config or EmbeddingConfig()

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        """Embed a list of documents/texts."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass


class SentenceTransformersProvider(EmbeddingProvider):
    """Embedding provider using SentenceTransformers (local models)."""

    def __init__(self, config: EmbeddingConfig | None = None):
        super().__init__(config)
        self._model = None
        self._cache = {}

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.config.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        start_time = time.time()
        model = self._get_model()

        if self.config.cache_enabled:
            cached_embeddings = {}
            uncached_texts = []
            uncached_indices = []

            for i, text in enumerate(texts):
                cache_key = self._cache_key(text)
                if cache_key in self._cache:
                    cached_embeddings[i] = self._cache[cache_key]
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))

        if uncached_texts:
            new_embeddings = model.encode(
                uncached_texts,
                batch_size=self.config.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=self.config.normalize,
            )
            new_embeddings = new_embeddings.tolist()

            if self.config.cache_enabled:
                for idx, embedding in zip(uncached_indices, new_embeddings, strict=True):
                    cache_key = self._cache_key(texts[idx])
                    self._cache[cache_key] = embedding
        else:
            new_embeddings = []

        all_embeddings = [None] * len(texts)
        for i, emb in cached_embeddings.items():
            all_embeddings[i] = emb
        for idx, emb in zip(uncached_indices, new_embeddings, strict=True):
            all_embeddings[idx] = emb

        duration_ms = (time.time() - start_time) * 1000

        return EmbeddingResult(
            embeddings=all_embeddings,
            model=self.config.model_name,
            dimension=self.dimension,
            duration_ms=duration_ms,
        )

    def embed_query(self, text: str) -> list[float]:
        result = self.embed_documents([text])
        return result.embeddings[0]

    @property
    def dimension(self) -> int:
        model = self._get_model()
        return model.get_sentence_embedding_dimension()

    @property
    def model_name(self) -> str:
        return self.config.model_name

    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:32]


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Google Gemini API."""

    def __init__(self, config: EmbeddingConfig | None = None):
        super().__init__(config)
        self._client = None
        self._api_key = settings.GEMINI_API_KEY

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai

            if not self._api_key:
                raise ValueError("GEMINI_API_KEY not set in environment")
            genai.configure(api_key=self._api_key)
            self._client = genai
        return self._client

    def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        start_time = time.time()
        deadline = start_time + _DOC_DEADLINE_S
        client = self._get_client()

        total_batches = (len(texts) + self.config.batch_size - 1) // self.config.batch_size
        all_embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            batch_no = i // self.config.batch_size + 1
            for attempt in range(self.config.max_retries):
                try:
                    result = client.embed_content(
                        model=f"models/{self.config.model_name}",
                        content=batch,
                        task_type="retrieval_document",
                        output_dimensionality=self.config.dimension,
                        request_options={"timeout": _DOC_TIMEOUT_S},
                    )
                    all_embeddings.extend(result["embedding"])
                    if batch_no == 1 or batch_no % 10 == 0 or batch_no == total_batches:
                        logger.info(
                            f"Embedding progress: batch {batch_no}/{total_batches} "
                            f"({min(i + self.config.batch_size, len(texts))}/{len(texts)} texts)"
                        )
                    break
                except Exception as e:
                    if attempt == self.config.max_retries - 1:
                        raise
                    delay = _retry_delay(e, attempt, self.config.retry_delay)
                    if time.time() + delay > deadline:
                        logger.warning("Embedding deadline exceeded, aborting retries")
                        raise
                    logger.warning(
                        f"Embedding batch {batch_no}/{total_batches} failed ({e}); "
                        f"retrying in {delay:.0f}s (attempt {attempt + 1})"
                    )
                    time.sleep(delay)

        duration_ms = (time.time() - start_time) * 1000

        return EmbeddingResult(
            embeddings=all_embeddings,
            model=self.config.model_name,
            dimension=self.dimension,
            duration_ms=duration_ms,
        )

    def embed_query(self, text: str) -> list[float]:
        client = self._get_client()
        deadline = time.time() + _QUERY_DEADLINE_S

        for attempt in range(self.config.max_retries):
            try:
                result = client.embed_content(
                    model=f"models/{self.config.model_name}",
                    content=text,
                    task_type="retrieval_query",
                    output_dimensionality=self.config.dimension,
                    request_options={"timeout": _QUERY_TIMEOUT_S},
                )
                return result["embedding"]
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise
                delay = _retry_delay(e, attempt, self.config.retry_delay)
                if time.time() + delay > deadline:
                    logger.warning("Query embedding deadline exceeded, aborting retries")
                    raise
                logger.warning(f"Query embedding failed ({e}); retrying in {delay:.0f}s")
                time.sleep(delay)

    @property
    def dimension(self) -> int:
        return self.config.dimension

    @property
    def model_name(self) -> str:
        return self.config.model_name


class EmbeddingProviderFactory:
    """Factory for creating embedding providers."""

    PROVIDERS = {
        "sentence-transformers": SentenceTransformersProvider,
        "gemini": GeminiEmbeddingProvider,
    }

    @classmethod
    def create(cls, provider_name: str, config: EmbeddingConfig | None = None) -> EmbeddingProvider:
        if provider_name not in cls.PROVIDERS:
            raise ValueError(
                f"Unknown embedding provider: {provider_name}. Available: {list(cls.PROVIDERS.keys())}"  # noqa: E501
            )
        return cls.PROVIDERS[provider_name](config)

    @classmethod
    def register(cls, name: str, provider_class: type[EmbeddingProvider]):
        cls.PROVIDERS[name] = provider_class


def get_embedding_provider(
    provider_name: str | None = None,
    config: EmbeddingConfig | None = None,
) -> EmbeddingProvider:
    """Get embedding provider from environment or explicit config."""
    if provider_name is None:
        provider_name = settings.EMBEDDING_PROVIDER

    if config is None:
        config = EmbeddingConfig(
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )

    return EmbeddingProviderFactory.create(provider_name, config)


@lru_cache(maxsize=1)
def get_cached_embedding_provider() -> EmbeddingProvider:
    """Get singleton cached embedding provider."""
    return get_embedding_provider()
