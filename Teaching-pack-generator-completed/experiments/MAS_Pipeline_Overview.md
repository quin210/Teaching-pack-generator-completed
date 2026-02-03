# MAS Pipeline Overview

This document provides a compact overview of the multi-agent teaching pack pipeline.

## Goal

Automatically generate differentiated teaching packs for student groups with different mastery levels.

## High-Level Stages

1. Lesson parsing
2. Skill mapping
3. Diagnostic building
4. Group profiling
5. Group labeling
6. Pack planning
7. Slide drafting
8. Quiz generation
9. Video drafting

## Inputs

- Lesson summary JSON or PDF lesson file
- Optional ground-truth JSON for evaluation
- Number of groups and number of students

## Outputs

- Teaching packs per group (slides, quiz, video script)
- Evaluation results per group

## Key Scripts

- `experiments/mas_evaluation_experiment.py`
- `experiments/mas_evaluation_experiment_vllm.py`
- `experiments/mas_evaluation_experiment_vllm_qwen3_grpo_dpo.py`
