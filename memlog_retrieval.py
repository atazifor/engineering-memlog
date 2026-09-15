"""Shared, deterministic lexical ranking for Memlog query retrieval.

The implementation stays stdlib-only and scans the JSONL corpus in memory. It is
intentionally small: the data file remains the storage contract while this module
decides which matching entries should appear first.
"""

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


FIELD_WEIGHTS = (
    ("title", 8.0),
    ("tags", 7.0),
    ("problem", 6.0),
    ("cause", 5.0),
    ("prevention", 4.5),
    ("artifact", 4.0),
    ("fix", 3.0),
    ("repo", 3.0),
    ("service", 3.0),
    ("environment", 1.5),
    ("status", 0.5),
    ("source", 0.5),
)

TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def normalize(value: str) -> str:
    """Case-fold compatible Unicode and collapse whitespace."""
    compatible = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(compatible.split())


def tokenize(value: str) -> List[str]:
    """Split punctuation-delimited identifiers into stable lexical terms."""
    return TOKEN_RE.findall(normalize(value))


def parse_iso(timestamp: Any) -> Optional[datetime]:
    if not isinstance(timestamp, str) or not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def recency_bonus(timestamp: Any, now: datetime) -> float:
    """Small tie-breaker: 1.0 for seven days, decaying to zero by day 90."""
    parsed = parse_iso(timestamp)
    if parsed is None:
        return 0.0
    age_days = max(0.0, (now - parsed).total_seconds() / 86400.0)
    if age_days <= 7:
        return 1.0
    if age_days >= 90:
        return 0.0
    return 1.0 - (age_days - 7) / (90 - 7)


def field_text(entry: Dict[str, Any], field: str) -> str:
    value = entry.get(field)
    if isinstance(value, str):
        return normalize(value)
    if field == "tags" and isinstance(value, list):
        return normalize(" ".join(item for item in value if isinstance(item, str)))
    return ""


def token_match_quality(query_token: str, field_tokens: Sequence[str]) -> float:
    """Return 1.0 for exact tokens and 0.7 for useful identifier prefixes."""
    if query_token in field_tokens:
        return 1.0
    if len(query_token) < 4:
        return 0.0
    for candidate in field_tokens:
        if (
            len(candidate) >= 4
            and abs(len(candidate) - len(query_token)) <= 3
            and (candidate.startswith(query_token) or query_token.startswith(candidate))
        ):
            return 0.7
    return 0.0


def score_entry(
    entry: Dict[str, Any],
    terms: Sequence[str],
    now: Optional[datetime] = None,
) -> float:
    """Score query coverage, field importance, exact phrases, and light freshness."""
    normalized_terms = []
    for term in terms:
        normalized = normalize(term)
        if normalized:
            normalized_terms.append(normalized)
    query_tokens: List[str] = []
    seen_tokens = set()
    for term in normalized_terms:
        for token in tokenize(term):
            if token not in seen_tokens:
                seen_tokens.add(token)
                query_tokens.append(token)

    fields = []
    for field, weight in FIELD_WEIGHTS:
        text = field_text(entry, field)
        if text:
            fields.append((text, set(tokenize(text)), weight))

    score = 0.0
    matched_tokens = 0
    for query_token in query_tokens:
        best = 0.0
        for _, field_tokens, weight in fields:
            best = max(best, weight * token_match_quality(query_token, field_tokens))
        if best > 0.0:
            matched_tokens += 1
            score += best

    # Avoid returning an entry for one generic overlap from a richer query.
    # Single- and two-token lookups remain permissive for error codes and terse
    # identifiers; three or more distinct tokens need at least two matches.
    minimum_matches = 2 if len(query_tokens) >= 3 else 1
    if matched_tokens < minimum_matches:
        return 0.0

    if query_tokens:
        score += 10.0 * matched_tokens / len(query_tokens)

    # A verbatim phrase in one field should outrank the same words scattered
    # across an entry. Do not match across field boundaries.
    for term in normalized_terms:
        if len(tokenize(term)) < 2:
            continue
        best_phrase = max(
            (2.0 * weight for text, _, weight in fields if term in text),
            default=0.0,
        )
        score += best_phrase

    if score == 0.0:
        return 0.0

    try:
        confidence = float(entry.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    if 0.0 <= confidence <= 1.0:
        score += 0.5 * confidence

    current = now or datetime.now(timezone.utc)
    score += recency_bonus(entry.get("timestamp"), current)
    return score


def rank_entries(
    entries: Iterable[Dict[str, Any]],
    terms: Sequence[str],
    now: Optional[datetime] = None,
) -> List[Tuple[float, Dict[str, Any]]]:
    """Return matching entries by score, recency, then append order."""
    current = now or datetime.now(timezone.utc)
    ranked = []
    for index, entry in enumerate(entries):
        score = score_entry(entry, terms, current)
        if score <= 0.0:
            continue
        timestamp = parse_iso(entry.get("timestamp"))
        epoch = timestamp.timestamp() if timestamp else 0.0
        ranked.append((score, epoch, index, entry))

    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [(score, entry) for score, _, _, entry in ranked]
