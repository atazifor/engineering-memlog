"""Canonical engineering-memlog entry schema validation."""

import math
from datetime import datetime
from typing import Any, Dict, List


CURRENT_SCHEMA_VERSION = 1

REQUIRED_FIELDS = [
    "title",
    "problem",
    "fix",
    "cause",
    "prevention",
    "artifact",
    "repo",
    "service",
    "environment",
    "tags",
    "confidence",
    "status",
    "source",
]

REQUIRED_NONEMPTY_TEXT_FIELDS = [
    "title",
    "problem",
    "cause",
    "fix",
    "prevention",
    "artifact",
    "repo",
    "environment",
    "status",
    "source",
]


def valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def entry_validation_errors(
    entry: Dict[str, Any],
    allow_legacy_schema: bool = True,
) -> List[str]:
    errors: List[str] = []
    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    for field in REQUIRED_NONEMPTY_TEXT_FIELDS:
        if field not in entry:
            continue
        value = entry[field]
        if not isinstance(value, str):
            errors.append(f"Field '{field}' must be a string.")
        elif not value.strip():
            errors.append(f"Field '{field}' must not be empty.")

    if "service" in entry and not isinstance(entry["service"], str):
        errors.append("Field 'service' must be a string.")

    tags = entry.get("tags")
    if not isinstance(tags, list) or not all(
        isinstance(tag, str) and bool(tag.strip()) for tag in tags
    ):
        errors.append("Field 'tags' must be a JSON array of non-empty strings.")

    confidence = entry.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        errors.append("Field 'confidence' must be numeric.")
    elif not math.isfinite(float(confidence)) or not 0.0 <= float(confidence) <= 1.0:
        errors.append("Field 'confidence' must be between 0.0 and 1.0.")

    schema_version = entry.get("schema_version")
    if schema_version is None and not allow_legacy_schema:
        errors.append("Field 'schema_version' is required.")
    elif schema_version is not None and (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != CURRENT_SCHEMA_VERSION
    ):
        errors.append(f"Field 'schema_version' must be {CURRENT_SCHEMA_VERSION}.")

    if "id" not in entry:
        errors.append("Missing auto-filled field: id")
    elif not isinstance(entry["id"], str) or not entry["id"].strip():
        errors.append("Field 'id' must be a non-empty string.")

    if "timestamp" not in entry:
        errors.append("Missing auto-filled field: timestamp")
    elif not valid_timestamp(entry["timestamp"]):
        errors.append("Field 'timestamp' must be an RFC3339 timestamp with a timezone.")

    return errors
