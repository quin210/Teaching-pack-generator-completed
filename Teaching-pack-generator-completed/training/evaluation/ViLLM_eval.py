"""
ViLLM Evaluation Script

This script evaluates a language model on Vietnamese LLM benchmark using Gemini as a judge.

Usage:
    python ViLLM_eval.py

Environment Variables:
    - GEMINI_API_KEY: Gemini API key
    - HF_TOKEN: HuggingFace token (optional)
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional, Tuple, List

import pandas as pd
import torch
from datasets import load_dataset
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

import google.generativeai as genai
from google.genai import types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration for the evaluation script."""
    BASE_MODEL = "<ANONYMIZED_BASE_MODEL>"
    MODEL_PATH = "example-model"
    DATASET_NAME = "vlsp-2023-vllm/wikipediaqa_vi"
    DATASET_SPLIT = "test"
    BASE_DIR = "./results"
    SAVE_PATH = os.path.join(BASE_DIR, "results.csv")
    MAX_RETRIES = 3
    SLEEP_TIME = 2
    MAX_NEW_TOKENS = 256
    TEMPERATURE = 0.7
    TOP_P = 0.9


class ModelManager:
    """Handles model loading and inference."""

    def __init__(self, base_model: str, model_path: str):
        self.base_model = base_model
        self.model_path = model_path
        self.model: Optional[Any] = None  # AutoModelForCausalLM
        self.tokenizer: Optional[Any] = None  # AutoTokenizer

    def load_model(self) -> Tuple[Any, Any]:
        """Load model and tokenizer."""
        try:
            logger.info(f"Loading tokenizer: {self.base_model}")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.base_model,
                token=os.getenv("HF_TOKEN"),
                trust_remote_code=True
            )

            logger.info(f"Loading model: {self.model_path}")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                token=os.getenv("HF_TOKEN"),
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True
            )
            self.model.eval()  # type: ignore

            logger.info("Model loaded successfully")
            return self.model, self.tokenizer

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def generate_answer(self, prompt: str) -> Dict[str, Any]:
        """Generate answer for a prompt."""
        if not self.model or not self.tokenizer:
            raise ValueError("Model not loaded. Call load_model() first.")

        try:
            inputs = self.tokenizer(  # type: ignore
                prompt,
                return_tensors="pt"
            ).to(self.model.device)  # type: ignore

            with torch.no_grad():
                outputs = self.model.generate(  # type: ignore
                    **inputs,
                    max_new_tokens=Config.MAX_NEW_TOKENS,
                    do_sample=True,
                    temperature=Config.TEMPERATURE,
                    top_p=Config.TOP_P,
                )

            text = self.tokenizer.decode(  # type: ignore
                outputs[0],
                skip_special_tokens=True
            )

            # Try to parse JSON response
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"final": None, "raw": text}

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {"final": None, "raw": f"Error: {e}"}


class JudgeManager:
    """Handles judgment using Gemini API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)  # type: ignore
        self.client = genai.GenerativeModel("gemini-2.0-flash")  # type: ignore

    def judge_answer(
        self,
        question: str,
        choices: Dict[str, List[str]],
        gold: str,
        model_output: Dict[str, Any],
        max_retries: int = Config.MAX_RETRIES
    ) -> Dict[str, Any]:
        """Judge the model's answer using Gemini."""
        prompt = f"""
Question: {question}
Choices: {choices}
Correct Answer: {gold}
Model Output: {model_output}

Judge if the model's answer is correct. Return JSON with:
{{"is_correct": true/false, "similarity": 0.0-1.0, "reason": "explanation"}}
"""

        for attempt in range(max_retries):
            try:
                response = self.client.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(  # type: ignore
                        response_mime_type="application/json",
                        temperature=0
                    )
                )

                if response.text:
                    return json.loads(response.text)
                else:
                    logger.warning("Empty response from Gemini")
                    continue

            except Exception as e:
                logger.warning(
                    f"Judgment attempt {attempt + 1} failed: {e}"
                )
                if attempt == max_retries - 1:
                    return {
                        "is_correct": None,
                        "similarity": None,
                        "reason": "Failed after retries"
                    }

        return {
            "is_correct": None,
            "similarity": None,
            "reason": "Failed after retries"
        }


class EvaluationManager:
    """Manages the evaluation process."""

    def __init__(self):
        self.model_manager = ModelManager(Config.BASE_MODEL, Config.MODEL_PATH)
        self.judge_manager = None

    def setup(self) -> None:
        """Setup evaluation environment."""
        # Create results directory
        os.makedirs(Config.BASE_DIR, exist_ok=True)

        # Validate API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable required")

        self.judge_manager = JudgeManager(api_key)

        # Load model
        self.model_manager.load_model()

    def load_dataset(self):
        """Load evaluation dataset."""
        logger.info(f"Loading dataset: {Config.DATASET_NAME}")
        dataset = load_dataset(
            Config.DATASET_NAME,
            split=Config.DATASET_SPLIT
        )
        logger.info(f"Dataset loaded: {len(dataset)} samples")
        return dataset

    def load_existing_results(self) -> Tuple[List[Dict], set]:
        """Load existing results for resume functionality."""
        if not os.path.exists(Config.SAVE_PATH):
            return [], set()

        try:
            df_old = pd.read_csv(Config.SAVE_PATH)
            done_questions = set(df_old["question"])
            results = df_old.to_dict("records")
            logger.info(f"Loaded {len(results)} existing results")
            return results, done_questions
        except Exception as e:
            logger.warning(f"Failed to load existing results: {e}")
            return [], set()

    def save_results(self, results: List[Dict]) -> None:
        """Save results to CSV."""
        try:
            df = pd.DataFrame(results)
            df.to_csv(Config.SAVE_PATH, index=False)
            logger.info(f"Results saved to {Config.SAVE_PATH}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    def build_prompt(self, question: str, choices: Dict[str, List[str]]) -> str:
        """Build evaluation prompt."""
        opts = "\n".join([
            f"{label}. {text}"
            for label, text in zip(choices["labels"], choices["text"])
        ])

        return f"""You are an AI assistant for multiple choice questions.
Choose only 1 correct answer (A/B/C/D).

Question:
{question}

Options:
{opts}

Answer in JSON format:
{{
  "final": "A|B|C|D",
  "explanation": "brief explanation"
}}
"""

    def evaluate_sample(
        self,
        example: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a single sample."""
        question = example["question"]
        choices = example["choices"]
        gold = example["answerKey"]

        # Build prompt
        prompt = self.build_prompt(question, choices)

        # Generate answer
        model_out = self.model_manager.generate_answer(prompt)

        # Extract prediction
        pred = model_out.get("final")
        acc = int(pred == gold) if pred is not None else None

        # Judge answer
        judge_result = self.judge_manager.judge_answer(  # type: ignore
            question, choices, gold, model_out
        )

        return {
            "question": question,
            "gold": gold,
            "model_output": model_out,
            "prediction": pred,
            "accuracy": acc,
            "judge_correct": judge_result.get("is_correct"),
            "judge_similarity": judge_result.get("similarity"),
            "judge_reason": judge_result.get("reason", "")
        }

    def run_evaluation(self) -> None:
        """Run the complete evaluation."""
        # Setup
        self.setup()

        # Load data
        dataset = self.load_dataset()

        # Load existing results
        results, done_questions = self.load_existing_results()

        # Evaluation loop
        logger.info("Starting evaluation...")
        for ex in tqdm(dataset, desc="Evaluating"):
            question = ex["question"]  # type: ignore

            # Skip if already done
            if question in done_questions:
                continue

            # Evaluate sample
            result = self.evaluate_sample(ex)  # type: ignore
            results.append(result)

            # Save after each sample
            self.save_results(results)

            # Rate limiting
            time.sleep(Config.SLEEP_TIME)

        # Final statistics
        df = pd.DataFrame(results)
        total_questions = len(df)
        num_correct = df["judge_correct"].sum()

        judge_accuracy = num_correct / total_questions if total_questions > 0 else 0

        logger.info("Evaluation complete")
        logger.info(f"Judge Accuracy: {judge_accuracy:.4f}")
        logger.info(f"Correct / Total: {num_correct} / {total_questions}")

        # Export to Excel
        excel_path = "eval_results.xlsx"
        df.to_excel(excel_path, index=False)
        logger.info(f"Results exported to {excel_path}")


def main() -> None:
    """Main function."""
    evaluator = EvaluationManager()
    evaluator.run_evaluation()


if __name__ == "__main__":
    main()