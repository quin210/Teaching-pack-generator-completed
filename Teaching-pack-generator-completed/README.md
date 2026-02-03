# No One Left Behind, No One Held Back: Multi-Agent Teaching Packs for Group-Personalized Classrooms

This repository contains the experimental code for generating and evaluating group-personalized teaching packs with a multi-agent pipeline. The focus is on reproducible evaluation for the paper, not production deployment.

## Quick Start

1. Create a virtual environment (Python 3.12 recommended).
2. Install dependencies.
3. Set required API keys.
4. Run evaluation scripts.

```bash
pip install -r requirements.txt
cp .env.example .env
# Set GEMINI_API_KEY in .env

python experiments/mas_evaluation_experiment.py \
  --config config/default.yaml \
  --lesson_summary data/raw/lesson_summary.json \
  --ground_truth data/processed/ground_truth.json

python experiments/single_agent_evaluation_experiment.py \
  --config config/default.yaml \
  --lesson_summary data/raw/lesson_summary.json \
  --ground_truth data/processed/ground_truth.json
```

## Reproducibility Notes

- Seeds are configured in `config/default.yaml`.
- Some variability may remain due to nondeterminism in GPU kernels or LLM sampling.
- Evaluation results are saved under `results/`.

## Dataset

The original datasets and lesson materials are not distributed in this repository due to licensing and privacy constraints. Place your inputs under:

- `data/raw/` for raw lesson summaries or PDF files
- `data/processed/` for ground-truth JSON artifacts

## Environment

- Python: 3.12
- GPU: optional (required for some local LLM variants)

### Environment Variables

- `GEMINI_API_KEY` (required for evaluation)
- `HF_TOKEN` (required for Hugging Face generation in `mas_evaluation_experiment_qwen.py`)
- `VLLM_API_KEY` (optional for vLLM/OpenAI-compatible servers)

## Project Structure

```
config/
  default.yaml

data/
  raw/
  processed/

experiments/
  mas_evaluation_experiment.py
  single_agent_evaluation_experiment.py
  mas_evaluation_experiment_vllm.py
  mas_evaluation_experiment_vllm_qwen3_grpo_dpo.py
  single_agent_evaluation_experiment_vllm_qwen3_grpo_dpo.py

results/

src/
  agents/
  api/
  data/
  handlers/
  llm/
  models/
  utils/
```

## Configuration

`config/default.yaml` controls:

- model names
- evaluation settings
- number of groups and students
- output paths
- random seeds

## License

MIT
