"""
Log and document parsers for the ingestion pipeline.

Supports multiple log formats and document types with extensible parser architecture.
"""

import csv
import json
import re
import uuid
from abc import ABC, abstractmethod
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ParsedEntry:
    """Normalized log/document entry ready for chunking."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime | None = None
    service: str = "unknown"
    host: str = "unknown"
    level: str = "INFO"
    message: str = ""
    trace_id: str | None = None
    request_id: str | None = None
    environment: str = "production"
    exception: str | None = None
    stack_trace: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""
    source_type: str = "log"
    line_number: int = 0

    def to_text(self) -> str:
        """Convert to text for embedding."""
        parts = []
        if self.timestamp:
            parts.append(f"[{self.timestamp.isoformat()}]")
        parts.append(f"service={self.service}")
        parts.append(f"host={self.host}")
        parts.append(f"level={self.level}")
        parts.append(self.message)
        if self.exception:
            parts.append(f"exception={self.exception}")
        if self.stack_trace:
            parts.append(f"stack_trace={self.stack_trace}")
        return " ".join(parts)

    def to_metadata(self) -> dict[str, Any]:
        """Extract metadata for vector storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "service": self.service,
            "host": self.host,
            "level": self.level,
            "environment": self.environment,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "source_file": self.source_file,
            "source_type": self.source_type,
            "line_number": self.line_number,
            "has_exception": self.exception is not None,
            "has_stack_trace": self.stack_trace is not None,
            **self.raw,
        }


class BaseParser(ABC):
    """Abstract base class for all parsers."""

    @abstractmethod
    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        """Parse a file and yield normalized entries."""
        pass

    def _detect_encoding(self, filepath: Path) -> str:
        """Detect file encoding, fallback to utf-8 with error handling."""
        try:
            with open(filepath, encoding="utf-8") as f:
                f.read(1024)
            return "utf-8"
        except UnicodeDecodeError:
            return "utf-8"


class LogParser(BaseParser):
    """Base class for log parsers with common functionality."""

    def __init__(self, source_type: str = "log"):
        self.source_type = source_type

    def _open_file(self, filepath: Path):
        """Open file with encoding detection and error handling."""
        encoding = self._detect_encoding(filepath)
        return open(filepath, encoding=encoding, errors="replace")


class SSHLogParser(LogParser):
    """Parser for SSH auth logs."""

    PATTERN = re.compile(
        r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?)(?:\[\d+\])?:\s+(.+)$"
    )

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                match = self.PATTERN.match(line)
                if not match:
                    continue

                timestamp_str, host, service, message = match.groups()

                try:
                    timestamp = datetime.strptime(f"2024 {timestamp_str}", "%Y %b %d %H:%M:%S")
                except ValueError:
                    timestamp = datetime.now()

                level = "INFO"
                message_lower = message.lower()
                if any(
                    kw in message_lower
                    for kw in ["failed", "error", "invalid", "failure", "break-in", "refused"]
                ):
                    level = "ERROR"
                elif any(kw in message_lower for kw in ["accepted", "opened", "closed", "success"]):
                    level = "INFO"
                elif "warning" in message_lower or "warn" in message_lower:
                    level = "WARN"

                ip_match = re.search(r"from\s+(\d+\.\d+\.\d+\.\d+)", message)
                user_match = re.search(r"(?:invalid user|user)\s+(\S+)", message)

                yield ParsedEntry(
                    timestamp=timestamp,
                    service="sshd",
                    host=host,
                    level=level,
                    message=message,
                    raw={
                        "ip": ip_match.group(1) if ip_match else None,
                        "user": user_match.group(1) if user_match else None,
                    },
                    source_file=filepath.name,
                    source_type=self.source_type,
                    line_number=line_num,
                )


class ProxifierLogParser(LogParser):
    """Parser for Proxifier logs."""

    PATTERN = re.compile(r"^\[(\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+(\S+)\s+-\s+(\S+)\s+(.+)$")

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                match = self.PATTERN.match(line)
                if not match:
                    continue

                timestamp_str, process, endpoint, details = match.groups()

                try:
                    timestamp = datetime.strptime(f"2024 {timestamp_str}", "%Y %m.%d %H:%M:%S")
                except ValueError:
                    timestamp = datetime.now()

                host = endpoint.split(":")[0] if ":" in endpoint else endpoint

                yield ParsedEntry(
                    timestamp=timestamp,
                    service="proxifier",
                    host=host,
                    level="INFO",
                    message=f"{process} - {details}",
                    raw={"process": process, "endpoint": endpoint, "details": details},
                    source_file=filepath.name,
                    source_type=self.source_type,
                    line_number=line_num,
                )


class HealthAppLogParser(LogParser):
    """Parser for HealthApp Android logs."""

    PATTERN = re.compile(r"^(\d{8}-\d{2}:\d{2}:\d{2}:\d{3})\|(\S+)\|(\d+)\|(.+)$")

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                match = self.PATTERN.match(line)
                if not match:
                    continue

                timestamp_str, tag, pid, message = match.groups()

                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d-%H:%M:%S:%f")
                except ValueError:
                    timestamp = datetime.now()

                yield ParsedEntry(
                    timestamp=timestamp,
                    service="healthapp",
                    host=tag,
                    level="DEBUG",
                    message=message,
                    raw={"tag": tag, "pid": pid},
                    source_file=filepath.name,
                    source_type=self.source_type,
                    line_number=line_num,
                )


class ApacheLogParser(LogParser):
    """Parser for Apache error logs."""

    PATTERN = re.compile(
        r"^\[(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})\]\s+\[(\w+)\]\s+(.+)$"
    )

    LEVEL_MAP = {
        "notice": "INFO",
        "warn": "WARN",
        "error": "ERROR",
        "crit": "CRITICAL",
        "alert": "CRITICAL",
        "emerg": "CRITICAL",
        "debug": "DEBUG",
        "info": "INFO",
    }

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                match = self.PATTERN.match(line)
                if not match:
                    continue

                timestamp_str, level, message = match.groups()

                try:
                    timestamp = datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %Y")
                except ValueError:
                    timestamp = datetime.now()

                mapped_level = self.LEVEL_MAP.get(level.lower(), "INFO")

                yield ParsedEntry(
                    timestamp=timestamp,
                    service="apache",
                    host="apache-server",
                    level=mapped_level,
                    message=message,
                    raw={"apache_level": level},
                    source_file=filepath.name,
                    source_type=self.source_type,
                    line_number=line_num,
                )


class AndroidLogParser(LogParser):
    """Parser for Android logcat format."""

    PATTERN = re.compile(
        r"^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+(\S+):\s+(.+)$"
    )

    LEVEL_MAP = {
        "V": "DEBUG",
        "D": "DEBUG",
        "I": "INFO",
        "W": "WARN",
        "E": "ERROR",
        "F": "CRITICAL",
    }

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                match = self.PATTERN.match(line)
                if not match:
                    continue

                timestamp_str, pid, tid, level_char, tag, message = match.groups()

                try:
                    timestamp = datetime.strptime(f"2024 {timestamp_str}", "%Y %m-%d %H:%M:%S.%f")
                except ValueError:
                    timestamp = datetime.now()

                yield ParsedEntry(
                    timestamp=timestamp,
                    service="android",
                    host=tag,
                    level=self.LEVEL_MAP.get(level_char, "INFO"),
                    message=message,
                    raw={"pid": pid, "tid": tid, "tag": tag, "level_char": level_char},
                    source_file=filepath.name,
                    source_type=self.source_type,
                    line_number=line_num,
                )


class JSONLogParser(LogParser):
    """Parser for JSON Lines format logs."""

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                timestamp = None
                if "timestamp" in data:
                    try:
                        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        timestamp = datetime.now()
                elif "@timestamp" in data:
                    try:
                        timestamp = datetime.fromisoformat(
                            data["@timestamp"].replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        timestamp = datetime.now()

                yield ParsedEntry(
                    timestamp=timestamp,
                    service=data.get("service", data.get("logger", "unknown")),
                    host=data.get("host", data.get("hostname", "unknown")),
                    level=data.get("level", data.get("severity", "INFO")).upper(),
                    message=data.get("message", data.get("msg", json.dumps(data))),
                    trace_id=data.get("trace_id") or data.get("traceId"),
                    request_id=data.get("request_id") or data.get("requestId"),
                    environment=data.get("environment", "production"),
                    exception=data.get("exception"),
                    stack_trace=data.get("stack_trace") or data.get("stackTrace"),
                    raw={
                        k: v
                        for k, v in data.items()
                        if k
                        not in [
                            "timestamp",
                            "@timestamp",
                            "service",
                            "logger",
                            "host",
                            "hostname",
                            "level",
                            "severity",
                            "message",
                            "msg",
                            "trace_id",
                            "traceId",
                            "request_id",
                            "requestId",
                            "environment",
                            "exception",
                            "stack_trace",
                            "stackTrace",
                        ]
                    },
                    source_file=filepath.name,
                    source_type=self.source_type,
                    line_number=line_num,
                )


class TextLogParser(LogParser):
    """Fallback parser for generic text logs."""

    TIMESTAMP_PATTERNS = [
        (
            r"^(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)",
            "%Y-%m-%dT%H:%M:%S.%f%z",
        ),
        (r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", "%Y-%m-%d %H:%M:%S"),
        (r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]", "%Y-%m-%d %H:%M:%S"),
        (r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})", "%b %d %H:%M:%S"),
    ]

    LEVEL_PATTERN = re.compile(
        r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL|TRACE)\b", re.IGNORECASE
    )

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                timestamp = None
                message = line

                for pattern, fmt in self.TIMESTAMP_PATTERNS:
                    match = re.match(pattern, line)
                    if match:
                        try:
                            ts_str = match.group(1)
                            if "T" in ts_str or "+" in ts_str or "Z" in ts_str:
                                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            else:
                                timestamp = datetime.strptime(ts_str, fmt.replace("%f", ""))
                            message = line[match.end() :].strip()
                            break
                        except ValueError:
                            continue

                level_match = self.LEVEL_PATTERN.search(line)
                level = level_match.group(1).upper() if level_match else "INFO"
                if level == "WARNING":
                    level = "WARN"

                yield ParsedEntry(
                    timestamp=timestamp,
                    service="unknown",
                    host="unknown",
                    level=level,
                    message=message,
                    source_file=filepath.name,
                    source_type=self.source_type,
                    line_number=line_num,
                )


class CSVParser(BaseParser):
    """Parser for CSV files."""

    def __init__(self, source_type: str = "csv"):
        super().__init__()
        self.source_type = source_type

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            reader = csv.DictReader(f)
            for line_num, row in enumerate(reader, 1):
                timestamp = None
                for ts_field in ["timestamp", "time", "@timestamp", "datetime", "date"]:
                    if ts_field in row and row[ts_field]:
                        try:
                            timestamp = datetime.fromisoformat(row[ts_field].replace("Z", "+00:00"))
                            break
                        except ValueError:
                            continue

                yield ParsedEntry(
                    timestamp=timestamp,
                    service=row.get("service", row.get("logger", "unknown")),
                    host=row.get("host", row.get("hostname", "unknown")),
                    level=row.get("level", row.get("severity", "INFO")).upper(),
                    message=row.get("message", row.get("msg", json.dumps(row))),
                    trace_id=row.get("trace_id") or row.get("traceId"),
                    request_id=row.get("request_id") or row.get("requestId"),
                    environment=row.get("environment", "production"),
                    exception=row.get("exception"),
                    stack_trace=row.get("stack_trace") or row.get("stackTrace"),
                    raw={
                        k: v
                        for k, v in row.items()
                        if k
                        not in [
                            "timestamp",
                            "time",
                            "@timestamp",
                            "datetime",
                            "date",
                            "service",
                            "logger",
                            "host",
                            "hostname",
                            "level",
                            "severity",
                            "message",
                            "msg",
                            "trace_id",
                            "traceId",
                            "request_id",
                            "requestId",
                            "environment",
                            "exception",
                            "stack_trace",
                            "stackTrace",
                        ]
                    },
                    source_file=filepath.name,
                    source_type=self.source_type,
                    line_number=line_num,
                )


class MarkdownParser(BaseParser):
    """Parser for Markdown files (postmortems, documentation)."""

    def __init__(self, source_type: str = "markdown"):
        super().__init__()
        self.source_type = source_type

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            content = f.read()

        yield ParsedEntry(
            timestamp=datetime.now(),
            service="documentation",
            host="manual",
            level="INFO",
            message=content[:5000],
            raw={"full_content": content, "file_size": len(content)},
            source_file=filepath.name,
            source_type=self.source_type,
            line_number=1,
        )


class JSONDocumentParser(BaseParser):
    """Parser for JSON documents (incident reports, postmortems)."""

    def __init__(self, source_type: str = "json"):
        super().__init__()
        self.source_type = source_type

    def parse(self, filepath: Path) -> Generator[ParsedEntry, None, None]:
        with self._open_file(filepath) as f:
            data = json.load(f)

        if isinstance(data, list):
            for idx, item in enumerate(data):
                yield self._parse_item(item, filepath, idx + 1)
        else:
            yield self._parse_item(data, filepath, 1)

    def _parse_item(self, data: dict, filepath: Path, line_num: int) -> ParsedEntry:
        timestamp = None
        for ts_field in ["timestamp", "created_at", "date", "@timestamp"]:
            if ts_field in data and data[ts_field]:
                try:
                    timestamp = datetime.fromisoformat(str(data[ts_field]).replace("Z", "+00:00"))
                    break
                except (ValueError, AttributeError):
                    continue

        return ParsedEntry(
            timestamp=timestamp,
            service=data.get("service", data.get("component", "unknown")),
            host=data.get("host", data.get("environment", "unknown")),
            level=data.get("severity", data.get("level", "INFO")).upper(),
            message=data.get(
                "description", data.get("summary", data.get("message", json.dumps(data)))
            ),
            trace_id=data.get("trace_id") or data.get("traceId"),
            request_id=data.get("request_id") or data.get("requestId"),
            environment=data.get("environment", "production"),
            exception=data.get("exception"),
            stack_trace=data.get("stack_trace") or data.get("stackTrace"),
            raw={
                k: v
                for k, v in data.items()
                if k
                not in [
                    "timestamp",
                    "created_at",
                    "date",
                    "@timestamp",
                    "service",
                    "component",
                    "host",
                    "environment",
                    "severity",
                    "level",
                    "description",
                    "summary",
                    "message",
                    "trace_id",
                    "traceId",
                    "request_id",
                    "requestId",
                    "exception",
                    "stack_trace",
                    "stackTrace",
                ]
            },
            source_file=filepath.name,
            source_type=self.source_type,
            line_number=line_num,
        )


class ParserFactory:
    """Factory for selecting appropriate parser based on file extension and content."""

    EXTENSION_MAP = {
        ".log": "log",
        ".txt": "log",
        ".json": "json",
        ".csv": "csv",
        ".md": "markdown",
        ".markdown": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
    }

    LOG_PARSERS = {
        "SSH.log": SSHLogParser(),
        "Proxifier.log": ProxifierLogParser(),
        "HealthApp.log": HealthAppLogParser(),
        "Apache.log": ApacheLogParser(),
        "Android.log": AndroidLogParser(),
    }

    def __init__(self):
        self._parsers: dict[str, BaseParser] = {
            "log": TextLogParser(),
            "json": JSONDocumentParser(),
            "jsonl": JSONLogParser(),
            "csv": CSVParser(),
            "markdown": MarkdownParser(),
        }

    def get_parser(self, filepath: Path) -> BaseParser:
        """Get appropriate parser for a file."""
        filename = filepath.name
        extension = filepath.suffix.lower()

        if filename in self.LOG_PARSERS:
            return self.LOG_PARSERS[filename]

        parser_type = self.EXTENSION_MAP.get(extension, "log")
        return self._parsers.get(parser_type, TextLogParser())

    def register_parser(self, name: str, parser: BaseParser):
        """Register a custom parser."""
        self._parsers[name] = parser


PARSER_FACTORY = ParserFactory()
