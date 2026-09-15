# Semantic and hybrid retrieval proposal

Status: design proposal; not implemented in version 0.2.0

## Problem statement

Memlog's current ranker is deterministic lexical search. It works when a new
failure shares identifiers, error fragments, technologies, or causal terms with
a stored lesson. It can miss a relevant lesson when the new symptom describes
the same mechanism with different vocabulary—for example, “the remote route is
gone but our wrapper blames deserialization” versus “check upstream status before
parsing an error body.”

The desired improvement is semantic recall without weakening Memlog's safety
contract: results remain untrusted hypotheses, retrieval stays bounded, a miss
never blocks diagnosis, JSONL remains zero-configuration, and users can see which
backend receives their data.

This is a retrieval problem first. Calling it “RAG” can obscure the scope:
Claude already receives recalled entries as context. The proposed work changes
candidate retrieval and ranking; it does not add a second answer-generating
model.

## Evidence and evaluation cases

[`evals/semantic-retrieval-cases.json`](../evals/semantic-retrieval-cases.json)
contains sanitized mechanisms adapted from real Memlog lessons. It includes
literal queries, paraphrases, cross-vocabulary queries, and unrelated controls.
No repository names, customer data, endpoints, or credentials from the source
log are included.

The checked-in baseline is generated with
`./scripts/evaluate-semantic-readiness --check`. The current lexical ranker
retrieves 4 of 6 hard paraphrases at ranks 1, 3, and 5, retrieves the literal
control, and returns nothing for the unrelated control. This small set proves
both that lexical ranking is already useful and that cross-vocabulary gaps are
real; it is not yet large enough to justify a production semantic backend.

A proposed retriever must:

- preserve every exact/identifier-heavy success of the lexical baseline;
- improve the judged hard-paraphrase cases rather than merely returning more
  entries;
- keep unrelated controls below the acceptance threshold;
- report latency, index size, embedding cost if any, and offline behavior;
- include an explanation or matched evidence suitable for hypothesis checking.

The corpus should grow through sanitized failures observed during dogfooding.
Thresholds should be fixed in the RFC after the first baseline measurement, not
chosen after seeing a prototype's results.

## Proposed extension point

Introduce an internal retrieval strategy with one contract:

```text
search(query, limit, filters) -> ordered candidates
```

The existing implementation becomes `lexical-scan`. It remains the default and
continues to work over JSONL or a version-1 provider's `scan` stream.

A future provider protocol version may advertise an optional server-side
`search` capability for stores that maintain FTS, embeddings, or a cache. A
request would carry the raw query, candidate limit, and explicit repo/service/
environment filters. A response would return validated Memlog entries plus an
ordered rank and non-secret match explanation. Provider scores must not be
treated as confidence in the lesson itself.

Compatibility rules:

1. Version-1 `scan`/`append` providers continue unchanged.
2. The built-in JSONL backend never requires embeddings or a network.
3. Semantic retrieval is opt-in; lexical ranking remains available as a control
   and fallback for the same readable store.
4. There is no silent switch to a different store after provider failure.
5. All returned entries pass the existing schema, size, and count limits before
   reaching model context.
6. Hybrid mode combines lexical and semantic *ranks* using a deterministic
   method such as reciprocal-rank fusion; it does not compare backend-specific
   raw scores.

Whether server-side search belongs in provider protocol v2 or a separate
retriever command is deliberately still open. The implementation RFC must decide
that after testing the consistency, privacy, and operational consequences of
each option.

## Contribution sequence

This topic is ready for design contributions, not an unreviewed vector-database
implementation:

1. Extend and independently judge the sanitized evaluation set.
2. Add a baseline harness and commit its metrics.
3. Write the protocol/API RFC, including data flow and failure semantics.
4. Prototype behind an explicit opt-in flag or provider.
5. Compare lexical, semantic, and hybrid results on the fixed evaluation set.
6. Merge only after privacy review, provider conformance tests, clean-install
   tests, and documentation of fallback behavior.

Useful first contributions are new sanitized retrieval cases, relevance
judgments, and small offline experiments. Adding a mandatory embedding service,
changing the default backend, or bypassing verify-before-apply is out of scope.
