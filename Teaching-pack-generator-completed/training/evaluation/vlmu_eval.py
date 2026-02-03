# -*- coding: utf-8 -*-
"""
VMLU Evaluation Script

This script evaluates a language model on VMLU (Vietnamese Multiple-choice Language Understanding) dataset.

Usage:
    python vlmu_eval.py --model_path <model_path> --data_folder <data_folder> --output_dir <output_dir>

Environment Variables:
    - HF_TOKEN: HuggingFace token for model access
"""

import argparse
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration for VMLU evaluation."""
    DEFAULT_MODEL = "Qwen/Qwen3-4B"
    DEFAULT_DATA_FOLDER = "./data/vmlu"
    DEFAULT_SPLIT_FILE = "dev.jsonl"
    DEFAULT_OUTPUT_DIR = "./evaluation_results"
    MAX_NEW_TOKENS = 8
    BATCH_SIZE = 1  # For single sample inference


class VMLUEvaluator:
    """Handles VMLU dataset evaluation."""

    def __init__(self, config: Config):
        self.config = config
        self.tokenizer = None
        self.model = None

    def load_model(self, model_path: str, sub_model_path: Optional[str] = None):
        """Load the model and tokenizer."""
        logger.info(f"Loading model: {model_path}")

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            token=os.getenv("HF_TOKEN"),
            trust_remote_code=True,
            use_fast=False
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load base model
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            token=os.getenv("HF_TOKEN"),
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )

        # Load adapter if provided
        if sub_model_path:
            logger.info(f"Loading adapter: {sub_model_path}")
            self.model = PeftModel.from_pretrained(
                self.model,
                sub_model_path,
                token=os.getenv("HF_TOKEN")
            )
            # Merge LoRA weights
            logger.info("Merging LoRA weights...")
            self.model = self.model.merge_and_unload()

        self.model.eval()
        logger.info("Model loaded successfully")

    def load_dataset(self, data_path: Path) -> List[Dict[str, Any]]:
        """Load VMLU dataset from JSONL file."""
        if not data_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {data_path}")

        logger.info(f"Loading dataset: {data_path}")
        data = []
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))

        logger.info(f"Loaded {len(data)} samples")
        return data

    def format_prompt(self, question: str, choices: List[str]) -> str:
        """Format the prompt for multiple choice question."""
        lines = [question, ""]
        for i, choice in enumerate(choices):
            lines.append(f"{chr(65 + i)}. {choice}")
        lines.extend([
            "",
            "Chỉ trả lời 1 chữ cái A/B/C/D/E tương ứng đáp án đúng.",
            "Answer:"
        ])
        return "\n".join(lines)

    def extract_answer(self, text: str) -> str:
        """Extract the answer letter from generated text."""
        matches = re.findall(r"\b([A-E])\b", text.upper())
        return matches[-1] if matches else ""

    def evaluate_sample(self, sample: Dict[str, Any]) -> Dict[str, str]:
        """Evaluate a single sample."""
        question_id = str(sample.get("id", ""))
        question = sample.get("question", "")
        choices = sample.get("choices", [])
        gold_answer = str(sample.get("answer", "")).strip().upper()

        prompt = self.format_prompt(question, choices)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.config.MAX_NEW_TOKENS,
                do_sample=False
            )

        generated_text = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True
        ).strip()

        predicted_answer = self.extract_answer(generated_text)

        return {
            "id": question_id,
            "pred": predicted_answer,
            "gold": gold_answer,
            "generated_text": generated_text
        }

    def evaluate(self, model_path: str, data_folder: str, split_file: str, output_dir: str,
                 sub_model_path: Optional[str] = None, resume: bool = True):
        """Run the full evaluation."""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Load model
        self.load_model(model_path, sub_model_path)

        # Load dataset
        data_path = Path(data_folder) / split_file
        data = self.load_dataset(data_path)

        # Prepare output file
        model_name = model_path.replace("/", "-")
        if sub_model_path:
            model_name += f"_{sub_model_path.replace('/', '-')}"
        output_file = os.path.join(output_dir, f"{model_name}_{split_file.replace('.jsonl', '')}.csv")

        # Resume from existing results if available
        done_ids = set()
        if resume and os.path.exists(output_file):
            df = pd.read_csv(output_file)
            done_ids = set(df["id"].astype(str))
            logger.info(f"Resuming from {len(done_ids)} completed samples")
        else:
            df = pd.DataFrame(columns=["id", "pred", "gold", "generated_text"])

        # Evaluate samples
        start_time = time.time()
        new_samples = 0

        try:
            for sample in tqdm(data, desc="Evaluating"):
                sample_id = str(sample.get("id", ""))
                if sample_id in done_ids:
                    continue

                result = self.evaluate_sample(sample)
                df = pd.concat([df, pd.DataFrame([result])], ignore_index=True)

                # Save progress
                df.to_csv(output_file, index=False)
                done_ids.add(sample_id)
                new_samples += 1

        except KeyboardInterrupt:
            logger.info("Evaluation interrupted by user. Progress saved.")

        # Calculate accuracy
        if len(df) > 0:
            df["correct"] = df["pred"] == df["gold"]
            accuracy = df["correct"].mean()
            logger.info(".4f")
        else:
            accuracy = 0.0

        elapsed_time = time.time() - start_time
        logger.info(f"New samples processed: {new_samples}")
        logger.info(".2f")
        logger.info(f"Results saved to: {output_file}")

        return accuracy, output_file


def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description="VMLU Evaluation Script")
    parser.add_argument("--model_path", type=str, default=Config.DEFAULT_MODEL,
                       help="Path to the model")
    parser.add_argument("--sub_model_path", type=str, default=None,
                       help="Path to the adapter/sub-model (optional)")
    parser.add_argument("--data_folder", type=str, default=Config.DEFAULT_DATA_FOLDER,
                       help="Path to the data folder")
    parser.add_argument("--split_file", type=str, default=Config.DEFAULT_SPLIT_FILE,
                       help="Dataset split file name")
    parser.add_argument("--output_dir", type=str, default=Config.DEFAULT_OUTPUT_DIR,
                       help="Output directory for results")
    parser.add_argument("--no_resume", action="store_true",
                       help="Do not resume from existing results")

    args = parser.parse_args()

    # Initialize evaluator
    config = Config()
    evaluator = VMLUEvaluator(config)

    # Run evaluation
    accuracy, output_file = evaluator.evaluate(
        model_path=args.model_path,
        data_folder=args.data_folder,
        split_file=args.split_file,
        output_dir=args.output_dir,
        sub_model_path=args.sub_model_path,
        resume=not args.no_resume
    )

    logger.info("Evaluation completed successfully")


if __name__ == "__main__":
    main()


