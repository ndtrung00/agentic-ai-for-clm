# Experiment Model Tracking

## Proprietary Models (official runs, neg_ratio=0.7, spt=0)

| Model                  | Provider  | B1  | B4  | M0  | M1  | M7  | M8  | M6  |
| ---------------------- | --------- | --- | --- | --- | --- | --- | --- | --- |
| Claude Sonnet 4        | Anthropic | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☑   |
| Claude Sonnet 4.6      | Anthropic | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☑   |
| Claude Opus 4.6        | Anthropic | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☑   |
| Claude Haiku 4.5       | Anthropic | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☑   |
| GPT 4.1                | OpenAI    | ☑   | ☐   | ☑   | ☑   | ☐   | ☐   | ☐   |
| GPT 4.1 Mini           | OpenAI    | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☐   |
| GPT 4.1 Nano           | OpenAI    | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☐   |
| Gemini 2.5 Pro         | Google    | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☐   |
| Gemini 2.5 Flash       | Google    | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☐   |
| Gemini 3 Flash Preview | Google    | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☐   |
| Gemini 3.1 Pro Preview | Google    | ☑   | ☑   | ☑   | ☑   | ☐   | ☐   | ☐   |

**Completed: 51 / 77** (11 models × 7 configs)

## Config Key

| Config | Type                      | Description                                        |
| ------ | ------------------------- | -------------------------------------------------- |
| B1     | Zero-shot                 | ContractEval replication (single agent)            |
| B4     | Chain-of-thought          | CoT reasoning (single agent)                       |
| M0     | Classify-then-extract     | Agent 1 classifies, Agent 2 extracts (two-stage)   |
| M1     | Full multi-agent          | LLM router → specialist → validation               |
| M7     | Extract-then-verify       | B4 extracts → specialist verifies/refines/recovers |
| M8     | Ensemble                  | B4 + specialist parallel → resolver adjudicates    |
| M6     | Combined prompts ablation | All specialist prompts in single agent             |
