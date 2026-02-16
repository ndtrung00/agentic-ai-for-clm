# B4 Over-Extraction Issue — gpt-4.1-mini

## Problem

B4 (Chain-of-Thought) with gpt-4.1-mini **never says "No related clause"** — it extracts clauses for every single sample, even when no clause exists in the contract.

| Symptom | Observed | Expected |
|---------|----------|----------|
| TN (true negatives) | **0** | ~15 (all negative samples) |
| FP (false positives) | **15** | ~0 |
| Clauses per sample | **10–28** | 1–3 |
| Jaccard | **0.123** | >0.50 |
| Precision | **0.634** | >0.80 |
| Laziness rate | 0.0% | Low but non-zero is fine |

The model over-extracts massively — high recall (0.867) but low precision (0.634) and very low span overlap. The laziness metric reads 0% but this is misleading: it masks the opposite problem (over-extraction).

## Root Causes

### 1. Parsing Bug (most likely)

The `parse_response` method in `chain_of_thought.py` tries to split the model's response into reasoning vs. answer using delimiters like "Final Answer:", "Answer:", etc. When the model doesn't produce any of these delimiters, the parser **falls back to treating the entire response as extracted clauses**:

```python
# If no delimiter found, use the full text as the answer
if not answer_section:
    answer_section = text
```

Then it splits on `\n\n`, so every paragraph of step-by-step reasoning becomes a "clause" — inflating clause counts to 20–28 per sample.

### 2. One-Sided Prompt

The CoT prompt includes anti-laziness instructions:

> "If you are uncertain whether a clause is relevant, INCLUDE IT. It is better to extract a potentially relevant clause than to miss one."

There is no counterbalancing instruction for precision. This pushes the model toward over-extraction with no guardrail.

### 3. No Output Format Enforcement

B4 doesn't require the model to clearly separate reasoning from the final answer. Without a structured output format (e.g., JSON or a mandatory "Final Answer:" section), the parser cannot reliably distinguish CoT reasoning from actual extracted clauses.

### 4. No System/User Message Separation

B1 (zero-shot) separates instructions (system prompt) from content (user message). B4 puts everything — instructions, contract text, and question — into a single user message. This makes instruction boundaries less clear for the model.

## Proposed Solutions

### 1. Fix the Parser

Check raw responses from the intermediate JSONL to determine:
- Does the model produce "Final Answer:" or similar delimiters that the regex misses?
- Or does the model not produce delimiters at all?

If delimiters exist but are missed → fix the regex patterns.
If no delimiters → enforce them via prompt changes (see #2).

### 2. Add Precision Guidance + Output Format to Prompt

Balance the anti-laziness instruction with precision guidance and enforce a clear answer delimiter:

> "Only extract sentences that **directly** address the Question. Do not include tangentially related sentences."
>
> "End your response with 'Final Answer:' followed only by the exact extracted sentences, or 'No related clause.' if nothing is relevant."

### 3. Separate System and User Messages

Refactor B4 to use the same system/user message split as B1:
- **System prompt**: Role, instructions, anti-laziness + precision balance, output format
- **User message**: Contract text + question only

This gives the model clearer instruction boundaries and aligns B4's architecture with B1 for a fairer comparison.

## Next Steps

1. Inspect raw responses from the B4 intermediate JSONL to confirm the parsing hypothesis
2. Apply prompt + parser fixes
3. Re-run B4/gpt-4.1-mini calibration
4. Compare results against the current run
