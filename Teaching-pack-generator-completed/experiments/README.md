# Experiments Overview

This folder contains evaluation scripts for multi-agent and single-agent teaching pack generation.

## Scripts

- `mas_evaluation_experiment.py`: Multi-agent pipeline + evaluation
- `single_agent_evaluation_experiment.py`: Single-agent pipeline + evaluation
- `mas_evaluation_experiment_vllm.py`: Multi-agent pipeline using a local vLLM backend
- `mas_evaluation_experiment_vllm_qwen3_grpo_dpo.py`: Multi-agent pipeline with Qwen3 GRPO/DPO vLLM settings
- `mas_evaluation_experiment_vllm_qwen3_grpo_dpo_variant.py`: Variant vLLM configuration (alternate LoRA)
- `single_agent_evaluation_experiment_vllm_qwen3_grpo_dpo.py`: Single-agent pipeline with Qwen3 GRPO/DPO vLLM settings

## Metrics

The evaluation uses three metrics:

1. Content Accuracy (Acc)
- Per slide and per quiz question factual correctness.

2. Concept Coverage (EM)
- Semantic coverage of key concepts and skills from the ground truth.

3. Educational Soundness (ES)
- Grade level appropriateness
- Logical progression
- Quiz alignment with taught content
- Cognitive load management

## Example Commands

```bash
python experiments/mas_evaluation_experiment.py \
  --config config/default.yaml \
  --lesson_summary data/raw/lesson_summary.json \
  --ground_truth data/processed/ground_truth.json

python experiments/single_agent_evaluation_experiment.py \
  --config config/default.yaml \
  --lesson_summary data/raw/lesson_summary.json \
  --ground_truth data/processed/ground_truth.json
```
