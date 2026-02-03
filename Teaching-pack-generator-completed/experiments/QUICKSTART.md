# Quickstart

This quickstart mirrors the root README.

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Provide API keys:

```bash
cp .env.example .env
# Set GEMINI_API_KEY in .env
```

3. Run an evaluation script:

```bash
python experiments/mas_evaluation_experiment.py \
  --config config/default.yaml \
  --lesson_summary data/raw/lesson_summary.json \
  --ground_truth data/processed/ground_truth.json
```
