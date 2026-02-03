"""
DPO Training Script
Supports: Qwen, Llama, DeepSeek models
"""

import os
import torch
from dataclasses import dataclass, field
from typing import Optional
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    HfArgumentParser,
)
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import DPOTrainer, DPOConfig

from huggingface_hub import login
HF_TOKEN = os.getenv("HF_TOKEN")

try:
    login(token=HF_TOKEN)
    print("Logged in to Hugging Face")
except Exception as e:
    print(f"HF login failed: {e}")


@dataclass
class ScriptArguments:
    model_name: str = field(
        metadata={"help": "Model name or path"}
    )
    model_revision: str = field(
        default="main",
        metadata={"help": "Model revision"}
    )

    dataset_name: str = field(
        default="example-dataset",
        metadata={"help": "Dataset name from HuggingFace"}
    )
    dataset_split: str = field(
        default="train",
        metadata={"help": "Dataset split"}
    )

    use_lora: bool = field(
        default=True,
        metadata={"help": "Use LoRA"}
    )
    lora_r: int = field(
        default=16,
        metadata={"help": "LoRA rank"}
    )
    lora_alpha: int = field(
        default=32,
        metadata={"help": "LoRA alpha"}
    )
    lora_dropout: float = field(
        default=0.05,
        metadata={"help": "LoRA dropout"}
    )

    use_4bit: bool = field(
        default=True,
        metadata={"help": "Use 4-bit quantization"}
    )
    use_8bit: bool = field(
        default=False,
        metadata={"help": "Use 8-bit quantization"}
    )

    beta: float = field(
        default=0.1,
        metadata={"help": "DPO beta"}
    )
    loss_type: str = field(
        default="sigmoid",
        metadata={"help": "DPO loss type"}
    )

    output_dir: str = field(
        default="./dpo_output",
        metadata={"help": "Output directory"}
    )
    num_train_epochs: int = field(
        default=3,
        metadata={"help": "Number of epochs"}
    )
    per_device_train_batch_size: int = field(
        default=2,
        metadata={"help": "Batch size per device"}
    )
    gradient_accumulation_steps: int = field(
        default=4,
        metadata={"help": "Gradient accumulation steps"}
    )
    learning_rate: float = field(
        default=5e-5,
        metadata={"help": "Learning rate"}
    )
    max_length: int = field(
        default=1024,
        metadata={"help": "Maximum sequence length"}
    )
    max_prompt_length: int = field(
        default=512,
        metadata={"help": "Maximum prompt length"}
    )

    logging_steps: int = field(
        default=10,
        metadata={"help": "Logging steps"}
    )
    save_steps: int = field(
        default=100,
        metadata={"help": "Save steps"}
    )
    eval_steps: int = field(
        default=100,
        metadata={"help": "Eval steps"}
    )
    warmup_ratio: float = field(
        default=0.1,
        metadata={"help": "Warmup ratio"}
    )
    gradient_checkpointing: bool = field(
        default=True,
        metadata={"help": "Use gradient checkpointing"}
    )


def create_model_and_tokenizer(args: ScriptArguments):
    """
    Create model and tokenizer with optional quantization
    """
    # Configure quantization
    quantization_config = None
    if args.use_4bit:
        from transformers import BitsAndBytesConfig
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    elif args.use_8bit:
        from transformers import BitsAndBytesConfig
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True,
        )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name,
        revision=args.model_revision,
        trust_remote_code=True,
        local_files_only=args.model_name.startswith('/') or args.model_name.startswith('.'),
    )
    
    # Set padding token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    adapter_config_path = os.path.join(args.model_name, 'adapter_config.json')
    if os.path.exists(adapter_config_path):
        import json
        with open(adapter_config_path, 'r') as f:
            adapter_config = json.load(f)
        base_model_name = adapter_config.get('base_model_name_or_path')
        if base_model_name:
            print(f"Loading base model: {base_model_name}")
            model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                revision=args.model_revision,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.bfloat16 if not (args.use_4bit or args.use_8bit) else None,
                attn_implementation="eager",
                local_files_only=False, 
            )
            print(f"Loading adapter: {args.model_name}")
            model.load_adapter(args.model_name)
        else:
            raise ValueError(f"Adapter config at {adapter_config_path} does not have base_model_name_or_path")
    else:
        model = AutoModelForCausalLM.from_pretrained(
            args.model_name,
            revision=args.model_revision,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.bfloat16 if not (args.use_4bit or args.use_8bit) else None,
            attn_implementation="eager",
            local_files_only=args.model_name.startswith('/') or args.model_name.startswith('.'),
        )
    
    if args.use_4bit or args.use_8bit:
        model = prepare_model_for_kbit_training(model)
    
    if args.use_lora:
        target_modules = get_target_modules(args.model_name)
        
        peft_config = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            target_modules=target_modules,
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, peft_config)
        model.print_trainable_parameters()
    
    return model, tokenizer


def get_target_modules(model_name: str):
    """
    Get target modules for LoRA based on model architecture
    """
    model_name_lower = model_name.lower()
    
    if "qwen" in model_name_lower:
        return ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    elif "llama" in model_name_lower:
        return ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    elif "deepseek" in model_name_lower:
        return ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    else:
        return ["q_proj", "v_proj"]


def prepare_dataset(dataset_name: str, dataset_split: str, tokenizer):
    """
    Load and prepare dataset for DPO training
    
    DPO expects dataset with columns:
    - prompt: the input prompt
    - chosen: the preferred response
    - rejected: the less preferred response
    """
    # Load dataset
    dataset = load_dataset(dataset_name, split=dataset_split)
    
    print(f"Dataset loaded: {len(dataset)} examples")
    print(f"Dataset features: {dataset.features}")
    print(f"Sample example: {dataset[0]}")
    
    if 'prompt' in dataset.features and 'chosen' in dataset.features and 'rejected' in dataset.features:
        print("Dataset already in DPO format.")
    else:
        def format_dataset(example):
            """
            Format dataset for DPO
            """
            import random

            question = example.get('question', '')
            choices = example.get('choices', {})
            answer_key = example.get('answerKey', '')

            labels = choices.get('label', [])
            texts = choices.get('text', [])

            prompt = f"Question: {question}\n\nOptions:\n"
            for label, text in zip(labels, texts):
                prompt += f"{label}. {text}\n"
            prompt += "\nCorrect answer:"

            try:
                correct_idx = labels.index(answer_key)
                chosen = f" {answer_key}. {texts[correct_idx]}"
            except (ValueError, IndexError):
                chosen = f" {answer_key}"

            wrong_indices = [i for i, label in enumerate(labels) if label != answer_key]
            if wrong_indices:
                rejected_idx = random.choice(wrong_indices)
                rejected = f" {labels[rejected_idx]}. {texts[rejected_idx]}"
            else:
                rejected = f" {labels[0] if labels[0] != answer_key else labels[1] if len(labels) > 1 else 'A'}"

            return {
                'prompt': prompt,
                'chosen': chosen,
                'rejected': rejected,
            }

        dataset = dataset.map(
            format_dataset,
            remove_columns=dataset.column_names,
            desc="Formatting dataset"
        )

    dataset = dataset.filter(
        lambda x: len(x['chosen']) > 0 and len(x['rejected']) > 0,
        desc="Filtering examples"
    )

    print(f"Dataset after formatting: {len(dataset)} examples")

    return dataset


def main():
    parser = HfArgumentParser(ScriptArguments)
    args = parser.parse_args_into_dataclasses()[0]
    
    print("=" * 50)
    print(f"Training DPO model: {args.model_name}")
    print(f"Dataset: {args.dataset_name}")
    print(f"Output directory: {args.output_dir}")
    print("=" * 50)
    
    print("\nLoading model and tokenizer...")
    model, tokenizer = create_model_and_tokenizer(args)
    
    print("\nPreparing dataset...")
    train_dataset = prepare_dataset(args.dataset_name, args.dataset_split, tokenizer)
    
    if len(train_dataset) > 100:
        dataset_dict = train_dataset.train_test_split(test_size=0.1, seed=42)
        train_dataset = dataset_dict['train']
        eval_dataset = dataset_dict['test']
        print(f"Train size: {len(train_dataset)}, Eval size: {len(eval_dataset)}")
    else:
        eval_dataset = None
        print(f"Train size: {len(train_dataset)}")
    
    # Create DPO config
    training_args = DPOConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        warmup_ratio=args.warmup_ratio,
        gradient_checkpointing=args.gradient_checkpointing,
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False,
        eval_strategy="no", 
        save_strategy="steps",
        load_best_model_at_end=False,
        report_to="tensorboard",
        remove_unused_columns=False,
        beta=args.beta,
        loss_type=args.loss_type,
        max_length=args.max_length,
        max_prompt_length=args.max_prompt_length,
        save_total_limit=3, 
        save_on_each_node=True,
        resume_from_checkpoint=True, 
    )
    
    # Create DPO trainer
    print("\nInitializing DPO Trainer...")
    trainer = DPOTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        peft_config=None, 
    )
    
    print("\nStarting training...")
    try:
        import os
        checkpoints = [f for f in os.listdir(args.output_dir) if f.startswith('checkpoint-')] if os.path.exists(args.output_dir) else []
        resume_from = os.path.join(args.output_dir, sorted(checkpoints)[-1]) if checkpoints else None
        
        if resume_from:
            print(f"Resuming from checkpoint: {resume_from}")
        
        trainer.train(resume_from_checkpoint=resume_from)
        
        # Save final model
        print("\nSaving final model...")
        trainer.save_model(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)
        
        print(f"\nTraining complete! Model saved to {args.output_dir}")
        
    except Exception as e:
        print(f"\nTraining interrupted with error: {e}")
        print(f"Progress has been saved to checkpoints in {args.output_dir}")
        print("You can resume training by running the script again.")
        raise


if __name__ == "__main__":
    main()
