"""
Batch Evaluation Script
=======================

Evaluates multiple lesson summaries in batch mode and generates aggregate statistics.

Usage:
    python experiments/batch_evaluation.py --input_dir experiments/lessons --output_dir results/batch
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from experiments.mas_evaluation_experiment import run_experiment


async def evaluate_batch(
    input_dir: str,
    output_dir: str,
    num_groups: int = 3,
    num_students: int = 30,
    file_pattern: str = "*.json"
):
    """
    Evaluate multiple lesson summaries in batch

    Args:
        input_dir: Directory containing lesson summary JSON files
        output_dir: Directory to save results
        num_groups: Number of student groups
        num_students: Total number of students
        file_pattern: Glob pattern for lesson files (default: *.json)
    """
    print("=" * 80)
    print("BATCH EVALUATION - MAS EVALUATION EXPERIMENT")
    print("=" * 80)

    # Find all lesson files
    input_path = Path(input_dir)
    lesson_files = list(input_path.glob(file_pattern))

    if not lesson_files:
        print(f"\n ERROR: No files matching '{file_pattern}' found in {input_dir}")
        return

    print(f"\n Found {len(lesson_files)} lesson files:")
    for i, file in enumerate(lesson_files, 1):
        print(f"   {i}. {file.name}")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Track results
    batch_results = {
        "timestamp": datetime.now().isoformat(),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "num_groups": num_groups,
        "num_students": num_students,
        "total_lessons": len(lesson_files),
        "lessons": []
    }

    # Evaluate each lesson
    for i, lesson_file in enumerate(lesson_files, 1):
        print("\n" + "=" * 80)
        print(f"EVALUATING LESSON {i}/{len(lesson_files)}: {lesson_file.name}")
        print("=" * 80)

        try:
            # Load lesson to get metadata
            with open(lesson_file, 'r', encoding='utf-8') as f:
                lesson_data = json.load(f)

            lesson_title = lesson_data.get("title", lesson_file.stem)

            # Run evaluation
            await run_experiment(
                lesson_summary_path=str(lesson_file),
                ground_truth_path=None,
                output_dir=str(output_path / lesson_file.stem),
                num_groups=num_groups,
                num_students=num_students
            )

            # Find the most recent result file
            result_files = list((output_path / lesson_file.stem).glob("experiment_results_*.json"))
            if result_files:
                latest_result = max(result_files, key=lambda p: p.stat().st_mtime)

                # Load result
                with open(latest_result, 'r', encoding='utf-8') as f:
                    result = json.load(f)

                # Calculate aggregate scores
                evaluations = result.get("evaluations", [])
                if evaluations:
                    avg_accuracy = sum(e["evaluation"]["accuracy_total"] for e in evaluations) / len(evaluations)
                    avg_coverage = sum(e["evaluation"]["coverage_total"] for e in evaluations) / len(evaluations)
                    avg_soundness = sum(e["evaluation"]["educational_soundness_total"] for e in evaluations) / len(evaluations)
                    avg_overall = sum(e["evaluation"]["overall_score"] for e in evaluations) / len(evaluations)

                    batch_results["lessons"].append({
                        "lesson_file": lesson_file.name,
                        "lesson_title": lesson_title,
                        "status": "success",
                        "result_file": str(latest_result),
                        "num_groups_evaluated": len(evaluations),
                        "avg_accuracy": avg_accuracy,
                        "avg_coverage": avg_coverage,
                        "avg_soundness": avg_soundness,
                        "avg_overall": avg_overall
                    })

                    print(f"\n {lesson_file.name} - COMPLETED")
                    print(f"   Overall Score: {avg_overall:.2%}")

        except Exception as e:
            print(f"\n ERROR evaluating {lesson_file.name}: {str(e)}")
            batch_results["lessons"].append({
                "lesson_file": lesson_file.name,
                "lesson_title": lesson_data.get("title", "Unknown") if 'lesson_data' in locals() else "Unknown",
                "status": "failed",
                "error": str(e)
            })

    # Save batch results
    batch_file = output_path / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(batch_file, 'w', encoding='utf-8') as f:
        json.dump(batch_results, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 80)
    print("BATCH EVALUATION SUMMARY")
    print("=" * 80)

    successful = [l for l in batch_results["lessons"] if l["status"] == "success"]
    failed = [l for l in batch_results["lessons"] if l["status"] == "failed"]

    print(f"\n Total Lessons: {len(lesson_files)}")
    print(f" Successful: {len(successful)}")
    print(f" Failed: {len(failed)}")

    if successful:
        print("\n" + "=" * 80)
        print("INDIVIDUAL LESSON SCORES")
        print("=" * 80)

        for lesson in successful:
            print(f"\n {lesson['lesson_title']}")
            print(f"   File: {lesson['lesson_file']}")
            print(f"   Accuracy:  {lesson['avg_accuracy']:.2%}")
            print(f"   Coverage:  {lesson['avg_coverage']:.2%}")
            print(f"   Soundness: {lesson['avg_soundness']:.2%}")
            print(f"   Overall:   {lesson['avg_overall']:.2%}")

        # Calculate overall statistics
        overall_accuracy = sum(l["avg_accuracy"] for l in successful) / len(successful)
        overall_coverage = sum(l["avg_coverage"] for l in successful) / len(successful)
        overall_soundness = sum(l["avg_soundness"] for l in successful) / len(successful)
        overall_score = sum(l["avg_overall"] for l in successful) / len(successful)

        print("\n" + "=" * 80)
        print("AGGREGATE STATISTICS (ALL LESSONS)")
        print("=" * 80)
        print(f"\n Mean Accuracy:        {overall_accuracy:.2%}")
        print(f" Mean Coverage:        {overall_coverage:.2%}")
        print(f" Mean Soundness:       {overall_soundness:.2%}")
        print(f"\n MEAN OVERALL SCORE:   {overall_score:.2%}")

        # Calculate standard deviations
        import statistics
        if len(successful) > 1:
            std_accuracy = statistics.stdev([l["avg_accuracy"] for l in successful])
            std_coverage = statistics.stdev([l["avg_coverage"] for l in successful])
            std_soundness = statistics.stdev([l["avg_soundness"] for l in successful])
            std_overall = statistics.stdev([l["avg_overall"] for l in successful])

            print(f"\n Std Dev Accuracy:     {std_accuracy:.2%}")
            print(f" Std Dev Coverage:     {std_coverage:.2%}")
            print(f" Std Dev Soundness:    {std_soundness:.2%}")
            print(f" Std Dev Overall:      {std_overall:.2%}")

    if failed:
        print("\n" + "=" * 80)
        print("FAILED EVALUATIONS")
        print("=" * 80)
        for lesson in failed:
            print(f"\n {lesson['lesson_file']}")
            print(f"   Error: {lesson['error']}")

    print("\n" + "=" * 80)
    print(f" Batch results saved to: {batch_file}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Run batch evaluation on multiple lesson summaries"
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        required=True,
        help="Directory containing lesson summary JSON files"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="results/batch_evaluation",
        help="Directory to save results (default: results/batch_evaluation)"
    )
    parser.add_argument(
        "--num_groups",
        type=int,
        default=3,
        help="Number of student groups (default: 3)"
    )
    parser.add_argument(
        "--num_students",
        type=int,
        default=30,
        help="Total number of students (default: 30)"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.json",
        help="File pattern to match (default: *.json)"
    )

    args = parser.parse_args()

    # Check if GEMINI_API_KEY is set
    if not os.getenv("GEMINI_API_KEY"):
        print("\n ERROR: GEMINI_API_KEY environment variable not set!")
        print("\nPlease set it:")
        print("  Linux/Mac:  export GEMINI_API_KEY='your-key-here'")
        print("  Windows:    set GEMINI_API_KEY=your-key-here")
        return

    asyncio.run(evaluate_batch(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        num_groups=args.num_groups,
        num_students=args.num_students,
        file_pattern=args.pattern
    ))


if __name__ == "__main__":
    main()
