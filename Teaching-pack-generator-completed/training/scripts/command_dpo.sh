#!/bin/bash
# Train DPO

python src/train_dpo.py \
    --model_name "../model_outputs/sft_model" \
    --dataset_name "data/dataset_DPO/dataset.json" \
    --dataset_split "train" \
    --output_dir "./model_outputs/dpo_model" \
    --use_lora True \
    --lora_r 16 \
    --lora_alpha 32 \
    --lora_dropout 0.05 \
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
    --warmup_ratio 0.1 \
    --gradient_checkpointing True
