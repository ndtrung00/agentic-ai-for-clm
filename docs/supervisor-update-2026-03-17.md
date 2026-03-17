# Supervisor Update — 17 March 2026

**To:** Prof. Dr. Ingo Weber
**From:** Trung Nguyen
**Re:** Post-midterm findings and next steps

---

## 1. German Legal Dataset Investigation

No publicly available German contract dataset comparable to CUAD was found. Prof. Matthes (TUM) maintains a German legal dataset, but it is small in scale and designed for legal reasoning tasks rather than clause extraction. **Decision:** Continue with CUAD (English) as the primary evaluation dataset. This is consistent with the ContractEval baseline we are replicating.

## 2. Retrieve-then-Extract Pipeline Extension

A key finding from the midterm phase: the current pipeline sends entire contracts (up to 300KB) to the LLM as context. This does not reflect how lawyers work — they navigate to relevant sections first, then read closely.

We are extending the pipeline with **intra-document retrieval** as a preprocessing stage:

- **B5 (BM25 retrieval):** Chunk contracts into sections, retrieve top-k chunks via BM25, pass only retrieved context to the LLM. Same ContractEval prompt — clean single-variable ablation against B1.
- **B6 (BM25 + cross-encoder reranking):** BM25 retrieves top-20 candidates, a cross-encoder reranker (ms-marco-MiniLM) rescores to top-5. Tests whether semantic matching recovers what lexical retrieval misses — particularly relevant for rare categories with varied phrasing.

This creates a three-way comparison (B1 vs B5 vs B6) isolating the contribution of retrieval and reranking independently. A detailed implementation plan is available in `docs/retrieve-then-extract-plan.md`.

## 3. Model Performance Update

Preliminary runs with **Gemini 3.1 Pro** show notable improvements in both precision and recall over earlier models (Gemini 2.5 Pro/Flash, GPT-4.1). This is encouraging for the multi-agent experiments (M1), as stronger base models amplify the benefit of specialized routing. Updated model comparison runs are in progress.

## 4. Rethinking Baseline Design — PDF Extraction as Preprocessing

The current baselines feed raw text directly to the LLM. However, CUAD's raw text is extracted from PDFs and contains significant noise — broken tables, misaligned columns, headers/footers repeated on every page, garbled formatting artifacts. The model spends context and attention on text that a human lawyer would never read.

A more realistic baseline would **preprocess the PDF with a dedicated extraction step first** — using tools like document layout parsers (e.g., Adobe Extract API, Docling, PyMuPDF) or vision-based models to produce clean, structured text before passing it to the LLM. This mirrors actual contract review workflows where documents are first ingested and normalized.

This is worth investigating because it tests a different hypothesis: **performance may be bottlenecked by input quality, not model capability.** If a clean-extraction baseline outperforms raw-text baselines, it suggests that better document processing matters more than better prompting or retrieval.

## Next Steps

1. Implement retrieve-then-extract pipeline (B5/B6) and run experiments
2. Complete M1 multi-agent runs with Gemini 3.1 Pro as the backbone
3. Statistical comparison across all configurations (B1, B4, B5, B6, M1, M6)

