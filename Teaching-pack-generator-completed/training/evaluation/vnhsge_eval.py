"""
VNHSGE Evaluation Script

This script evaluates a language model on VNHSGE benchmark using Gemini as a judge.

Usage:
    python vnhsge_eval.py

Environment Variables:
    - GEMINI_API_KEY: Gemini API key
    - HF_TOKEN: HuggingFace token (optional)

Dataset Setup:
    1. Clone the repository: git clone https://github.com/Xdao85/VNHSGE.git
    2. Navigate to the evaluation directory: cd evaluation
    3. Prepare your dataset in ./dataset/eval/ with subject folders
"""

import json
import logging
import os
import re
import time
from typing import Dict, Any, Optional, Tuple, List

import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

import google.generativeai as genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration for the evaluation script."""
    BASE_MODEL_NAME = "Qwen/Qwen2.5-3B"
    MODEL_NAME = "example-model"
    SAVE_DIR = "./evaluation_results"
    DATASET_PATH = "./dataset/eval"
    MAX_NEW_TOKENS = 128
    MAX_RETRIES = 3
    SLEEP_TIME = 2


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

    def generate_answer(self, prompt: str) -> str:
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
                    do_sample=False,
                )

            text = self.tokenizer.decode(  # type: ignore
                outputs[0],
                skip_special_tokens=True
            )

            return text

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"Error: {e}"


class JudgeManager:
    """Handles judgment using Gemini API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)  # type: ignore
        self.judge_model = genai.GenerativeModel("gemini-2.0-flash")  # type: ignore

    def judge_answer(
        self,
        question: str,
        gold: str,
        pred: str,
        max_retries: int = Config.MAX_RETRIES
    ) -> Dict[str, Any]:
        """Judge the model's answer using Gemini."""
        prompt = self.build_judge_prompt(question, gold, pred)

        for attempt in range(max_retries):
            try:
                response = self.judge_model.generate_content(prompt)
                result = self.extract_json(response.text)

                if result:
                    return result
                else:
                    logger.warning(f"Failed to parse JSON on attempt {attempt + 1}")

            except Exception as e:
                logger.warning(
                    f"Judgment attempt {attempt + 1} failed: {e}"
                )
                time.sleep(Config.SLEEP_TIME)

        return {
            "correct": None,
            "reason": "Failed after retries"
        }

    def build_judge_prompt(self, q: str, gold: str, pred: str) -> str:
        """Build judge prompt."""
        return f"""
You are an independent judge.

Question:
{q}

Correct answer:
{gold}

Model's answer:
{pred}

Evaluate if the model's answer is correct.

Return only JSON:
{{"correct": true or false, "reason": "brief explanation"}}
"""

    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text."""
        try:
            # Find JSON in text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
        except json.JSONDecodeError:
            return None


class EvaluationManager:
    """Manages the evaluation process."""

    def __init__(self):
        self.model_manager = ModelManager(Config.BASE_MODEL_NAME, Config.MODEL_NAME)
        self.judge_manager = None

    def setup(self) -> None:
        """Setup evaluation environment."""
        # Create results directory
        os.makedirs(Config.SAVE_DIR, exist_ok=True)

        # Validate API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable required")

        self.judge_manager = JudgeManager(api_key)

        # Load model
        self.model_manager.load_model()

    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load evaluation dataset."""
        logger.info(f"Loading dataset from: {Config.DATASET_PATH}")

        if not os.path.exists(Config.DATASET_PATH):
            raise FileNotFoundError(f"Dataset path not found: {Config.DATASET_PATH}")

        dataset = []
        subject_dirs = [d for d in os.listdir(Config.DATASET_PATH)
                       if os.path.isdir(os.path.join(Config.DATASET_PATH, d))]

        for subject in subject_dirs:
            subject_path = os.path.join(Config.DATASET_PATH, subject)
            json_files = [f for f in os.listdir(subject_path)
                         if f.endswith('.json')]

            for json_file in json_files:
                file_path = os.path.join(subject_path, json_file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for item in data:
                            item['subject'] = subject
                            item['file'] = json_file
                        dataset.extend(data)
                except Exception as e:
                    logger.warning(f"Failed to load {file_path}: {e}")

        logger.info(f"Dataset loaded: {len(dataset)} samples")
        return dataset

    def build_prompt(self, question: str, options: List[str]) -> str:
        """Build evaluation prompt."""
        opts = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])

        return f"""You are taking a multiple choice test.
Choose the correct answer (A, B, C, or D) and provide a brief explanation.

Question: {question}

Options:
{opts}

Answer in the format:
Final Answer: [A/B/C/D]
Explanation: [brief explanation]
"""

    def extract_answer(self, text: str) -> str:
        """Extract answer from model output."""
        # Look for "Final Answer:" pattern
        match = re.search(r'Final Answer:\s*([A-D])', text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        # Fallback: look for single letter answers
        for char in ['A', 'B', 'C', 'D']:
            if f" {char}" in text or f"{char}." in text:
                return char

        return "N/A"

    def evaluate_sample(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single sample."""
        question = sample["question"]
        options = sample["choices"]
        gold = sample["answer"]

        # Build prompt
        prompt = self.build_prompt(question, options)

        # Generate answer
        model_output = self.model_manager.generate_answer(prompt)

        # Extract prediction
        pred = self.extract_answer(model_output)

        # Judge answer
        judge_result = self.judge_manager.judge_answer(question, gold, pred)

        return {
            "subject": sample.get("subject", ""),
            "question": question,
            "gold": gold,
            "model_output": model_output,
            "prediction": pred,
            "judge_correct": judge_result.get("correct"),
            "judge_reason": judge_result.get("reason", "")
        }

    def save_results(self, results: List[Dict], filename: str) -> None:
        """Save results to JSON."""
        try:
            filepath = os.path.join(Config.SAVE_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"Results saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    def run_evaluation(self) -> None:
        """Run the complete evaluation."""
        # Setup
        self.setup()

        # Load data
        dataset = self.load_dataset()

        # Evaluation loop
        logger.info("Starting evaluation...")
        results = []

        for sample in tqdm(dataset, desc="Evaluating"):
            result = self.evaluate_sample(sample)
            results.append(result)

            # Rate limiting
            time.sleep(Config.SLEEP_TIME)

        # Save results
        self.save_results(results, "evaluation_results.json")

        # Statistics
        total_questions = len(results)
        num_correct = sum(1 for r in results if r["judge_correct"] is True)

        accuracy = num_correct / total_questions if total_questions > 0 else 0

        logger.info("Evaluation complete")
        logger.info(f"Accuracy: {accuracy:.4f}")
        logger.info(f"Correct / Total: {num_correct} / {total_questions}")


def main() -> None:
    """Main function."""
    evaluator = EvaluationManager()
    evaluator.run_evaluation()


if __name__ == "__main__":
    main()