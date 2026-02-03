#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM

from peft import LoraConfig, get_peft_model
from trl import GRPOTrainer, GRPOConfig  # TRL supports GRPOTrainer in recent versions


# ----------------------------
# Config
# ----------------------------
MODEL_NAME = "<ANONYMIZED_MODEL_NAME>"   # Use Llama-3.1-8B model from Hugging Face
DATASET_NAME = "<ANONYMIZED_DATASET_NAME>"
OUTPUT_DIR = "<ANONYMIZED_OUTPUT_DIR>"

NUM_GENERATIONS = 8  # số completion per prompt cho GRPO (4-8 ok, 16 tốt nhưng tốn)
MAX_NEW_TOKENS = 512


# ----------------------------
# Utilities: extract final answer
# ----------------------------
ANSWER_MARKERS = [
    r"####\s*([^\n\r]+)",
    r"(?:the\s*answer\s*is|answer|result)\s*[:：]\s*([^\n\r]+)",
]

def normalize_answer(s: str) -> str:
    s = (s or "").strip()
    # remove latex $
    s = s.replace("$", "").strip()
    # change decimal comma to dot if needed
    s = s.replace(",", ".")
    # remove trailing dot
    s = s.rstrip(" .。;；")
    return s

def extract_final_answer(text: str) -> str:
    """Best-effort: find answer after markers, else last number-like token, else last line."""
    if not text:
        return ""

    t = text.strip()

    # 1) markers
    for pat in ANSWER_MARKERS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            ans = m.group(1).strip()
            ans = re.split(r"[\n\r]+", ans)[0].strip()
            return normalize_answer(ans)

    # 2) last non-empty line
    lines = [ln.strip() for ln in re.split(r"[\r\n]+", t) if ln.strip()]
    if lines:
        last = normalize_answer(lines[-1])
        # nếu line quá dài, thử tìm số cuối
        if len(last) > 120:
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:/\d+)?", t)
            if nums:
                return normalize_answer(nums[-1])
        return last

    return ""


def answers_match(pred: str, gold: str) -> bool:
    """Loose match for numeric answers."""
    p = normalize_answer(pred)
    g = normalize_answer(gold)

    if not p or not g:
        return False

    # exact string match
    if p == g:
        return True

    # numeric float match (if both parse)
    def to_float(x: str) -> Optional[float]:
        try:
            # fraction a/b
            if "/" in x:
                a, b = x.split("/", 1)
                return float(a) / float(b)
            return float(x)
        except Exception:
            return None

    pf, gf = to_float(p), to_float(g)
    if pf is not None and gf is not None:
        return math.isclose(pf, gf, rel_tol=1e-4, abs_tol=1e-6)

    return False


# ----------------------------
# Reward functions for GRPO
# TRL expects reward functions that take (prompts, completions, **kwargs) and return List[float]
# We'll compute multiple rewards and sum them.
# ----------------------------
def reward_correctness(prompts: List[str], completions: List[str], **kwargs) -> List[float]:
    """Reward 1.0 if final answer matches gold (reference_solution), else 0.0."""
    golds = kwargs.get("reference_solution", None)  # list[str]
    if golds is None:
        # fallback: no gold -> give zero
        return [0.0] * len(completions)

    rewards = []
    for comp, gold in zip(completions, golds):
        pred = extract_final_answer(comp)
        rewards.append(1.0 if answers_match(pred, gold) else 0.0)
    return rewards


def reward_format(prompts: List[str], completions: List[str], **kwargs) -> List[float]:
    """
    Encourage a clear final line. Reward if contains 'Answer:' or 'The answer is:' or '####'.
    """
    rewards = []
    for comp in completions:
        c = comp.lower()
        ok = ("answer" in c) or ("the answer" in c) or ("####" in comp)
        rewards.append(1.0 if ok else 0.0)  # Increased reward from 0.2 to 1.0
    return rewards


def reward_mathematical_content(prompts: List[str], completions: List[str], **kwargs) -> List[float]:
    """Reward for containing mathematical expressions or numbers."""
    import re
    rewards = []
    for comp in completions:
        # Check for mathematical expressions, numbers, or LaTeX
        has_math = bool(re.search(r'[\d\+\-\*/\^\(\)\[\]\{\}\\$]', comp))
        has_sqrt = '\\sqrt' in comp or 'sqrt' in comp.lower()
        has_frac = '\\frac' in comp or 'frac' in comp.lower()
        score = 0.0
        if has_math:
            score += 0.3
        if has_sqrt or has_frac:
            score += 0.2
        rewards.append(score)
    return rewards


def reward_no_think_tag(prompts: List[str], completions: List[str], **kwargs) -> List[float]:
    """Penalty if model leaks <think> tags (optional)."""
    rewards = []
    for comp in completions:
        if "<think>" in comp or "</think>" in comp:
            rewards.append(-0.2)
        else:
            rewards.append(0.0)
    return rewards


# ----------------------------
# Build prompt strings
# If your dataset prompt is already a string, we keep it.
# If you want chat format, you can wrap it with a system instruction here.
# ----------------------------
SYSTEM_PROMPT = (
    "You are a Math assistant. Solve the problem clearly, present reasonable steps, "
    "and end with #### followed by the final answer. "
    "Example: #### \\sqrt{5}"
)

def build_prompt(user_prompt: str, tokenizer=None) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Problem:\n{user_prompt.strip()}"}
    ]
    if tokenizer and hasattr(tokenizer, 'apply_chat_template'):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        return f"{SYSTEM_PROMPT}\n\nProblem:\n{user_prompt.strip()}\n"


def main():
    # Load tokenizer first for chat template
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load chat template for Llama
    if tokenizer.chat_template is None:
        tokenizer.chat_template = """{% for message in messages %}{{ '<|start_header_id|>' + message['role'] + '<|end_header_id|>' }}

{{ message['content'] }}{% if not loop.last %}{{ '<|eot_id|>' }}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ '<|start_header_id|>assistant<|end_header_id|>' }}{% endif %}"""

    # Load dataset from Hugging Face
    ds = load_dataset(DATASET_NAME, split="train", download_mode='reuse_cache_if_exists')

    # Map to final prompt text used for generation
    def _map(ex):
        return {
            "prompt_text": build_prompt(ex["prompt"], tokenizer),
            # gold answer (short) used by reward_correctness
            "reference_solution": str(ex.get("reference_solution", "")).strip(),
        }

    ds = ds.map(_map)

    # 4-bit load to fit 8B model
    from transformers import BitsAndBytesConfig
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=quantization_config,
        device_map="auto",
    )

    # LoRA
    lora_cfg = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "up_proj", "down_proj", "gate_proj"],
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    # TRL GRPOConfig
    args = GRPOConfig(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,     # GRPO tốn do num_generations
        gradient_accumulation_steps=8,
        learning_rate=1e-5,
        num_train_epochs=1,
        logging_steps=5,  # More frequent logging
        save_steps=200,
        bf16=torch.cuda.is_available(),
        fp16=False,
        report_to="none",
        remove_unused_columns=False,
    )

    # GRPO Trainer
    trainer = GRPOTrainer(
        model=model,
        args=args,
        train_dataset=ds,
        # reward functions list
        reward_funcs=[reward_correctness, reward_format, reward_mathematical_content, reward_no_think_tag],
    )

    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    print("Done. Saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()