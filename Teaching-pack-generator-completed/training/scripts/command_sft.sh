#!/bin/bash
# Train SFT

python src/train_sft.py \
    --model_name "Qwen/Qwen2.5-3B" \
    --dataset_name "vlsp-2023-vllm/comprehension" \
    --dataset_split "train" \
    --output_dir "./model_outputs/sft_model" \
    --use_lora True \
    --lora_r 16 \
    --lora_alpha 32 \
    --lora_dropout 0.05 \
    --use_4bit True \
    --num_train_epochs 3 \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 4 \
    --learning_rate 5e-5 \
    --max_length 1024 \
    --logging_steps 10 \
    --save_steps 100 \
    --warmup_ratio 0.1 \
    --gradient_checkpointing True