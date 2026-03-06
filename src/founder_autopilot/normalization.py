from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Final

from founder_autopilot.contracts import ActivityEvent, MetadataValue, SignalType


VALID_SIGNAL_TYPES: Final[set[str]] = {
    "code",
    "writing",
    "planning",
    "research",
    "ops",
    "unknown",
}

CODE_EXTENSIONS: Final[set[str]] = {
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
}
OPS_EXTENSIONS: Final[set[str]] = {".env", ".ini", ".ps1", ".toml", ".yaml", ".yml"}
WRITING_EXTENSIONS: Final[set[str]] = {".md", ".rst", ".txt"}
RESEARCH_EXTENSIONS: Final[set[str]] = {".csv", ".pdf"}
PLANNING_HINTS: Final[set[str]] = {"brief", "issue", "plan", "prd", "roadmap", "spec", "task"}


def normalize_timestamp(value: str | int | float | datetime) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value, UTC)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("timestamp is empty")
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            try:
                parsed = datetime.fromtimestamp(float(raw), UTC)
            except ValueError as exc:
                raise ValueError(f"timestamp is not ISO-8601: {value}") from exc
    else:
        raise ValueError(f"unsupported timestamp type: {type(value).__name__}")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    else:
        parsed = parsed.astimezone(UTC)
    return parsed.isoformat()


def build_cursor(timestamp: str | int | float | datetime, source_event_id: str) -> str:
    return f"{normalize_timestamp(timestamp)}|{source_event_id}"


def compute_checksum(source: str, payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(f"{source}|{encoded}".encode("utf-8")).hexdigest()


def make_deterministic_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256(
        "|".join(str(part) for part in parts).encode("utf-8")
    ).hexdigest()
    return f"{prefix}_{digest[:16]}"


def normalize_activity_event(
    *,
    project_id: str,
    source: str,
    raw_event_id: str,
    payload: dict[str, object],
) -> ActivityEvent:
    match source:
        case "git":
            activity = _normalize_git_event(project_id, payload)
        case "cos":
            activity = _normalize_cos_event(project_id, payload)
        case "filesystem":
            activity = _normalize_filesystem_event(project_id, payload)
        case _:
            raise ValueError(f"unsupported source: {source}")

    validate_activity_event(activity)
    return ActivityEvent(
        id=activity.id,
        source=activity.source,
        timestamp=activity.timestamp,
        actor=activity.actor,
        project_id=activity.project_id,
        signal_type=activity.signal_type,
        summary=activity.summary,
        metadata={
            **activity.metadata,
            "rawEventId": raw_event_id,
        },
    )


def validate_activity_event(activity: ActivityEvent) -> None:
    if activity.source not in {"git", "cos", "filesystem", "manual"}:
        raise ValueError(f"invalid source: {activity.source}")
    if activity.actor != "founder":
        raise ValueError("actor must be 'founder'")
    if activity.signal_type not in VALID_SIGNAL_TYPES:
        raise ValueError(f"invalid signal type: {activity.signal_type}")
    if not activity.summary.strip():
        raise ValueError("summary is required")
    normalize_timestamp(activity.timestamp)


def infer_signal_type_from_path(path_value: str) -> SignalType:
    path = Path(path_value)
    suffix = path.suffix.lower()
    joined = " ".join(part.lower() for part in path.parts)
    if suffix in CODE_EXTENSIONS:
        return "code"
    if suffix in OPS_EXTENSIONS:
        return "ops"
    if suffix in RESEARCH_EXTENSIONS:
        return "research"
    if suffix in WRITING_EXTENSIONS:
        if any(hint in joined for hint in PLANNING_HINTS):
            return "planning"
        if "docs" in joined or "note" in joined:
            return "writing"
    return "unknown"


def _normalize_git_event(project_id: str, payload: dict[str, object]) -> ActivityEvent:
    source_event_id = _require_string(
        payload.get("sourceEventId") or payload.get("commit"),
        "git.sourceEventId",
    )
    timestamp = normalize_timestamp(
        payload.get("committedAt") or payload.get("timestamp") or payload.get("observedAt")
    )
    summary = _first_non_empty_string(
        payload.get("summary"),
        payload.get("message"),
        default=f"Committed {source_event_id[:7]}",
    )
    metadata = _metadata_from_payload(
        payload,
        consumed_keys={"committedAt", "message", "sourceEventId", "summary", "timestamp"},
    )
    metadata.setdefault("commit", source_event_id)
    metadata.setdefault("filesChanged", _count_payload_items(payload.get("files")))
    return ActivityEvent(
        id=make_deterministic_id("evt", project_id, "git", source_event_id),
        source="git",
        timestamp=timestamp,
        actor="founder",
        project_id=project_id,
        signal_type="code",
        summary=summary,
        metadata=metadata,
    )


def _normalize_cos_event(project_id: str, payload: dict[str, object]) -> ActivityEvent:
    timestamp = normalize_timestamp(
        payload.get("timestamp")
        or payload.get("occurredAt")
        or payload.get("createdAt")
        or payload.get("observedAt")
    )
    source_event_id = _first_non_empty_string(
        payload.get("id"),
        payload.get("sourceEventId"),
        payload.get("eventId"),
        default=make_deterministic_id("cos", project_id, timestamp, payload),
    )
    summary = _first_non_empty_string(
        payload.get("summary"),
        payload.get("title"),
        payload.get("message"),
        payload.get("action"),
        default="COS activity",
    )
    signal_type = _coerce_signal_type(
        payload.get("signalType"),
        fallback_text=" ".join(
            str(payload.get(key, ""))
            for key in ("summary", "title", "message", "category", "type", "tags")
        ),
    )
    metadata = _metadata_from_payload(
        payload,
        consumed_keys={
            "action",
            "createdAt",
            "eventId",
            "id",
            "message",
            "occurredAt",
            "signalType",
            "sourceEventId",
            "summary",
            "timestamp",
            "title",
        },
    )
    return ActivityEvent(
        id=make_deterministic_id("evt", project_id, "cos", source_event_id),
        source="cos",
        timestamp=timestamp,
        actor="founder",
        project_id=project_id,
        signal_type=signal_type,
        summary=summary,
        metadata=metadata,
    )


def _normalize_filesystem_event(
    project_id: str,
    payload: dict[str, object],
) -> ActivityEvent:
    path_value = _first_non_empty_string(
        payload.get("relativePath"),
        payload.get("path"),
        default="unknown-file",
    )
    timestamp = normalize_timestamp(
        payload.get("modifiedAt") or payload.get("timestamp") or payload.get("observedAt")
    )
    source_event_id = _first_non_empty_string(
        payload.get("sourceEventId"),
        default=f"{path_value}:{timestamp}",
    )
    signal_type = _coerce_signal_type(
        payload.get("signalType"),
        fallback_path=path_value,
    )
    summary = _first_non_empty_string(
        payload.get("summary"),
        default=f"Updated {path_value}",
    )
    metadata = _metadata_from_payload(
        payload,
        consumed_keys={"modifiedAt", "signalType", "sourceEventId", "summary", "timestamp"},
    )
    metadata.setdefault("path", path_value)
    return ActivityEvent(
        id=make_deterministic_id("evt", project_id, "filesystem", source_event_id),
        source="filesystem",
        timestamp=timestamp,
        actor="founder",
        project_id=project_id,
        signal_type=signal_type,
        summary=summary,
        metadata=metadata,
    )


def _coerce_signal_type(
    raw_value: object,
    *,
    fallback_path: str | None = None,
    fallback_text: str | None = None,
) -> SignalType:
    if isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered in VALID_SIGNAL_TYPES:
            return lowered  # type: ignore[return-value]

    if fallback_path:
        inferred = infer_signal_type_from_path(fallback_path)
        if inferred != "unknown":
            return inferred

    text = (fallback_text or "").lower()
    if any(token in text for token in {"commit", "code", "build", "test", "refactor"}):
        return "code"
    if any(token in text for token in {"write", "draft", "doc", "note"}):
        return "writing"
    if any(token in text for token in {"plan", "spec", "task", "roadmap"}):
        return "planning"
    if any(token in text for token in {"research", "investigate", "read", "explore"}):
        return "research"
    if any(token in text for token in {"config", "ops", "deploy", "infra"}):
        return "ops"
    return "unknown"


def _metadata_from_payload(
    payload: dict[str, object],
    *,
    consumed_keys: set[str],
) -> dict[str, MetadataValue]:
    metadata: dict[str, MetadataValue] = {}
    for key, value in payload.items():
        if key in consumed_keys:
            continue
        metadata[key] = _coerce_metadata_value(value)
    return metadata


def _coerce_metadata_value(value: object) -> MetadataValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, sort_keys=True, default=str)


def _count_payload_items(value: object) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def _require_string(raw_value: object, field_name: str) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"{field_name} is required")
    return raw_value.strip()


def _first_non_empty_string(
    *values: object,
    default: str,
) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default
