# CUAD Retrieve-then-Extract Pipeline

## Motivation

The thesis is being rescoped to mimic how lawyers work with contracts: **navigate to relevant sections first, then extract clauses** — instead of dumping 300KB of text into the LLM. This requires two workstreams:

1. **Dataset preparation** — chunk contracts into sections, map answer spans to chunks, create retrieval ground truth
2. **Pipeline integration** — add retrieval as a stage before extraction, new experiment types (B5/B6), retrieval evaluation metrics

The existing pipeline (`src/experiments/pipeline.py`) is modular: adding a new run type only requires a label in `RUN_TYPE_LABELS`, a factory function, and a branch in `run_experiment_pipeline()`. Everything downstream (evaluation, saving, dashboard) works unchanged.

**Critical gap:** `CUADSample` discards `answer_start` offsets at line 171 of `cuad_loader.py`. These are needed to map answers to chunks.

---

## Part 1: Dataset Preparation

### Step 1: Contract Chunking (`src/data/chunker.py`)

**Dataclasses:**
- `ContractChunk(chunk_id, contract_title, text, char_start, char_end, section_header, chunk_index, total_chunks, strategy)`
- `ChunkedContract(contract_title, original_length, chunks, metadata)`

**Section detection** — 3-tier regex cascade (stop when ≥3 sections found):
1. **Formal:** `ARTICLE [IVX]+`, `Section N.N`
2. **Numbered:** `N. TITLE` (digit + dot + space + uppercase)
3. **Caps lines:** standalone ALL-CAPS lines (5–80 chars)

**`chunk_contract(text, title, max_chunk_chars=4000, min_chunk_chars=200, overlap_chars=200)`:**
1. Detect section boundaries via regex cascade
2. Per section: emit if within range; split at `\n\n` then sentences if too large; merge forward if too small
3. Fallback to paragraph/fixed-size if no sections detected
4. Always emit "preamble" chunk (start → first section boundary)
5. Record `char_start`/`char_end` for every chunk

**Why these defaults:**
- 4000 chars (~1k tokens): fits embedding models, ~8 chunks per median contract
- 200 overlap: covers median answer span length (196 chars)

### Step 2: Ground Truth Mapping (`src/data/chunk_index.py`)

**`map_answers_to_chunks(answers_with_offsets, chunks) → relevant_chunk_ids`:**
- Chunk is relevant if `[char_start, char_end)` overlaps `[span_start, span_end)`
- Negative samples → empty relevant set

**`build_retrieval_ground_truth(cuad_json_path, chunked_contracts) → list[RetrievalGroundTruth]`:**
- Reads directly from `CUAD_v1.json` to access `answer_start` offsets
- Produces one `RetrievalGroundTruth` per (contract, category) pair

**Dataclass:**
```python
RetrievalGroundTruth(
    qa_id, contract_title, category, tier,
    is_positive, relevant_chunk_ids,
    relevant_chunk_indices, answer_spans
)
```

### Step 3: One-Time Preparation Script (`scripts/prepare_chunks.py`)

```
uv run python scripts/prepare_chunks.py [--max-chunk-chars 4000] [--overlap 200] [--output-dir data/cuad/chunked]
```

1. Load `CUAD_v1.json`, chunk all 510 contracts → `contract_chunks.jsonl`
2. Map all 20,910 QA pairs → `retrieval_labels.jsonl`
3. Self-validation: verify every positive answer found verbatim in ≥1 mapped chunk
4. Write `chunking_metadata.json` with aggregate stats
5. Print summary report

**Output files in `data/cuad/chunked/`:**

| File | Format | Contents |
|------|--------|----------|
| `contract_chunks.jsonl` | 1 line/chunk | chunk_id, text, char_start/end, section_header, strategy |
| `retrieval_labels.jsonl` | 1 line/QA pair | qa_id, category, tier, is_positive, relevant_chunk_ids |
| `chunking_metadata.json` | JSON | config, stats (total chunks, avg per contract, boundary crossings) |

### Step 4: Extend `CUADSample` (backward-compatible)

**File:** `src/data/cuad_loader.py`

- Add field: `ground_truth_offsets: list[tuple[int, int]] = field(default_factory=list)`
- In `_load_from_local` (line 171), capture: `[(a["answer_start"], a["answer_start"] + len(a["text"])) for a in answers]`
- Pass to `CUADSample` constructor
- Default empty list → no existing code breaks

---

## Part 2: Retrieval Implementation

### Step 5: Retriever Interface (`src/retrieval/base.py`)

```python
class BaseRetriever(ABC):
    @abstractmethod
    def index_contract(self, chunks: list[ContractChunk]) -> None: ...

    @abstractmethod
    def retrieve(self, query: str, k: int = 5) -> list[RetrievedChunk]: ...

@dataclass
class RetrievedChunk:
    chunk: ContractChunk
    score: float
    rank: int
```

### Step 6: BM25 Retriever (`src/retrieval/bm25.py`)

- Use `rank_bm25` library (lightweight, no external services)
- `index_contract()`: tokenize chunk texts, build BM25 index
- `retrieve(query, k)`: tokenize query, score against index, return top-k
- Per-contract index (each contract's chunks indexed separately)
- New dependency: `rank-bm25` (add via `uv add rank-bm25`)

### Step 7: Cross-Encoder Reranker (`src/retrieval/reranker.py`)

**Why reranking matters:**
BM25 is lexical — it matches on exact terms. Legal contracts use varied phrasing for the same concept (e.g., "indemnification" vs "hold harmless", "limitation of liability" vs "damages shall not exceed"). A cross-encoder reranker scores each (query, chunk) pair with full attention, catching semantic matches BM25 misses.

**Architecture: two-stage retrieval**
```
BM25 (retrieve top-20, fast, recall-oriented)
  → Cross-encoder reranker (rescore to top-5, precise, relevance-oriented)
    → LLM extraction
```

**Implementation:**

```python
class CrossEncoderReranker:
    """Reranks BM25 results using a cross-encoder model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int = 5) -> list[RetrievedChunk]:
        pairs = [(query, chunk.chunk.text) for chunk in chunks]
        scores = self.model.predict(pairs)
        # Re-sort by cross-encoder score, return top_k
        ...
```

**`RerankerRetriever(BaseRetriever)`** — wraps any `BaseRetriever`:
- `retrieve(query, k)`: calls inner retriever with `k * rerank_factor` (e.g., 20), reranks, returns top-k
- Composable: `RerankerRetriever(BM25Retriever(...), reranker=CrossEncoderReranker())`

**Model options:**

| Model | Size | Latency/chunk | Notes |
|-------|------|---------------|-------|
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | 22M params | ~2ms | Default. General-domain, fast, no GPU needed |
| `BAAI/bge-reranker-v2-m3` | 568M params | ~15ms | Stronger, multilingual. Use if accuracy matters more |
| Cohere Rerank v3 | API | ~50ms | API-based. Avoid for reproducibility |

**Recommendation:** Default to `ms-marco-MiniLM-L-6-v2`. It runs on CPU in ~2ms per chunk, so reranking 20 chunks adds <50ms per sample — negligible vs LLM latency.

**New dependency:** `sentence-transformers` (add via `uv add sentence-transformers`)

### ~~Step 7b: Dense Retriever~~ — Deferred

Dense embedding retrieval (bi-encoder) is out of scope for Phase 1. The cross-encoder reranker already captures semantic similarity. A full dense retriever would add complexity (embedding index, vector store) without clear benefit over BM25 + reranker for this dataset size.

---

## Part 3: Pipeline Integration

### Step 8: Retrieval Evaluation Metrics (`src/retrieval/metrics.py`)

```python
def recall_at_k(relevant_ids, retrieved_ids, k) -> float
def precision_at_k(relevant_ids, retrieved_ids, k) -> float
def mrr(relevant_ids, retrieved_ids) -> float
def retrieval_metrics_batch(labels, retrieved, k_values=[1,3,5,10]) -> dict
```

### Step 9: New Experiment Types in `src/experiments/pipeline.py`

**Add to `RUN_TYPE_LABELS`:**
```python
"B5": "retrieve_extract_bm25",
"B6": "retrieve_rerank_extract",
```

**Add to `BASELINE_TYPES`:**
```python
BASELINE_TYPES = {"B1", "B4", "B5", "B6"}
```

**New factory: `_make_b5_extract_fn(config, diagnostics)`:**
1. Load chunked contract index from `data/cuad/chunked/contract_chunks.jsonl`
2. For each sample:
   a. Get that contract's chunks from the index
   b. Build BM25 index for the contract
   c. Retrieve top-k chunks using the category question as query
   d. Concatenate retrieved chunk texts as the new context
   e. Pass reduced context to the same extraction prompt (reuse B1's `CONTRACTEVAL_PROMPT`)
   f. Return `ExtractionOutput` with additional retrieval metadata

**New factory: `_make_b6_extract_fn(config, diagnostics)`:**
1. Same as B5, but wraps BM25 retriever in `RerankerRetriever`
2. BM25 retrieves top-20 → cross-encoder reranks to top-5
3. Otherwise identical pipeline (same prompt, same parser)

**Key design decision:** Reuse the exact ContractEval prompt (B1) and parser — only the context changes (retrieved chunks instead of full contract). This is a clean ablation: same prompt, same parser, same evaluation. The only variable is retrieval quality.

**Three-way comparison isolates each component:**

| Comparison | What it tests |
|------------|---------------|
| B5 > B1 | Retrieval helps (reduced context is sufficient) |
| B5 < B1 | Retrieval loses information (BM25 misses relevant chunks) |
| B6 > B5 | Reranking recovers what BM25 misses (semantic matching matters) |
| B6 ~ B5 | BM25 is sufficient for this task (lexical matching is enough) |
| B6 > B1 | Full retrieve+rerank pipeline outperforms brute-force context |

**Hypothesis for rare categories:** B6 should show the largest improvement over B5 on rare categories (e.g., "Uncapped Liability", "Covenant Not To Sue") because these use the most varied language — exactly where semantic reranking compensates for BM25's lexical limitation.

**JSONL record extension** — add `retrieval` field:
```json
{
  "retrieval": {
    "method": "bm25",
    "k": 5,
    "retrieved_chunk_ids": ["CONTRACT__chunk_003", "CONTRACT__chunk_007"],
    "retrieval_recall": 1.0,
    "retrieval_mrr": 0.5,
    "context_chars_original": 54290,
    "context_chars_retrieved": 8200
  }
}
```

For B6, the `retrieval` field extends with reranker metadata:
```json
{
  "retrieval": {
    "method": "bm25+rerank",
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "bm25_candidates": 20,
    "k": 5,
    "retrieved_chunk_ids": ["CONTRACT__chunk_007", "CONTRACT__chunk_003"],
    "retrieval_recall": 1.0,
    "retrieval_mrr": 1.0,
    "context_chars_original": 54290,
    "context_chars_retrieved": 8200
  }
}
```

### Step 10: Retrieve-Extract Baseline (`src/baselines/retrieve_extract.py`)

```python
class RetrieveExtractBaseline(BaseAgent):
    def __init__(self, retriever: BaseRetriever, k: int = 5, ...): ...

    async def extract(self, contract_text, category, question) -> ExtractionResult:
        # 1. Get chunks for this contract
        # 2. Retrieve top-k
        # 3. Build reduced context
        # 4. Call LLM with CONTRACTEVAL_PROMPT + reduced context
        # 5. Parse response (reuse ZeroShotBaseline parser)
```

### ~~Step 11: Retrieval-Aware Prompt~~ — Not Needed

Reusing the exact ContractEval prompt from B1. No new prompt template needed. This keeps B1 vs B5 as a clean single-variable comparison.

### Step 12: Experiment Config (`configs/experiments/retrieval.yaml`)

```yaml
experiments:
  B5:
    type: retrieve_extract_bm25
    retrieval:
      method: bm25
      k: 5
      chunk_dir: data/cuad/chunked
    extraction:
      prompt: zero_shot  # reuse ContractEval prompt
      temperature: 0.0
      max_tokens: 4096

  B6:
    type: retrieve_rerank_extract
    retrieval:
      method: bm25+rerank
      bm25_candidates: 20        # BM25 retrieves top-20
      k: 5                       # reranker selects top-5
      reranker_model: cross-encoder/ms-marco-MiniLM-L-6-v2
      chunk_dir: data/cuad/chunked
    extraction:
      prompt: zero_shot  # reuse ContractEval prompt
      temperature: 0.0
      max_tokens: 4096
```

---

## Part 4: Dashboard Extension

### Step 13: Display Retrieval Metadata

| File | Change |
|------|--------|
| `dashboard/src/lib/types.ts` | Add `retrieval?` field to sample type |
| `dashboard/src/app/experiments/[runId]/tabs.tsx` | Show retrieval stats in Overview tab (context reduction %, retrieval recall) |
| `dashboard/src/app/experiments/[runId]/samples/[sampleId]/page.tsx` | Show retrieved chunks, highlight which were relevant |

This is lower priority and can be done after the pipeline works end-to-end.

---

## Part 5: Tests

### Step 14: Chunking Tests (`tests/test_chunker.py`)

- Section detection on synthetic contracts with known headers
- Chunking respects max/min size constraints
- Overlap applied correctly at sub-section splits
- Ground truth mapping: span in one chunk, span crossing boundary, negative sample
- Self-validation: answer text found verbatim in mapped chunk

### Step 15: Retrieval Tests (`tests/test_retrieval.py`)

- BM25 retriever indexes and retrieves correctly
- Cross-encoder reranker reorders results by semantic relevance
- `RerankerRetriever` composes BM25 + reranker correctly (top-20 → top-5)
- Retrieval metrics (recall@k, MRR) computed correctly
- End-to-end: chunk → index → retrieve → rerank → verify relevant chunks found

---

## Files Summary

### New Files (ordered by implementation sequence)

| # | File | Purpose |
|---|------|---------|
| 1 | `src/data/chunker.py` | Section detection + contract splitting |
| 2 | `src/data/chunk_index.py` | Answer-to-chunk mapping, retrieval ground truth |
| 3 | `scripts/prepare_chunks.py` | One-time dataset preparation script |
| 4 | `src/retrieval/__init__.py` | Package init + exports |
| 5 | `src/retrieval/base.py` | Abstract retriever interface |
| 6 | `src/retrieval/bm25.py` | BM25 retriever implementation |
| 7 | `src/retrieval/reranker.py` | Cross-encoder reranker + RerankerRetriever wrapper |
| 8 | `src/retrieval/metrics.py` | Recall@k, MRR, Precision@k |
| 9 | `src/baselines/retrieve_extract.py` | Retrieve-then-extract baseline (reuses ContractEval prompt) |
| 10 | `configs/experiments/retrieval.yaml` | B5/B6 experiment config |
| 11 | `tests/test_chunker.py` | Chunking + ground truth tests |
| 12 | `tests/test_retrieval.py` | Retrieval, reranking + metrics tests |

### Modified Files

| File | Change |
|------|--------|
| `src/data/cuad_loader.py` | Add `ground_truth_offsets` field to `CUADSample` |
| `src/data/__init__.py` | Export `ContractChunk`, `ChunkedContract`, etc. |
| `src/baselines/__init__.py` | Export `RetrieveExtractBaseline` |
| `src/experiments/pipeline.py` | Add B5/B6 to `RUN_TYPE_LABELS`, factory fns, branches in `run_experiment_pipeline()` |
| `src/experiments/runner.py` | Add optional `retrieval` field to JSONL record |
| `pyproject.toml` | Add `rank-bm25` and `sentence-transformers` dependencies |

---

## Verification Checklist

1. **Dataset prep:** `uv run python scripts/prepare_chunks.py` → completes <1min, 0 validation failures
2. **Spot check:** verify "Document Name" maps to preamble chunk, "Governing Law" maps to late-contract chunk
3. **Unit tests:** `uv run pytest tests/test_chunker.py tests/test_retrieval.py -v`
4. **Existing tests:** `uv run pytest tests/ -v` → all 81 tests still pass
5. **End-to-end B5:** `uv run python scripts/run_experiment.py --type B5 --model gpt-4.1-mini --samples-per-tier 5` → produces valid summary JSON
6. **End-to-end B6:** `uv run python scripts/run_experiment.py --type B6 --model gpt-4.1-mini --samples-per-tier 5` → produces valid summary JSON with reranker metadata
7. **Compare:** B1 vs B5 vs B6 on same samples → verify `context_chars_retrieved << context_chars_original`; check if B6 retrieval_recall ≥ B5 retrieval_recall
8. **Dashboard:** `cd dashboard && npm run build` → no errors; B5/B6 results visible in experiments list

---

## Architecture Diagram

```
                      ┌──────────────┐
                      │  CUAD_v1.json │
                      └──────┬───────┘
                             │
                      ┌──────▼───────┐
                      │   Chunker    │  ← Step 1: Section detection + splitting
                      │  (one-time)  │
                      └──────┬───────┘
                             │
                ┌────────────┼────────────┐
                ▼                         ▼
      ┌─────────────────┐     ┌───────────────────┐
      │ contract_chunks  │     │ retrieval_labels   │  ← Step 2: Ground truth mapping
      │    .jsonl        │     │    .jsonl          │
      └────────┬────────┘     └───────────────────┘
               │
      ┌────────▼────────┐
      │  BM25 Retriever │  ← Step 6: Per-contract indexing
      │  (top-20)       │
      └────────┬────────┘
               │
         ┌─────┴─────┐
         │           │
    B5 path      B6 path
         │           │
         │    ┌──────▼───────┐
         │    │ Cross-Encoder │  ← Step 7: Semantic reranking
         │    │  Reranker     │
         │    │  (top-5)      │
         │    └──────┬───────┘
         │           │
         └─────┬─────┘
               │
      ┌────────▼────────┐
      │  Top-k Chunks   │  ← Retrieved context (~8KB vs ~54KB)
      └────────┬────────┘
               │
      ┌────────▼────────┐
      │  ContractEval   │  ← Same B1 prompt, reduced context
      │    Prompt       │
      └────────┬────────┘
               │
      ┌────────▼────────┐
      │ ExtractionResult│  ← Same evaluation pipeline
      └─────────────────┘
```

## Experiment Comparison Matrix

| Experiment | Context | Retrieval | Reranking | Prompt | What it tests |
|------------|---------|-----------|-----------|--------|---------------|
| **B1** | Full contract | None | None | ContractEval | Baseline (brute force) |
| **B5** | BM25 top-k | BM25 | None | ContractEval | Does lexical retrieval help? |
| **B6** | BM25+rerank top-k | BM25 | Cross-encoder | ContractEval | Does semantic reranking add value? |

All three share the same prompt, parser, and evaluation — the only variable is how context is selected.
