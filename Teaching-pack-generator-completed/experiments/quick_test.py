"""
Quick Test Script
=================

This script provides a fast way to test the evaluation pipeline with an existing teaching pack.

Usage:
    python experiments/quick_test.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from experiments.mas_evaluation_experiment import run_experiment


async def main():
    """Run a quick test with an existing teaching pack"""

    print("=" * 80)
    print("QUICK TEST - MAS EVALUATION EXPERIMENT")
    print("=" * 80)

    # Check if GEMINI_API_KEY is set
    if not os.getenv("GEMINI_API_KEY"):
        print("\n❌ ERROR: GEMINI_API_KEY environment variable not set!")
        print("\nPlease set it:")
        print("  Linux/Mac:  export GEMINI_API_KEY='your-key-here'")
        print("  Windows:    set GEMINI_API_KEY=your-key-here")
        return

    # Find an existing teaching pack
    outputs_dir = project_root / "outputs"
    teaching_packs = list(outputs_dir.glob("teaching_packs_*.json"))

    if not teaching_packs:
        print("\n❌ ERROR: No teaching pack files found in outputs/")
        print("\nPlease generate a teaching pack first using the main API.")
        return

    # Use the most recent teaching pack
    latest_pack = max(teaching_packs, key=lambda p: p.stat().st_mtime)

    print(f"\n✅ Found teaching pack: {latest_pack.name}")
    print(f"   Using this for quick test...\n")

    # Extract lesson summary first
    print("Step 1: Extracting lesson summary...")
    import json
    with open(latest_pack, 'r', encoding='utf-8') as f:
        teaching_pack = json.load(f)

    if "lesson_summary" not in teaching_pack:
        print("❌ ERROR: No lesson_summary found in teaching pack")
        return

    # Save temporary lesson summary
    temp_lesson = project_root / "experiments" / "temp_lesson_summary.json"
    with open(temp_lesson, 'w', encoding='utf-8') as f:
        json.dump(teaching_pack["lesson_summary"], f, indent=2, ensure_ascii=False)

    print(f"   ✓ Lesson summary extracted")
    print(f"   ✓ Title: {teaching_pack['lesson_summary']['title']}")

    # Run experiment with reduced parameters for speed
    print("\nStep 2: Running evaluation experiment...")
    print("   (Using 2 groups and 20 students for faster testing)")

    await run_experiment(
        lesson_summary_path=str(temp_lesson),
        ground_truth_path=None,
        output_dir=str(project_root / "outputs" / "experiments"),
        num_groups=2,  # Reduced for quick test
        num_students=20  # Reduced for quick test
    )

    # Clean up temp file
    temp_lesson.unlink()

    print("\n" + "=" * 80)
    print("✅ QUICK TEST COMPLETED!")
    print("=" * 80)
    print("\nCheck results in: outputs/experiments/")
    print("\nTo run a full experiment with custom parameters:")
    print("  python experiments/mas_evaluation_experiment.py --lesson_summary <path>")
    print("\nFor more info, see: experiments/README.md")


if __name__ == "__main__":
    asyncio.run(main())
