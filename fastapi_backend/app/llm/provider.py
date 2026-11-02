"""
LLM provider abstraction for the RAG pipeline.

Supports Google Gemini with structured output generation for incident analysis.
Falls back to mock provider for development when Gemini is unavailable.
"""

import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.rag.models import QueryUnderstanding, RAGContext


class LLMProviderType(StrEnum):
    """Supported LLM providers."""

    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    model_name: str = "gemini-1.5-flash"
    temperature: float = 0.1
    max_output_tokens: int = 8192
    top_p: float = 0.95
    top_k: int = 40
    system_prompt: str | None = None


@dataclass
class LLMResponse:
    """Response from LLM generation."""

    content: str
    model: str
    tokens_used: int = 0
    duration_ms: float = 0.0
    finish_reason: str = "unknown"


_ALLOWED_SOURCES = {"github", "confluence", "pagerduty", "manual", "logs", "analysis"}
_ALLOWED_STATUSES = {"resolved", "mitigated", "open", "investigating"}
_ALLOWED_SEVERITIES = {"P0", "P1", "P2", "P3"}
_ALLOWED_RISKS = {"Critical", "High", "Medium", "Low"}
_ALLOWED_CONFIDENCE = {"High", "Medium", "Low", "Insufficient Evidence"}
_LLM_TIMEOUT_S = 60.0


def _normalize_str(value: Any, allowed: set[str] | None, default: str) -> str:
    """Return a cleaned string, matched case-insensitively against allowed values."""
    if not isinstance(value, str):
        return default
    candidate = value.strip()
    if not candidate:
        return default
    if allowed is not None:
        for allowed_value in allowed:
            if allowed_value.lower() == candidate.lower():
                return allowed_value
        return default
    return candidate


_STOPWORDS = {
    "the", "and", "for", "why", "did", "does", "what", "how", "was", "were", "with",
    "this", "that", "from", "have", "has", "had", "are", "you", "can", "should", "would",
    "could", "about", "into", "over", "under", "there", "their", "them", "then", "than",
    "when", "where", "which", "while", "please", "show", "give", "tell", "any", "all",
    "me", "my", "our", "its", "not", "but", "out", "get", "got", "fix", "issue", "issues",
}

_LEVEL_RE = re.compile(r"\b(ERROR|FATAL|CRITICAL|WARN(?:ING)?|INFO|DEBUG|TRACE)\b", re.I)
_PREFIX_RE = re.compile(r"^\[[^\]]*\]\s*service=.*?\s*level=(\S+)\s+(.*)$", re.I)
_WINDOW_RE = re.compile(r"^Service:.*?Log count:\s*\d+\.\s*(.*)$", re.I)
_TRUNCATED_HEADER_RE = re.compile(r"^\[[^\]]*\]\s*service=\S+", re.I)
_FAILURE_WORD_RE = re.compile(
    r"\b(fail(?:ed|ure|ing)?|error|exception|cannot|unable|denied|refused|timeout|timed out|invalid)\b",
    re.I,
)
_CONFIG_LINE_RE = re.compile(r"^[\w.\-]+\s*[:=]\s*\S+$")
_NON_LOG_LABEL_RE = re.compile(r"^(?:service node|graph (?:node|relationship)|relationship)\b", re.I)
_TS_RE = re.compile(r"^\[([^\]]+)\]")

_SIGNATURE_RULES: dict[str, dict[str, Any]] = {
    "connectivity failure": {
        "keywords": [
            "connection refused", "retrying connect", "error in contacting", "connect to server",
            "connection reset", "no route to host", "failed to connect", "broken pipe",
            "connection error", "error contacting rm",
        ],
        "explanation": (
            "Repeated connection attempts to a required endpoint (ResourceManager, NameNode, "
            "or a remote service) failed, so work could not be scheduled or completed."
        ),
        "fixes": [
            "Confirm the target endpoint (host and port) is reachable from the failing node (ping/telnet/nc).",
            "Check the ResourceManager/NameNode/master service health and logs for restarts or overload.",
            "Review firewall, security-group, DNS and hosts configuration between the worker and the endpoint.",
            "Tune IPC retry/timeout settings (e.g. ipc.client.connect.max.retries, socket timeouts) if failures are transient.",
            "Re-run the workload after connectivity is restored and verify no failed containers remain.",
        ],
    },
    "scheduler/container allocation failure": {
        "keywords": [
            "container allocator", "could not allocate", "no available resources", "insufficient resources",
            "rmcontainerallocator", "allocation", "container allocation", "resource manager",
            "not enough resources", "queue",
        ],
        "explanation": (
            "The scheduler could not allocate containers for the job, typically due to insufficient "
            "cluster resources, queue limits, or an unavailable/overloaded ResourceManager."
        ),
        "fixes": [
            "Inspect YARN queue capacity and cluster resource usage during the incident window.",
            "Check ResourceManager and NodeManager logs for container allocation errors.",
            "Increase queue capacity or reduce concurrent demand, then resubmit the job.",
            "Verify NodeManager health and that nodes are not marked unhealthy or decommissioned.",
            "Review scheduler (capacity/fair) configuration for restrictive limits.",
        ],
    },
    "HDFS lease/NameNode warning": {
        "keywords": ["leaserenewer", "lease renewal", "lease expired", "lease", "namenode", "hdfs"],
        "explanation": (
            "The HDFS lease renewal path reported warnings, which can stall writes and leave "
            "files under construction if the NameNode or client connection is unhealthy."
        ),
        "fixes": [
            "Check NameNode health, load and logs for lease-related warnings.",
            "Verify network connectivity between the client and NameNode.",
            "Ensure the client is not pausing lease renewals (long GC pauses, blocked threads).",
            "Review dfs.client.socket-timeout and lease renewal intervals.",
            "If files are stuck under construction, use hdfs debug recoverLease after confirming safety.",
        ],
    },
    "operation timeout": {
        "keywords": ["timed out", "timeout", "deadline exceeded", "socket timeout", "retry policy"],
        "explanation": (
            "An operation exceeded its configured deadline, indicating a slow or unresponsive "
            "downstream dependency."
        ),
        "fixes": [
            "Identify the dependency that is responding slowly and check its health and latency.",
            "Review timeout/retry settings and confirm they match the service SLO.",
            "Look for resource saturation (CPU, memory, disk I/O, GC pauses) on the dependency.",
            "Add or tune circuit breakers and backoff to avoid cascading retries.",
            "Re-test after remediation and compare latency to the baseline.",
        ],
    },
    "memory exhaustion": {
        "keywords": ["outofmemory", "out of memory", "gc overhead", "heap space", "memory error"],
        "explanation": "A process exhausted its available heap, causing the task or JVM to fail.",
        "fixes": [
            "Increase heap/container memory for the affected component within cluster limits.",
            "Analyse heap dumps and GC logs to locate the leak or oversized working set.",
            "Reduce batch/partition sizes or increase parallelism to lower per-task memory.",
            "Review recent code/config changes that increased memory usage.",
            "Add memory-usage alerting to catch growth before OOM.",
        ],
    },
    "disk/I/O failure": {
        "keywords": ["no space left", "disk full", "disk failure", "ioexception", "input/output error", "read-only file system"],
        "explanation": "A node ran out of disk space or hit an I/O error, preventing normal operation.",
        "fixes": [
            "Check disk usage on the affected node and free or expand capacity.",
            "Inspect system logs (dmesg) for hardware or filesystem errors.",
            "Verify data directories are writable and not mounted read-only.",
            "Move data to healthy nodes / decommission failing disks.",
            "Add disk-space alerting and log-rotation policies.",
        ],
    },
    "Windows servicing (CBS/CSI) error": {
        "keywords": ["cbs", "csi", "servicing", "component store", "windows update", "corrupt", "repair"],
        "explanation": (
            "The Windows servicing stack (CBS/CSI) reported component-store or update errors, "
            "which can leave the component store inconsistent."
        ),
        "fixes": [
            "Run DISM /Online /Cleanup-Image /ScanHealth and /RestoreHealth.",
            "Run sfc /scannow to repair protected system files.",
            "Review CBS.log/CSI.log for the specific component or package that failed.",
            "Free space on the system drive (servicing requires headroom).",
            "Re-apply the failed update after repairing the component store.",
        ],
    },
    "authentication/authorization failure": {
        "keywords": ["authentication", "unauthorized", "forbidden", "permission denied", "access denied", "401", "403"],
        "explanation": "A request was rejected because authentication or authorization failed.",
        "fixes": [
            "Verify credentials, tokens and certificates used by the affected service.",
            "Check role/ACL assignments and recent permission changes.",
            "Confirm clock skew is within tolerance for token validation.",
            "Review authentication service availability and logs.",
            "Rotate or re-issue credentials if they expired or were revoked.",
        ],
    },
    "DNS/name resolution failure": {
        "keywords": ["name or service not known", "unknown host", "dns", "resolve host", "temporary failure in name resolution"],
        "explanation": "Hostname resolution failed for a required dependency.",
        "fixes": [
            "Verify DNS servers and resolver configuration on the affected host.",
            "Confirm the target hostname resolves correctly (nslookup/dig).",
            "Check /etc/hosts (or Windows hosts file) for stale or conflicting entries.",
            "Review DNS service health and recent record changes.",
            "Add retries/fallbacks for transient resolution failures.",
        ],
    },
    "database contention": {
        "keywords": ["deadlock", "lock wait", "replication lag", "connection pool", "too many connections"],
        "explanation": "The database connection pool or locking path was saturated or blocked.",
        "fixes": [
            "Inspect slow queries and lock waits during the incident window.",
            "Increase pool size or reduce long-held transactions as appropriate.",
            "Check replication lag and database server resource saturation.",
            "Review recent schema/index or query changes.",
            "Add monitoring for pool saturation and lock contention.",
        ],
    },
}


def _query_tokens(query: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", query.lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _iter_log_lines(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten evidence chunks into individual, cleaned log lines."""
    lines: list[dict[str, Any]] = []
    for ev in evidence:
        content = (ev.get("content") or "").strip()
        if not content:
            continue
        if _NON_LOG_LABEL_RE.match(content):
            continue
        meta = ev.get("metadata") or {}
        raw_parts = [p.strip() for p in re.split(r"\s\|\s|\n", content) if p.strip()]
        parts: list[tuple[str, bool]] = []
        for part in raw_parts:
            window_match = _WINDOW_RE.match(part)
            if window_match:
                parts.extend(
                    (p.strip(), True)
                    for p in re.split(r"\s{2,}", window_match.group(1))
                    if p.strip()
                )
            else:
                parts.append((part, False))

        for part, from_window in parts:
            level = None
            timestamp = None
            prefix_match = _PREFIX_RE.match(part)
            if prefix_match:
                level = prefix_match.group(1).upper()
                ts_match = _TS_RE.match(part)
                timestamp = ts_match.group(1) if ts_match else None
                line = prefix_match.group(2).strip()
            elif _TRUNCATED_HEADER_RE.match(part):
                continue
            else:
                level_match = _LEVEL_RE.search(part)
                level = level_match.group(1).upper() if level_match else None
                line = part
            if not level:
                level = (meta.get("level") or meta.get("severity") or "").upper() or None
            lines.append(
                {
                    "line": line[:500],
                    "level": level,
                    "service": meta.get("service"),
                    "timestamp": timestamp or meta.get("timestamp"),
                    "source": ev.get("source"),
                    "from_window": from_window,
                }
            )
    return lines


def _rank_log_lines(
    evidence: list[dict[str, Any]],
    query: str,
    signature_keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    tokens = _query_tokens(query)
    sig_tokens = [k.lower() for k in (signature_keywords or []) if k]
    seen: set[str] = set()
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in _iter_log_lines(evidence):
        key = item["line"][:120].lower()
        if not key or key in seen:
            continue
        seen.add(key)
        text = item["line"].lower()
        score = sum(1 for token in tokens if token in text)
        if sig_tokens:
            score += 2 * sum(1 for token in sig_tokens if token in text)
        if _FAILURE_WORD_RE.search(text):
            score += 2
        if _CONFIG_LINE_RE.match(item["line"].strip()):
            score -= 2
        if item["level"] in {"ERROR", "FATAL", "CRITICAL"}:
            score += 3
        elif item["level"] in {"WARN", "WARNING"}:
            score += 1
        if item.get("from_window"):
            score -= 2
        scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


def _detect_signature(text: str) -> tuple[str | None, int]:
    low = text.lower()
    best_label: str | None = None
    best_hits = 0
    for label, rule in _SIGNATURE_RULES.items():
        hits = sum(low.count(keyword) for keyword in rule["keywords"])
        if hits > best_hits:
            best_label, best_hits = label, hits
    return best_label, best_hits


def _ground_analysis_response(
    data: dict[str, Any],
    query: str,
    understanding: QueryUnderstanding,
    evidence: list[dict[str, Any]],
    graph_relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge an LLM analysis with server-verified retrieval data.

    The LLM writes the narrative fields (title, root cause, timeline, ...).
    Evidence-derived fields (incident_id, evidence, sources,
    graph_relationships) are always rebuilt from the actual retrieval
    results so the API can never cite fabricated sources or chunks.
    """
    services = understanding.entities.services or ["unknown-service"]
    errors = understanding.entities.errors or ["unknown-error"]

    # Derive services / severity signals from the actual retrieved evidence so the
    # grounded fallback is specific instead of generic.
    ev_services: list[str] = []
    ev_levels: dict[str, int] = {}
    for _ev in evidence:
        _meta = _ev.get("metadata") or {}
        _svc = _meta.get("service")
        if _svc and _svc != "unknown" and _svc not in ev_services:
            ev_services.append(_svc)
        _lvl = _meta.get("level") or _meta.get("severity")
        if _lvl:
            ev_levels[_lvl] = ev_levels.get(_lvl, 0) + 1

    if understanding.entities.services:
        services = understanding.entities.services
    elif ev_services:
        services = ev_services

    if understanding.entities.errors:
        errors = understanding.entities.errors
    else:
        _error_levels = [lvl for lvl in ev_levels if lvl in {"ERROR", "CRITICAL", "FATAL"}]
        errors = _error_levels or ["unknown-error"]

    evidence_text = " ".join(str(ev.get("content") or "") for ev in evidence)
    combined_text = evidence_text
    signature_label, _signature_hits = _detect_signature(combined_text + " " + query)
    signature_keywords = (
        _SIGNATURE_RULES.get(signature_label, {}).get("keywords", []) if signature_label else []
    )

    ranked_lines = _rank_log_lines(evidence, query, signature_keywords)

    def _is_strong(item: dict[str, Any]) -> bool:
        text = item["line"].lower()
        return (
            item["level"] in {"ERROR", "FATAL", "CRITICAL", "WARN", "WARNING"}
            or bool(_FAILURE_WORD_RE.search(text))
            or any(k in text for k in signature_keywords)
        )

    strong_lines = [item for item in ranked_lines if _is_strong(item)]
    primary = strong_lines[0] if strong_lines else None
    error_lines = [
        item
        for item in ranked_lines
        if item["level"] in {"ERROR", "FATAL", "CRITICAL", "WARN", "WARNING"}
    ]
    matched_lines = (error_lines or ranked_lines)[:6]

    signature_rule = _SIGNATURE_RULES.get(signature_label) if signature_label else None
    signature_phrase = signature_label or "the observed failure"

    primary_service = (
        (understanding.entities.services[0] if understanding.entities.services else None)
        or (primary.get("service") if primary and primary.get("service") else None)
        or (services[0] if services else "the affected service")
    )
    primary_line = primary["line"] if primary else ""
    primary_timestamp = (
        str(primary.get("timestamp")) if primary and primary.get("timestamp") else ""
    )
    evidence_services = ", ".join(services[:4])

    sources = [
        {
            "source_file": e.get("metadata", {}).get("source_file") or e.get("source", "unknown"),
            "chunk_id": e.get("chunk_id", "unknown"),
            "retrieval_score": e.get("score", 0),
            "source_type": e.get("type", "unknown"),
            "service": e.get("metadata", {}).get("service", "unknown"),
            "timestamp": e.get("metadata", {}).get("timestamp", "unknown"),
        }
        for e in evidence[:20]
    ]

    # Real timestamps from the matched logs (not the current time).
    observed_timestamps = sorted(
        {
            str(item["timestamp"])
            for item in matched_lines
            if item.get("timestamp") and len(str(item["timestamp"])) >= 10
        }
    )

    timeline = data.get("timeline")
    if isinstance(timeline, list):
        timeline = [
            t for t in timeline if isinstance(t, dict) and t.get("timestamp") and t.get("event")
        ]
    if not timeline:
        timeline = []
        if observed_timestamps:
            timeline.append(
                {
                    "timestamp": observed_timestamps[0],
                    "event": f"Earliest matching log entry for {primary_service}",
                    "actor": "logs",
                }
            )
        if primary_timestamp and primary_line:
            timeline.append(
                {
                    "timestamp": primary_timestamp,
                    "event": f"Primary failure signature: {primary_line[:140]}",
                    "actor": primary_service,
                }
            )
        if observed_timestamps and observed_timestamps[-1] != observed_timestamps[0]:
            timeline.append(
                {
                    "timestamp": observed_timestamps[-1],
                    "event": f"Most recent matching log entry for {primary_service}",
                    "actor": "logs",
                }
            )
        if not timeline:
            now = datetime.now(UTC).isoformat(timespec="seconds")
            timeline = [
                {
                    "timestamp": now,
                    "event": f"Analysis requested: {query[:100]}",
                    "actor": "user",
                },
                {
                    "timestamp": now,
                    "event": "No timestamped log matches were found",
                    "actor": "rag-system",
                },
            ]

    fixes = (
        signature_rule["fixes"]
        if signature_rule
        else [
            f"Inspect {primary_service} logs around the incident window for the root trigger.",
            "Check the health and saturation of upstream dependencies.",
            "Review recent deployments and configuration changes.",
            "Compare with similar historical incidents in the knowledge base.",
            "Apply the validated fix and monitor for recurrence.",
        ]
    )

    if not evidence:
        root_cause_default = (
            "Insufficient evidence found in the indexed knowledge base for this query."
        )
        impact_default = "Unable to determine impact: no matching logs or graph nodes were retrieved."
        resolution_default = (
            "No remediation can be derived without matching evidence. Ingest the relevant logs "
            "or broaden the query, then re-run the analysis."
        )
        potential_default = "Under investigation — no supporting evidence retrieved."
    elif primary:
        root_cause_default = (
            f"{primary_service} failed"
            + (f" at {primary_timestamp}" if primary_timestamp else "")
            + f": {primary_line}. "
            + (f"{signature_rule['explanation']} " if signature_rule else "")
            + f"This is corroborated by {len(matched_lines)} matching log entries across "
            f"{len(sources)} cited sources."
        )
        error_count = sum(
            1 for item in matched_lines if item["level"] in {"ERROR", "FATAL", "CRITICAL"}
        )
        impact_default = (
            f"{primary_service} was impacted during "
            f"{observed_timestamps[0] if observed_timestamps else 'the incident window'}"
            + (f" to {observed_timestamps[-1]}" if len(observed_timestamps) > 1 else "")
            + f". {error_count} error-level and {len(matched_lines) - error_count} warning/other "
            f"matching entries were retrieved across {evidence_services}."
        )
        resolution_default = (
            f"Recommended remediation for {primary_service} ({signature_phrase}):\n"
            + "\n".join(f"{i}. {step}" for i, step in enumerate(fixes, 1))
        )
        potential_default = (
            f"Most likely {signature_phrase} in {primary_service}: {primary_line[:200]}"
            if signature_rule
            else f"Most likely failure in {primary_service}, evidenced by: {primary_line[:200]}"
        )
    else:
        if signature_rule:
            root_cause_default = (
                f"{primary_service} most likely experienced a {signature_phrase}. "
                f"{signature_rule['explanation']} "
                f"Retrieved {len(evidence)} evidence items across {evidence_services}, but none "
                "contained an explicit failure line; review the evidence section for the closest "
                "matches."
            )
            resolution_default = (
                f"Recommended remediation for {primary_service} ({signature_phrase}):\n"
                + "\n".join(f"{i}. {step}" for i, step in enumerate(fixes, 1))
            )
            potential_default = f"Most likely {signature_phrase} in {primary_service}."
        else:
            root_cause_default = (
                f"Retrieved {len(evidence)} evidence items for {evidence_services}, but none "
                "contained a clear failure line. Review the evidence section for the closest matches."
            )
            resolution_default = (
                "1. Inspect the retrieved evidence for the earliest anomaly.\n"
                "2. Correlate with service health and recent changes.\n"
                "3. Re-run the query with a more specific error or service name."
            )
            potential_default = f"Likely related to {evidence_services}."
        impact_default = f"Service(s) {evidence_services} matched the query; impact is unconfirmed."

    signature_keywords = (
        ", ".join(signature_rule["keywords"][:3])
        if signature_rule
        else (errors[0] if errors else "errors")
    )

    lessons_learned = data.get("lessons_learned")
    if not isinstance(lessons_learned, list) or not lessons_learned:
        if evidence:
            lessons_learned = [
                f"Add proactive alerting for {signature_phrase} in {primary_service} "
                f"(watch for {signature_keywords}).",
                f"Document and rehearse a recovery runbook for {primary_service} "
                "covering this failure mode.",
                f"Capture the '{primary_line[:80]}' signature and link it to historical incidents "
                "for faster matching.",
                f"Review retry/timeout and capacity configuration for {primary_service} "
                "to prevent recurrence.",
            ]
        else:
            lessons_learned = ["Insufficient historical data for lessons learned"]

    log_snippets = data.get("log_snippets")
    if not isinstance(log_snippets, list) or not log_snippets:
        log_snippets = [item["line"][:240] for item in matched_lines]

    tags = data.get("tags")
    if not isinstance(tags, list):
        tags = list(
            dict.fromkeys(
                services
                + ([signature_label] if signature_label else [])
                + errors
                + [understanding.intent.value]
            )
        )

    recommended_investigation = data.get("recommended_investigation")
    if not isinstance(recommended_investigation, list) or not recommended_investigation:
        if primary:
            recommended_investigation = [
                f"Inspect {primary_service} logs around "
                f"{observed_timestamps[0] if observed_timestamps else 'the incident window'} "
                f"for '{signature_keywords}'.",
                f"Validate the proposed remediation steps for {primary_service} ({signature_phrase}).",
                f"Check the health of related services: {evidence_services}.",
                f"Compare against {len(sources)} cited historical log matches to confirm the pattern.",
                "Confirm recovery and record the verified fix for future retrieval.",
            ]
        else:
            recommended_investigation = [
                "Broaden the query with a service name, error text, or timestamp.",
                "Ingest the relevant log files for the incident window.",
                "Review the vector and graph stores for available services.",
            ]

    if not evidence:
        default_confidence = "Insufficient Evidence"
    elif signature_rule and len(matched_lines) >= 4:
        default_confidence = "High"
    else:
        default_confidence = "Medium"

    return {
        "incident_id": str(uuid.uuid4()),
        "title": _normalize_str(
            data.get("title"), None, f"{primary_service}: {signature_phrase}"
        ),
        "source": _normalize_str(data.get("source"), _ALLOWED_SOURCES, "analysis"),
        "source_url": data.get("source_url") if isinstance(data.get("source_url"), str) else None,
        "severity": _normalize_str(
            data.get("severity"),
            _ALLOWED_SEVERITIES,
            understanding.entities.severity or "P2",
        ),
        "status": _normalize_str(data.get("status"), _ALLOWED_STATUSES, "investigating"),
        "service": _normalize_str(data.get("service"), None, services[0]),
        "team": _normalize_str(data.get("team"), None, "platform-engineering"),
        "timeline": timeline,
        "root_cause": _normalize_str(
            data.get("root_cause"),
            None,
            root_cause_default,
        ),
        "impact": _normalize_str(
            data.get("impact"),
            None,
            impact_default,
        ),
        "resolution": _normalize_str(
            data.get("resolution"), None, resolution_default
        ),
        "lessons_learned": lessons_learned,
        "log_snippets": log_snippets,
        "tags": tags,
        "created_at": _normalize_str(
            data.get("created_at"),
            None,
            datetime.now(UTC).isoformat(timespec="seconds"),
        ),
        "resolved_at": (
            data.get("resolved_at") if isinstance(data.get("resolved_at"), str) else None
        ),
        "raw_content": _normalize_str(
            data.get("raw_content"),
            None,
            f"Analysis generated from {len(evidence)} retrieved evidence items for query: {query}",
        ),
        "evidence": evidence[:20],
        "graph_relationships": graph_relationships[:20],
        "recommended_investigation": recommended_investigation,
        "potential_root_cause": _normalize_str(
            data.get("potential_root_cause"),
            None,
            potential_default,
        ),
        "risk_severity": _normalize_str(data.get("risk_severity"), _ALLOWED_RISKS, "Medium"),
        "confidence": _normalize_str(
            data.get("confidence"), _ALLOWED_CONFIDENCE, default_confidence
        ),
        "sources": sources,
    }


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate text from prompt."""
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema: dict[str, Any], **kwargs) -> dict[str, Any]:
        """Generate structured output matching schema."""
        pass

    @abstractmethod
    def generate_incident_analysis(
        self,
        query: str,
        understanding: QueryUnderstanding,
        evidence: list[dict[str, Any]],
        graph_relationships: list[dict[str, Any]],
        context: RAGContext,
    ) -> dict[str, Any]:
        """Generate incident analysis response."""
        pass


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for development and testing."""

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        return LLMResponse(
            content="Mock response for development",
            model="mock",
            duration_ms=10.0,
        )

    def generate_structured(self, prompt: str, schema: dict[str, Any], **kwargs) -> dict[str, Any]:
        return self.generate_incident_analysis(
            query="mock query",
            understanding=QueryUnderstanding(original_query="mock"),
            evidence=[],
            graph_relationships=[],
            context=RAGContext(
                vector_results=None,
                graph_results=[],
                query_understanding=QueryUnderstanding(original_query="mock"),
            ),
        )

    def generate_incident_analysis(
        self,
        query: str,
        understanding: QueryUnderstanding,
        evidence: list[dict[str, Any]],
        graph_relationships: list[dict[str, Any]],
        context: RAGContext,
    ) -> dict[str, Any]:
        """Generate a mock incident analysis for development."""
        return _ground_analysis_response({}, query, understanding, evidence, graph_relationships)


# Try to import Gemini, fall back to mock if unavailable
_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig

    _GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("google-generativeai not available, using mock provider")
    genai = None
    GenerationConfig = None


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, config: LLMConfig | None = None):
        super().__init__(config)
        self._model = None
        self._api_key = settings.GEMINI_API_KEY

    def _get_model(self):
        """Lazy initialize Gemini model."""
        if not _GEMINI_AVAILABLE:
            raise RuntimeError("google-generativeai package not available")

        if self._model is None:
            if not self._api_key:
                raise ValueError("GEMINI_API_KEY not set in environment")
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(
                model_name=self.config.model_name,
                generation_config=GenerationConfig(
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_output_tokens,
                    top_p=self.config.top_p,
                    top_k=self.config.top_k,
                ),
            )
        return self._model

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate text from prompt."""
        start_time = time.time()
        model = self._get_model()

        try:
            response = model.generate_content(
                prompt,
                request_options={"timeout": _LLM_TIMEOUT_S},
                **kwargs,
            )
            duration_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                content=response.text or "",
                model=self.config.model_name,
                tokens_used=getattr(response.usage_metadata, "total_token_count", 0)
                if hasattr(response, "usage_metadata")
                else 0,
                duration_ms=duration_ms,
                finish_reason=response.candidates[0].finish_reason.name
                if response.candidates
                else "unknown",
            )
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    def generate_structured(self, prompt: str, schema: dict[str, Any], **kwargs) -> dict[str, Any]:
        """Generate structured output using JSON mode."""
        model = self._get_model()

        json_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Do not include any explanation, markdown, or text outside the JSON object."""

        try:
            response = model.generate_content(
                json_prompt,
                generation_config=GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=self.config.max_output_tokens,
                    response_mime_type="application/json",
                ),
                request_options={"timeout": _LLM_TIMEOUT_S},
            )
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response.text}")
            raise
        except Exception as e:
            logger.error(f"Structured generation failed: {e}")
            raise

    def generate_incident_analysis(
        self,
        query: str,
        understanding: QueryUnderstanding,
        evidence: list[dict[str, Any]],
        graph_relationships: list[dict[str, Any]],
        context: RAGContext,
    ) -> dict[str, Any]:
        """Generate structured incident analysis response."""
        prompt = self._build_incident_analysis_prompt(
            query, understanding, evidence, graph_relationships, context
        )

        schema = {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string", "format": "uuid"},
                "title": {"type": "string"},
                "source": {
                    "type": "string",
                    "enum": ["github", "confluence", "pagerduty", "manual", "logs", "analysis"],
                },
                "source_url": {"type": ["string", "null"], "format": "uri"},
                "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                "status": {
                    "type": "string",
                    "enum": ["resolved", "mitigated", "open", "investigating"],
                },
                "service": {"type": "string"},
                "team": {"type": "string"},
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string", "format": "date-time"},
                            "event": {"type": "string"},
                            "actor": {"type": "string"},
                        },
                        "required": ["timestamp", "event", "actor"],
                    },
                },
                "root_cause": {"type": "string"},
                "impact": {"type": "string"},
                "resolution": {"type": "string"},
                "lessons_learned": {"type": "array", "items": {"type": "string"}},
                "log_snippets": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "created_at": {"type": "string", "format": "date-time"},
                "resolved_at": {"type": ["string", "null"], "format": "date-time"},
                "raw_content": {"type": "string"},
                "evidence": {"type": "array", "items": {"type": "object"}},
                "graph_relationships": {"type": "array", "items": {"type": "object"}},
                "recommended_investigation": {"type": "array", "items": {"type": "string"}},
                "potential_root_cause": {"type": "string"},
                "risk_severity": {"type": "string", "enum": ["Critical", "High", "Medium", "Low"]},
                "confidence": {
                    "type": "string",
                    "enum": ["High", "Medium", "Low", "Insufficient Evidence"],
                },
                "sources": {"type": "array", "items": {"type": "object"}},
            },
            "required": [
                "incident_id",
                "title",
                "source",
                "severity",
                "status",
                "service",
                "team",
                "timeline",
                "root_cause",
                "impact",
                "resolution",
                "lessons_learned",
                "log_snippets",
                "tags",
                "created_at",
                "raw_content",
                "evidence",
                "graph_relationships",
                "recommended_investigation",
                "potential_root_cause",
                "risk_severity",
                "confidence",
                "sources",
            ],
        }

        try:
            data = self.generate_structured(prompt, schema)
        except Exception as e:
            logger.error(f"Incident analysis generation failed, returning grounded fallback: {e}")
            data = {}
        return _ground_analysis_response(data, query, understanding, evidence, graph_relationships)

    def _build_incident_analysis_prompt(
        self,
        query: str,
        understanding: QueryUnderstanding,
        evidence: list[dict[str, Any]],
        graph_relationships: list[dict[str, Any]],
        context: RAGContext,
    ) -> str:
        """Build the prompt for incident analysis generation."""

        evidence_text = self._format_evidence_for_prompt(evidence)
        graph_text = self._format_graph_for_prompt(graph_relationships)

        intent_guidance = {
            "root_cause_analysis": "Focus on identifying the root cause with supporting evidence.",
            "historical_incident_search": "Focus on finding and comparing similar historical incidents.",  # noqa: E501
            "component_investigation": "Focus on which components to investigate first.",  # noqa: E501
            "dependency_investigation": "Focus on service dependencies and upstream/downstream impacts.",  # noqa: E501
            "previous_fix_search": "Focus on what fixes worked previously.",
            "lesson_learned_search": "Focus on lessons learned and preventive measures.",
            "incident_comparison": "Focus on comparing this incident with similar ones.",
            "impact_analysis": "Focus on blast radius and affected services.",
            "service_relationship": "Focus on how services interact and depend on each other.",
            "error_diagnosis": "Focus on diagnosing the specific error.",
            "postmortem_retrieval": "Focus on retrieving postmortem details.",
        }

        guidance = intent_guidance.get(
            understanding.intent.value, "Provide comprehensive incident analysis."
        )

        prompt = f"""You are an expert SRE and Incident Commander analyzing production incidents.

USER QUERY: "{query}"

QUERY UNDERSTANDING:
- Intent: {understanding.intent.value}
- Detected Services: {", ".join(understanding.entities.services) or "None"}
- Detected Errors: {", ".join(understanding.entities.errors) or "None"}
- Severity Hint: {understanding.entities.severity or "Not specified"}
- Guidance: {guidance}

RETRIEVED EVIDENCE (Vector + Graph):
{evidence_text}

GRAPH RELATIONSHIPS:
{graph_text}

TASK: Generate a comprehensive incident analysis report. Follow these rules STRICTLY:

1. EVIDENCE-BACKED: Every claim must be supported by retrieved evidence. Cite using [Source N].
2. NO HALLUCINATION: Never invent incidents, fixes, logs, or relationships not in the evidence.
3. DISTINGUISH EVIDENCE vs INFERENCE: Clearly separate what was retrieved vs what you infer.
4. CONFIDENCE SCORING: Rate confidence High/Medium/Low/Insufficient Evidence based on quality.
5. ACTIONABLE RECOMMENDATIONS: Provide specific, prioritized investigation steps.

If evidence is insufficient, say "Insufficient evidence found" and state what was vs what's missing.

OUTPUT FORMAT: Return ONLY a JSON object matching the schema. No markdown, no extra text.

Generate incident_id as a valid UUID v4 string.
Use current timestamp for created_at if not found in evidence.
For timeline, extract from evidence or create reasonable timeline based on evidence.
For sources, include: source_file, chunk_id, retrieval_score, source_type, service, timestamp."""

        return prompt

    def _format_evidence_for_prompt(self, evidence: list[dict[str, Any]]) -> str:
        """Format evidence for inclusion in prompt."""
        if not evidence:
            return "No evidence retrieved."

        lines = []
        for i, ev in enumerate(evidence[:15], 1):
            source_info = f"[Source {i}] "
            source_info += f"Type: {ev.get('type', 'unknown')}, "
            source_info += f"Source: {ev.get('source', 'unknown')}, "
            source_info += f"Score: {ev.get('score', 0):.3f}, "
            source_info += f"Service: {ev.get('metadata', {}).get('service', 'unknown')}, "
            source_info += f"Time: {ev.get('metadata', {}).get('timestamp', 'unknown')}"
            lines.append(source_info)
            lines.append(f"Content: {ev.get('content', '')[:400]}")
            lines.append("")

        return "\n".join(lines)

    def _format_graph_for_prompt(self, relationships: list[dict[str, Any]]) -> str:
        """Format graph relationships for prompt."""
        if not relationships:
            return "No graph relationships retrieved."

        lines = ["Graph structure:"]
        for rel in relationships[:20]:
            lines.append(
                f"  {rel.get('source', '?')} --[{rel.get('type', 'RELATED_TO')}]--> {rel.get('target', '?')}"  # noqa: E501
            )
        return "\n".join(lines)


class LLMProviderFactory:
    """Factory for creating LLM providers."""

    PROVIDERS = {
        LLMProviderType.GEMINI: GeminiProvider,
        LLMProviderType.MOCK: MockLLMProvider,
    }

    @classmethod
    def create(cls, provider_type: LLMProviderType, config: LLMConfig | None = None) -> LLMProvider:
        if provider_type not in cls.PROVIDERS:
            raise ValueError(f"Unknown LLM provider: {provider_type}")
        return cls.PROVIDERS[provider_type](config)

    @classmethod
    def register(cls, provider_type: LLMProviderType, provider_class: type[LLMProvider]):
        cls.PROVIDERS[provider_type] = provider_class


def get_llm_provider(
    provider_type: LLMProviderType | None = None,
    config: LLMConfig | None = None,
) -> LLMProvider:
    """Get LLM provider from environment or explicit config."""
    if provider_type is None:
        provider_name = settings.LLM_PROVIDER
        try:
            provider_type = LLMProviderType(provider_name)
        except ValueError:
            provider_type = LLMProviderType.MOCK

    if config is None:
        config = LLMConfig(
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )

    # Fallback to mock if Gemini requested but not available
    if provider_type == LLMProviderType.GEMINI and not _GEMINI_AVAILABLE:
        logger.warning("Gemini requested but not available, falling back to mock provider")
        provider_type = LLMProviderType.MOCK

    return LLMProviderFactory.create(provider_type, config)
