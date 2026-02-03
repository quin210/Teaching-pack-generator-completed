"""
Extract Lesson Summary from Teaching Pack
==========================================

This helper script extracts the lesson summary from an existing teaching pack JSON file.
Useful for testing the evaluation pipeline with existing teaching packs.

Usage:
    python experiments/extract_lesson_summary.py --input <teaching_pack.json> --output <lesson_summary.json>
"""

import json
import argparse
from pathlib import Path


def extract_lesson_summary(input_path: str, output_path: str):
    """
    Extract lesson summary from a teaching pack JSON file

    Args:
        input_path: Path to teaching pack JSON file
        output_path: Path to save extracted lesson summary
    """
    print(f" Reading teaching pack from: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        teaching_pack = json.load(f)

    # Check if lesson_summary exists
    if "lesson_summary" not in teaching_pack:
        raise ValueError("No 'lesson_summary' field found in teaching pack JSON")

    lesson_summary = teaching_pack["lesson_summary"]

    print(f"\n Extracted lesson summary:")
    print(f"  Title: {lesson_summary.get('title', 'N/A')}")
    print(f"  Subject: {lesson_summary.get('subject', 'N/A')}")
    print(f"  Grade: {lesson_summary.get('grade', 'N/A')}")
    print(f"  Key Concepts: {len(lesson_summary.get('key_concepts', []))}")

    # Save lesson summary
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(lesson_summary, f, indent=2, ensure_ascii=False)

    print(f"\n Lesson summary saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract lesson summary from teaching pack JSON"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to teaching pack JSON file"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to save extracted lesson summary"
    )

    args = parser.parse_args()

    extract_lesson_summary(args.input, args.output)


if __name__ == "__main__":
    main()
