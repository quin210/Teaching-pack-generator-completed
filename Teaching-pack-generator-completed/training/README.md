# LLM Alignment Training Framework

## Overview

This repository provides a comprehensive framework for aligning Large Language Models (LLMs) using state-of-the-art techniques including Supervised Fine-Tuning (SFT), Direct Preference Optimization (DPO), and Group Relative Policy Optimization (GRPO). The framework is designed to facilitate research and development in LLM alignment, supporting multiple model architectures and datasets.

## Training Recipe

We operationalize the competence-ethics target with a staged training recipe in which each phase contributes a distinct control mechanism for teacher-like behavior under classroom constraints. The phases are complementary: supervised fine-tuning (SFT) instills a stable procedural prior, direct preference optimization (DPO) sharpens norm-compliant decision boundaries via paired contrasts, and group-relative policy optimization (GRPO) refines behavior in genuine multi-objective regimes where no single canonical response is adequate.

## Technical Parameters

### Supervised Fine-Tuning (SFT)
```python
training_args = TrainingArguments(
    output_dir=args.output_dir,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,
    num_train_epochs=2,
    learning_rate=2e-4,
    logging_steps=10,
    save_steps=500,
    save_total_limit=2,
    bf16=True,
    report_to="none",
)
```

### Direct Preference Optimization (DPO)
```bash
--use_4bit True \
--beta 0.1 \
--loss_type "sigmoid" \
--num_train_epochs 3 \
--per_device_train_batch_size 2 \
--gradient_accumulation_steps 4 \
--learning_rate 5e-5 \
--max_length 1024 \
--max_prompt_length 512 \
--logging_steps 10 \
--save_steps 100 \
--eval_steps 100 \
--warmup_ratio 0.1 \
--gradient_checkpointing True
```

### Group Relative Policy Optimization (GRPO)
```python
args = GRPOConfig(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=1e-5,
    num_train_epochs=1,
    logging_steps=5,
    save_steps=200,
    bf16=torch.cuda.is_available(),
    fp16=False,
    report_to="none",
    remove_unused_columns=False,
)
# NUM_GENERATIONS = 8
```

## Features

- **Supervised Fine-Tuning (SFT)**: Adapt pre-trained models to specific tasks using labeled instruction-response pairs
- **Direct Preference Optimization (DPO)**: Optimize models using preference data without explicit reward modeling
- **Group Relative Policy Optimization (GRPO)**: Advanced reinforcement learning method for LLM alignment
- **Multi-Model Support**: Compatible with Qwen, Llama, DeepSeek, and other transformer-based architectures
- **LoRA Integration**: Efficient parameter-efficient fine-tuning using Low-Rank Adaptation
- **Comprehensive Evaluation**: Built-in evaluation scripts for various benchmarks and datasets

## Project Structure

```
├── scripts/                    # Training command scripts
│   ├── command_sft.sh         # SFT training command
│   ├── command_dpo.sh         # DPO training command
│   └── command_grpo.sh        # GRPO training command
├── src/                       # Training scripts
│   ├── train_sft.py           # SFT training implementation
│   ├── train_dpo.py           # DPO training implementation
│   └── train_grpo.py          # GRPO training implementation
├── evaluation/                # Model evaluation scripts
│   ├── GeneralKnowledge_eval.py
│   ├── ViLLM_eval.py
│   └── vnhsge_eval.py
├── data/                      # Dataset storage (create as needed)
├── models/                    # Model checkpoints and outputs (create as needed)
├── docs/                      # Documentation
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Requirements

- Python 3.8+
- PyTorch 2.0+
- CUDA-compatible GPU (recommended for training)
- Hugging Face account with access tokens for model downloads

## Installation


1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up Hugging Face authentication:
```bash
export HF_TOKEN=your_huggingface_token
```

## Usage

### Supervised Fine-Tuning (SFT)

SFT adapts pre-trained language models to follow instructions by training on pairs of instructions and desired responses.

**Command:**
```bash
bash scripts/command_sft.sh
```

**Key Parameters:**
- `model_name`: Pre-trained model to fine-tune (e.g., "Qwen/Qwen2-7B")
- `dataset_name`: Hugging Face dataset for training
- `use_lora`: Enable LoRA for parameter-efficient training
- `learning_rate`: Learning rate for optimization
- `num_train_epochs`: Number of training epochs

### Direct Preference Optimization (DPO)

DPO optimizes language models using preference data, learning from comparisons between preferred and dispreferred responses without requiring explicit reward modeling.

**Command:**
```bash
bash scripts/command_dpo.sh
```

**Key Parameters:**
- `model_name`: Base model for DPO training
- `dataset_name`: Preference dataset (e.g., containing chosen/rejected pairs)
- `beta`: DPO regularization parameter
- `use_lora`: Enable LoRA adaptation

### Group Relative Policy Optimization (GRPO)

GRPO implements an advanced reinforcement learning approach for LLM alignment, utilizing group-based relative policy optimization techniques.

**Command:**
```bash
bash scripts/command_grpo.sh
```

**Key Parameters:**
- `model_name`: Model to optimize
- `dataset_name`: Training dataset
- `group_size`: Size of comparison groups for relative optimization

## Evaluation

The framework includes evaluation scripts for assessing model performance on various benchmarks:

- **General Knowledge Evaluation**: `evaluation/GeneralKnowledge_eval.py`
- **ViLLM Evaluation**: `evaluation/ViLLM_eval.py`
- **VNHSGE Evaluation**: `evaluation/vnhsge_eval.py`

Run evaluations using the respective scripts with appropriate model paths and dataset configurations.

## Configuration

Training scripts use Hugging Face's `HfArgumentParser` for configuration. Key configuration options include:

- Model and dataset specifications
- Training hyperparameters (learning rate, batch size, epochs)
- LoRA configuration for parameter-efficient training
- Quantization settings (4-bit, 8-bit)
- Logging and checkpointing options

## Best Practices

1. **Environment Setup**: Use a dedicated Python environment to avoid dependency conflicts
2. **GPU Memory**: Monitor GPU memory usage and adjust batch sizes accordingly
3. **Checkpointing**: Enable regular checkpointing to resume training if interrupted
4. **Evaluation**: Regularly evaluate models during training to monitor alignment progress
5. **Data Quality**: Ensure high-quality, diverse training data for optimal results

## Troubleshooting

- **CUDA Out of Memory**: Reduce batch size or enable gradient checkpointing
- **Hugging Face Authentication**: Ensure valid HF_TOKEN is set
- **Dataset Loading Issues**: Verify dataset names and access permissions
- **LoRA Training**: Check LoRA configuration for target modules

## License

This project is released under the MIT License. See LICENSE file for details.

## Contributing

Contributions are welcome. Please ensure that all changes maintain code quality and include appropriate documentation.