"""
General Knowledge Evaluation Script

This script evaluates a language model on general knowledge questions using Gemini as a judge.

Usage:
    python GeneralKnowledge_eval.py

Environment Variables:
    - GOOGLE_API_KEY: Gemini API key
    - HF_TOKEN: HuggingFace token (optional)
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional, Tuple, Union

import torch
from datasets import load_dataset
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

import google.generativeai as genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration for the evaluation script."""
    MODEL_PATH = "example-model"
    DATASET_NAME = "MuskumPillerum/General-Knowledge"
    NUM_QUESTIONS = 3000
    OUTPUT_FILE = "./evaluation_results.json"
    MAX_LENGTH = 512
    MAX_RETRIES = 3
    SLEEP_TIME = 2
    TEMPERATURE = 0.7


class ModelManager:
    """Handles model loading and inference."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model: Optional[Any] = None  # AutoModelForCausalLM
        self.tokenizer: Optional[Any] = None  # AutoTokenizer

    def load_model(self) -> Tuple[Any, Any]:
        """Load model and tokenizer from HuggingFace."""
        try:
            logger.info(f"Loading model: {self.model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )

            if self.tokenizer.pad_token is None:  # type: ignore
                self.tokenizer.pad_token = self.tokenizer.eos_token  # type: ignore

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.bfloat16,
                trust_remote_code=True,
            )
            self.model.to('cuda')  # type: ignore
            self.model.eval()  # type: ignore

            logger.info("Model loaded successfully")
            return self.model, self.tokenizer

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def generate_response(
        self,
        question: str,
        max_length: int = Config.MAX_LENGTH,
        max_retries: int = Config.MAX_RETRIES
    ) -> str:
        """Generate response for a question with retry logic."""
        if not self.model or not self.tokenizer:
            raise ValueError("Model not loaded. Call load_model() first.")

        for attempt in range(max_retries):
            try:
                inputs = self.tokenizer(  # type: ignore
                    question,
                    return_tensors="pt"
                ).to(self.model.device)  # type: ignore

                with torch.no_grad():
                    outputs = self.model.generate(  # type: ignore
                        **inputs,
                        max_length=max_length,
                        num_return_sequences=1,
                        do_sample=True,
                        temperature=Config.TEMPERATURE,
                        pad_token_id=self.tokenizer.pad_token_id,  # type: ignore
                    )

                response = self.tokenizer.decode(  # type: ignore
                    outputs[0],
                    skip_special_tokens=True
                )

                # Remove question prefix if present
                if response.startswith(question):
                    response = response[len(question):].strip()

                return response

            except Exception as e:
                logger.warning(
                    f"Generation attempt {attempt + 1} failed: {e}"
                )
                if attempt == max_retries - 1:
                    return "Error: Failed to generate response"

        return "Error: Failed to generate response"


class JudgeManager:
    """Handles judgment using Gemini API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)  # type: ignore
        self.client = genai.GenerativeModel('gemini-2.0-flash')  # type: ignore

    def judge_answer(
        self,
        question: str,
        model_answer: str,
        ground_truth: str,
        max_retries: int = Config.MAX_RETRIES
    ) -> Dict[str, Any]:
        """Judge the model's answer using Gemini."""
        prompt = f"""
        Question: {question}
        Ground Truth Answer: {ground_truth}
        Model's Answer: {model_answer}

        Rate the accuracy and quality of the model's answer compared to the ground truth on a scale of 1-10, where 1 is completely wrong and 10 is perfect match.
        Provide a brief explanation.

        Score: [number between 1-10]
        Explanation: [brief text]
        """

        for attempt in range(max_retries):
            try:
                response = self.client.generate_content(prompt)

                if response.text:
                    text = response.text.strip()
                    lines = text.split('\n')

                    score = 0
                    explanation = "Failed to parse"

                    for line in lines:
                        if line.startswith('Score:'):
                            try:
                                score = int(line.split('Score:')[1].strip())
                            except ValueError:
                                pass
                        elif line.startswith('Explanation:'):
                            explanation = line.split('Explanation:')[1].strip()

                    return {"score": score, "explanation": explanation}
                else:
                    logger.warning("Empty response from Gemini")
                    continue

            except Exception as e:
                logger.warning(
                    f"Judgment attempt {attempt + 1} failed: {e}"
                )
                if attempt == max_retries - 1:
                    return {
                        "score": 0,
                        "explanation": "Failed after retries"
                    }

        return {"score": 0, "explanation": "Failed after retries"}


def load_existing_results(output_file: str) -> Tuple[list, set]:
    """Load existing results if file exists."""
    if not os.path.exists(output_file):
        return [], set()

    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        processed_indices = set(r['index'] for r in results)
        logger.info(f"Loaded {len(results)} existing results")
        return results, processed_indices
    except Exception as e:
        logger.warning(f"Failed to load existing results: {e}")
        return [], set()


def save_results(results: list, output_file: str) -> None:
    """Save results to JSON file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")


def main() -> None:
    """Main evaluation function."""
    # Validate environment
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable required")

    # Initialize components
    model_manager = ModelManager(Config.MODEL_PATH)
    judge_manager = JudgeManager(api_key)

    # Load model
    model, tokenizer = model_manager.load_model()

    # Load dataset
    logger.info(f"Loading dataset: {Config.DATASET_NAME}")
    dataset = load_dataset(Config.DATASET_NAME, split='train')
    dataset = dataset.select(range(min(Config.NUM_QUESTIONS, len(dataset))))
    logger.info(f"Dataset loaded: {len(dataset)} questions")

    # Load existing results
    results, processed_indices = load_existing_results(Config.OUTPUT_FILE)
    total_score = sum(r.get('score', 0) for r in results)

    # Evaluation loop
    logger.info("Starting evaluation...")
    for i, example in tqdm(enumerate(dataset), total=len(dataset)):
        if i in processed_indices:
            continue

        question = example.get('Question', '')  # type: ignore
        ground_truth = example.get('Answer', '')  # type: ignore

        # Generate response
        response = model_manager.generate_response(question)

        # Judge response
        judgment = judge_manager.judge_answer(
            question, response, ground_truth
        )

        # Record result
        result = {
            "index": i,
            "question": question,
            "ground_truth": ground_truth,
            "model_answer": response,
            "score": judgment.get("score", 0),
            "explanation": judgment.get("explanation", "")
        }

        results.append(result)
        total_score += result["score"]

        # Save after each question
        save_results(results, Config.OUTPUT_FILE)

        # Rate limiting
        time.sleep(Config.SLEEP_TIME)

    # Final statistics
    avg_score = total_score / len(results) if results else 0
    logger.info("Evaluation complete")
    logger.info(f"Average score: {avg_score:.2f}")
    logger.info(f"Total questions evaluated: {len(results)}")


if __name__ == "__main__":
    main()