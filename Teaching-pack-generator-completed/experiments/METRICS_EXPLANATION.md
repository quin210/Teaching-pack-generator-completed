# Metrics Explanation

This document summarizes the evaluation metrics used in the experiments.

## Content Accuracy (Acc)

Assesses factual correctness of each slide and quiz question against the ground-truth lesson summary.

Scoring per unit:
- 1.0: fully correct
- 0.5: partially correct or ambiguous
- 0.0: incorrect or contradicts the lesson summary

## Concept Coverage (EM)

Measures semantic coverage of key concepts and skills.

Steps:
1. Extract all concepts from `key_concepts`.
2. Extract all skills from the skill set (if provided).
3. Score coverage in the teaching pack.

Scoring per concept:
- 1.0: clearly taught with correct meaning and context
- 0.5: mentioned but incomplete or unclear
- 0.0: not covered

## Educational Soundness (ES)

Four criteria are scored from 0 to 1:
1. Grade level appropriateness
2. Logical progression
3. Quiz alignment with taught content
4. Cognitive load management

## Overall Score

Overall score is the weighted sum used in the scripts:

```
overall = 0.4 * accuracy + 0.3 * coverage + 0.3 * educational_soundness
```
