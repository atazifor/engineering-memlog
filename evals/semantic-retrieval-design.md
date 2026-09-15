# Semantic retrieval design acceptance

Date: 2026-09-15

- [x] The problem is stated as cross-vocabulary retrieval, not “add a vector
  database.”
- [x] Six mechanisms adapted from real Memlog lessons are sanitized into an
  evaluation corpus with literal, paraphrase, and negative-control queries.
- [x] A repeatable harness records the lexical baseline: 4/6 hard paraphrases
  retrieved at rank 1, the literal control retrieved, and the unrelated control
  rejected.
- [x] The proposed extension preserves provider v1, zero-configuration JSONL,
  bounded model context, schema validation, and no cross-store fallback.
- [x] Server-side provider search versus a separate retriever remains an explicit
  RFC decision rather than an accidental implementation choice.
- [x] Contribution order requires fixed evaluation, data-flow and privacy review,
  an opt-in prototype, comparative measurement, and conformance tests.
- [x] The README describes version 0.2.0 accurately and does not claim semantic
  retrieval exists today.

This milestone makes semantic/hybrid retrieval ready for design and evaluation
contributions. It does not authorize or ship a production retrieval backend.
