#!/bin/bash
# Train GRPO for DeepSeek-R1-Distill-Qwen-7B from SFT checkpoint
# cd /network-volume/code/grpo && source ../.venv/bin/activate && bash train_deepseek_from_sft.sh

python src/train_grpo.py \
    --model_name "/network-volume/code/DeepSeek-R1-Distill-Qwen-7B_sft_comprehension" \
    --dataset_name "vlsp-2023-vllm/comprehension" \
    --dataset_split "test" \
    --output_dir "./model_outputs/DeepSeek-R1-Distill-Qwen-7B_grpo_from_sft" \
    --use_lora True \
    --lora_r 16 \
    --lora_alpha 32 \
    --lora_dropout 0.05 \
    --use_4bit True \
    --num_generations 4 \
    --temperature 0.7 \
    --top_k 50 \
    --top_p 0.95 \
    --num_train_epochs 3 \
    --per_device_train_batch_size 1 \
    --gradient_accumulation_steps 8 \
    --learning_rate 5e-5 \
    --max_length 1024 \
    --max_prompt_length 512 \
    --logging_steps 10 \
    --save_steps 100 \
    --eval_steps 100 \
    --warmup_ratio 0.1 \
    --gradient_checkpointing True
