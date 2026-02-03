"""
MAS Evaluation Experiment
=========================

This script evaluates the Multi-Agent System (MAS) for teaching pack generation using three metrics:
1. Content Accuracy (Acc) - Factual correctness of slides and quiz
2. Exact Match / Semantic Coverage (EM) - Coverage of key concepts from lesson summary
3. Educational Soundness (ES) - Pedagogical appropriateness

Usage:
    python experiments/mas_evaluation_experiment.py --lesson_summary <path> --ground_truth <path>
"""

import os
import sys
import json
import asyncio
import argparse
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import MAS components
from src.llm.base import AgentClient
from src.utils.config_loader import load_config, resolve_value
from src.utils.reproducibility import set_seed
from src.data.prompts.teaching_pack_prompts import (
    LESSON_PARSER_PROMPT,
    SKILL_MAPPER_PROMPT,
    DIAGNOSTIC_BUILDER_PROMPT,
    GROUP_LABELER_PROMPT,
    PACK_PLANNER_PROMPT,
    SLIDE_DRAFTER_PROMPT,
    VIDEO_DRAFTER_PROMPT,
    QUIZ_PRACTICE_PROMPT,
)
from src.models.teaching_pack_models import (
    LessonSummary,
    SkillSet,
    Diagnostic,
    GroupProfile,
    PackPlan,
    Slides,
    Video,
    Quiz,
)
from src.utils.basetools.grouping_utils import profile_groups_by_quartile
from src.utils.workflow_helpers import generate_mock_diagnostic_results, export_final_results
from src.utils.basetools.pdf_parser import extract_text_from_pdf

# Import Google Gemini for evaluation
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.exceptions import ModelHTTPError
from pydantic import BaseModel


# =====================================================
# EVALUATION RESULT SCHEMAS
# =====================================================

class UnitScore(BaseModel):
    """Score for a single unit (slide or quiz question)"""
    unit_id: str
    unit_type: str  # "slide" or "quiz"
    accuracy: float  # 0, 0.5, or 1
    explanation: str


class ConceptCoverage(BaseModel):
    """Coverage score for a single concept"""
    concept: str
    coverage: float  # 0, 0.5, or 1
    explanation: str


class EducationalSoundnessScore(BaseModel):
    """Educational soundness evaluation"""
    criterion: str
    score: float  # 0 to 1
    explanation: str


class EvaluationResult(BaseModel):
    """Complete evaluation result with all metrics"""
    # Content Accuracy
    accuracy_scores: List[UnitScore]
    accuracy_total: float

    # Exact Match / Semantic Coverage
    concept_coverage: List[ConceptCoverage]
    coverage_total: float

    # Educational Soundness
    educational_soundness: List[EducationalSoundnessScore]
    educational_soundness_total: float

    # Overall Score
    overall_score: float

    # Metadata
    num_slides: int
    num_quiz_questions: int
    num_concepts: int
    evaluation_timestamp: str


# =====================================================
# MAS PIPELINE RUNNER
# =====================================================

def _normalize_lesson_summary(raw: Dict[str, Any]) -> LessonSummary:
    """Coerce ground-truth lesson summary into the expected schema."""
    data = dict(raw)
    data["grade"] = str(data.get("grade", ""))
    if "key_concepts" in data:
        data["key_concepts"] = [str(x) for x in (data.get("key_concepts") or [])]
    if "examples" in data:
        data["examples"] = [str(x) for x in (data.get("examples") or [])]
    if "definitions" in data and isinstance(data["definitions"], list):
        defs: Dict[str, str] = {}
        for item in data["definitions"]:
            if isinstance(item, dict):
                term = item.get("term") or item.get("key") or item.get("name")
                definition = item.get("definition") or item.get("value") or item.get("desc")
                if term is not None and definition is not None:
                    defs[str(term)] = str(definition)
        data["definitions"] = defs
    data.setdefault("lesson_content", "")
    return LessonSummary(**data)


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _trim_lesson_content(lesson_summary: LessonSummary, max_chars: int = 1200) -> None:
    """Trim lesson_content to avoid exceeding small context windows."""
    content = lesson_summary.lesson_content or ""
    if len(content) <= max_chars:
        return
    trimmed = content[:max_chars]
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    lesson_summary.lesson_content = trimmed + "..."


def _compact_lesson_summary(lesson_summary: LessonSummary) -> LessonSummary:
    """Create a compact lesson summary for prompt usage."""
    compact = lesson_summary.model_copy(deep=True)
    compact.lesson_content = ""
    compact.examples = (compact.examples or [])[:3]
    if compact.definitions:
        items = list(compact.definitions.items())[:6]
        compact.definitions = {k: v for k, v in items}
    return compact


def _extract_json_block(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model output.")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("Unclosed JSON object in model output.")


def _extract_max_tokens_limit(err: Exception) -> int | None:
    message = ""
    if isinstance(err, ModelHTTPError):
        body = getattr(err, "body", None)
        if isinstance(body, dict):
            message = body.get("message") or body.get("error", {}).get("message") or ""
    if not message:
        message = str(err)

    match = re.search(r"maximum context length is (\d+)", message)
    match_input = re.search(r"request has (\d+) input tokens", message)
    if match and match_input:
        max_len = int(match.group(1))
        input_tokens = int(match_input.group(1))
        return max(16, max_len - input_tokens)

    match_alt = re.search(r"\((\d+) > (\d+) - (\d+)\)", message)
    if match_alt:
        max_len = int(match_alt.group(2))
        input_tokens = int(match_alt.group(3))
        return max(16, max_len - input_tokens)

    return None


def _parse_model_from_text(text: str, model_cls: Any) -> Any:
    cleaned = _strip_code_fence(text)
    json_text = _extract_json_block(cleaned) if "{" in cleaned else cleaned
    try:
        return model_cls.model_validate_json(json_text)
    except Exception:
        data = json.loads(json_text)
        if isinstance(data, dict):
            if model_cls is LessonSummary:
                data.setdefault("grade", "")
                data.setdefault("lesson_content", "")
            elif model_cls is SkillSet:
                skills = data.get("skills")
                if isinstance(skills, list):
                    normalized = []
                    for skill in skills:
                        if not isinstance(skill, dict):
                            continue
                        fixed = dict(skill)
                        if "skill_id" not in fixed:
                            fixed["skill_id"] = fixed.get("id") or fixed.get("skillId")
                        if "name" not in fixed:
                            fixed["name"] = fixed.get("title") or fixed.get("label")
                        if fixed.get("name") is None:
                            fixed["name"] = "Unnamed skill"
                        if "description" not in fixed:
                            fixed["description"] = fixed.get("desc") or fixed.get("detail")
                        if fixed.get("description") is None:
                            fixed["description"] = ""
                        if "is_prerequisite" not in fixed:
                            fixed["is_prerequisite"] = bool(fixed.get("prerequisite", False))
                        if "weight" not in fixed:
                            fixed["weight"] = 0.7
                        normalized.append(fixed)
                    data["skills"] = normalized
                data.setdefault("skill_dependencies", {})
            elif model_cls is Diagnostic:
                if "diagnostic" in data and isinstance(data["diagnostic"], dict):
                    inner = data.pop("diagnostic")
                    if "questions" not in data and "questions" in inner:
                        data["questions"] = inner["questions"]
                    if "total_questions" not in data and "total_questions" in inner:
                        data["total_questions"] = inner["total_questions"]
                    if "skills_covered" not in data and "skills_covered" in inner:
                        data["skills_covered"] = inner["skills_covered"]
                questions = data.get("questions")
                if isinstance(questions, list):
                    normalized_qs = []
                    for idx, q in enumerate(questions, start=1):
                        if not isinstance(q, dict):
                            continue
                        fixed_q = dict(q)
                        if "question_id" not in fixed_q:
                            fixed_q["question_id"] = fixed_q.get("id") or f"q{idx}"
                        if "question_text" not in fixed_q:
                            fixed_q["question_text"] = fixed_q.get("question") or fixed_q.get("prompt")
                        if "correct_answer" not in fixed_q:
                            fixed_q["correct_answer"] = fixed_q.get("answer") or fixed_q.get("correct")
                        if fixed_q.get("question_text") is None:
                            fixed_q["question_text"] = ""
                        if fixed_q.get("correct_answer") is None:
                            fixed_q["correct_answer"] = ""
                        else:
                            fixed_q["correct_answer"] = str(fixed_q["correct_answer"])
                        if "skill_id" not in fixed_q:
                            fixed_q["skill_id"] = ""
                        if "rationale" not in fixed_q:
                            fixed_q["rationale"] = ""
                        normalized_qs.append(fixed_q)
                    data["questions"] = normalized_qs
                data.setdefault("questions", [])
                data.setdefault("skills_covered", [])
                data.setdefault("total_questions", len(data.get("questions", [])))
            elif model_cls is GroupProfile:
                data.setdefault("group_id", "")
                data.setdefault("mastery_level", "medium")
                if data.get("mastery_level") not in {"low", "medium", "high", "advanced"}:
                    data["mastery_level"] = "medium"
                data.setdefault("skill_mastery", {})
                data.setdefault("learning_pace", "moderate")
                if data.get("learning_pace") not in {"slow", "moderate", "fast"}:
                    data["learning_pace"] = "moderate"
                data.setdefault("students", [])
            elif model_cls is PackPlan:
                if "teaching_pack" in data and isinstance(data["teaching_pack"], dict):
                    inner = data.pop("teaching_pack")
                    for key in ("learning_objectives", "slide_outline", "quiz_blueprint", "estimated_time", "differentiation_strategy", "group_id"):
                        if key not in data and key in inner:
                            data[key] = inner[key]
                data.setdefault("group_id", "")
                data.setdefault("learning_objectives", [])
                estimated_time = data.get("estimated_time")
                if isinstance(estimated_time, dict):
                    data["estimated_time"] = sum(
                        int(v) for v in estimated_time.values() if isinstance(v, (int, float, str)) and str(v).isdigit()
                    )
                elif not isinstance(estimated_time, int):
                    estimated_str = str(estimated_time)
                    digits = "".join(ch for ch in estimated_str if ch.isdigit())
                    data["estimated_time"] = int(digits) if digits else 0
                data.setdefault("differentiation_strategy", "")
                diff_strategy = data.get("differentiation_strategy")
                if not isinstance(diff_strategy, str):
                    data["differentiation_strategy"] = json.dumps(
                        diff_strategy, ensure_ascii=False
                    )
                slide_outline = data.get("slide_outline")
                if isinstance(slide_outline, list):
                    normalized_outline = []
                    for idx, item in enumerate(slide_outline, start=1):
                        if not isinstance(item, dict):
                            continue
                        fixed_item = dict(item)
                        if "slide_number" in fixed_item:
                            fixed_item["slide_number"] = str(fixed_item["slide_number"])
                        else:
                            fixed_item["slide_number"] = str(idx)
                        key_points = fixed_item.get("key_points")
                        if isinstance(key_points, list):
                            fixed_item["key_points"] = "\n".join(str(x) for x in key_points)
                        elif key_points is None:
                            fixed_item["key_points"] = ""
                        normalized_outline.append(fixed_item)
                    data["slide_outline"] = normalized_outline
                data.setdefault("slide_outline", [])
                quiz_blueprint = data.get("quiz_blueprint")
                if isinstance(quiz_blueprint, dict):
                    data["quiz_blueprint"] = [quiz_blueprint]
                elif quiz_blueprint is None:
                    data["quiz_blueprint"] = []
                if isinstance(data.get("quiz_blueprint"), list):
                    normalized_qb = []
                    for qb in data["quiz_blueprint"]:
                        if not isinstance(qb, dict):
                            continue
                        fixed_qb = dict(qb)
                        for key in (
                            "total_questions",
                            "number_of_questions",
                            "num_questions",
                            "difficulty_levels",
                            "question_types",
                            "topics",
                            "easy",
                            "medium",
                            "hard",
                            "challenge",
                        ):
                            if key in fixed_qb:
                                val = fixed_qb[key]
                                if isinstance(val, list):
                                    fixed_qb[key] = ", ".join(str(x) for x in val)
                                elif isinstance(val, dict):
                                    fixed_qb[key] = json.dumps(val, ensure_ascii=False)
                                else:
                                    fixed_qb[key] = str(val)
                        normalized_qb.append(fixed_qb)
                    data["quiz_blueprint"] = normalized_qb
            elif model_cls is Slides:
                slides = data.get("slides")
                if isinstance(slides, list):
                    normalized_slides = []
                    for idx, slide in enumerate(slides, start=1):
                        if not isinstance(slide, dict):
                            continue
                        fixed_slide = dict(slide)
                        if "slide_id" not in fixed_slide:
                            fixed_slide["slide_id"] = fixed_slide.get("id") or f"slide_{idx}"
                        if "title" not in fixed_slide:
                            fixed_slide["title"] = fixed_slide.get("slide_title") or fixed_slide.get("heading") or ""
                        if "content" not in fixed_slide:
                            fixed_slide["content"] = fixed_slide.get("body") or fixed_slide.get("text") or ""
                        if "visual_notes" not in fixed_slide:
                            fixed_slide["visual_notes"] = fixed_slide.get("visual_aids") or ""
                        if "speaker_notes" not in fixed_slide:
                            fixed_slide["speaker_notes"] = fixed_slide.get("notes") or ""
                        normalized_slides.append(fixed_slide)
                    data["slides"] = normalized_slides
                data.setdefault("slides", [])
            elif model_cls is Quiz:
                questions = data.get("questions")
                if isinstance(questions, list):
                    normalized_qs = []
                    for idx, q in enumerate(questions, start=1):
                        if not isinstance(q, dict):
                            continue
                        fixed_q = dict(q)
                        if "question_id" not in fixed_q:
                            fixed_q["question_id"] = fixed_q.get("id") or f"q{idx}"
                        if "question_text" not in fixed_q:
                            fixed_q["question_text"] = fixed_q.get("question") or fixed_q.get("prompt") or ""
                        if "correct_answer" not in fixed_q:
                            fixed_q["correct_answer"] = fixed_q.get("answer") or fixed_q.get("correct") or ""
                        diff = fixed_q.get("difficulty")
                        diff_norm = str(diff).lower() if diff is not None else "medium"
                        if diff_norm not in ("easy", "medium", "hard"):
                            diff_norm = "medium"
                        fixed_q["difficulty"] = diff_norm
                        if "skill_id" not in fixed_q:
                            fixed_q["skill_id"] = ""
                        if "hint" not in fixed_q:
                            fixed_q["hint"] = ""
                        if "explanation" not in fixed_q:
                            fixed_q["explanation"] = ""
                        normalized_qs.append(fixed_q)
                    data["questions"] = normalized_qs
                data.setdefault("questions", [])
                practice_exercises = data.get("practice_exercises")
                if isinstance(practice_exercises, list):
                    normalized_ex = []
                    for ex in practice_exercises:
                        if not isinstance(ex, dict):
                            continue
                        fixed_ex = dict(ex)
                        diff = fixed_ex.get("difficulty")
                        diff_norm = str(diff).lower() if diff is not None else "medium"
                        if diff_norm not in ("easy", "medium", "hard"):
                            diff_norm = "medium"
                        fixed_ex["difficulty"] = diff_norm
                        normalized_ex.append(fixed_ex)
                    data["practice_exercises"] = normalized_ex
                data.setdefault("practice_exercises", [])
                data.setdefault("answer_key", {})
                data.setdefault("total_questions", len(data.get("questions", [])))
        return model_cls.model_validate(data)


async def _run_agent_json(agent: Any, prompt: str, model_cls: Any, retries: int = 2) -> Any:
    last_err: Exception | None = None
    max_tokens = 512
    parse_attempts = 0
    max_token_adjusts = 0
    max_allowed: int | None = None
    while parse_attempts <= retries:
        try:
            result = await agent.run(prompt, model_settings={"max_tokens": max_tokens})
        except Exception as err:
            allowed = _extract_max_tokens_limit(err)
            if allowed is not None and max_token_adjusts < 10:
                max_allowed = allowed
                max_tokens = max(16, allowed - 64)
                last_err = err
                max_token_adjusts += 1
                continue
            raise
        raw = getattr(result, "data", None)
        if raw is None:
            raw = getattr(result, "output", None)
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            raw = str(raw)
        try:
            return _parse_model_from_text(raw, model_cls)
        except Exception as err:
            last_err = err
            err_text = str(err)
            if "Unclosed JSON object" in err_text and max_token_adjusts < 10:
                if max_allowed is None:
                    max_tokens += 64
                elif max_tokens < max_allowed - 8:
                    max_tokens = min(max_allowed - 8, max_tokens + 64)
                max_token_adjusts += 1
                continue
            parse_attempts += 1
            prompt = (
                prompt
                + "\n\nReturn ONLY a valid JSON object that strictly matches the required schema. "
                + "Do not include any extra text."
            )
    raise ValueError(f"Failed to parse model output as {model_cls.__name__}: {last_err}")

class MASPipeline:
    """Runs the complete MAS pipeline to generate teaching packs"""

    def __init__(
        self,
        vllm_base_url: str,
        vllm_model: str,
        vllm_api_key: str | None = None,
        vllm_lora: str | None = None,
    ):
        """Initialize all agents"""
        provider = OpenAIProvider(base_url=vllm_base_url, api_key=vllm_api_key)
        extra_body = {"response_format": {"type": "json_object"}}
        if vllm_lora:
            extra_body["lora"] = vllm_lora
        self.model = OpenAIChatModel(
            vllm_model,
            provider=provider,
            settings={
                "extra_body": extra_body,
                "temperature": 0.2,
            },
        )

        # Initialize agents
        self.lesson_parser_agent = AgentClient(
            system_prompt=LESSON_PARSER_PROMPT,
            tools=[],
            model=self.model
        ).create_agent()

        self.skill_mapper_agent = AgentClient(
            system_prompt=SKILL_MAPPER_PROMPT,
            tools=[],
            model=self.model
        ).create_agent()

        self.diagnostic_builder_agent = AgentClient(
            system_prompt=DIAGNOSTIC_BUILDER_PROMPT,
            tools=[],
            model=self.model
        ).create_agent()

        self.group_labeler_agent = AgentClient(
            system_prompt=GROUP_LABELER_PROMPT,
            tools=[],
            model=self.model
        ).create_agent()

        self.pack_planner_agent = AgentClient(
            system_prompt=PACK_PLANNER_PROMPT,
            tools=[],
            model=self.model
        ).create_agent()

        self.slide_drafter_agent = AgentClient(
            system_prompt=SLIDE_DRAFTER_PROMPT,
            tools=[],
            model=self.model
        ).create_agent()

        self.video_drafter_agent = AgentClient(
            system_prompt=VIDEO_DRAFTER_PROMPT,
            tools=[],
            model=self.model
        ).create_agent()

        self.quiz_practice_agent = AgentClient(
            system_prompt=QUIZ_PRACTICE_PROMPT,
            tools=[],
            model=self.model
        ).create_agent()

    async def run_pipeline(
        self,
        lesson_summary: LessonSummary,
        num_groups: int = 3,
        num_students: int = 30
    ) -> Dict[str, Any]:
        """
        Run the complete MAS pipeline to generate teaching packs

        Args:
            lesson_summary: The lesson summary to generate teaching packs for
            num_groups: Number of student groups (default: 3)
            num_students: Total number of students (default: 30)

        Returns:
            Dictionary containing teaching packs for all groups
        """
        print("=" * 80)
        print("STARTING MAS PIPELINE")
        print("=" * 80)

        results = {
            "lesson_summary": lesson_summary,
            "skill_set": None,
            "diagnostic": None,
            "groups": [],
            "teaching_packs": []
        }
        prompt_lesson_summary = _compact_lesson_summary(lesson_summary)

        # Stage 1: Skill Mapping
        print("\n[1/7] Mapping skills from lesson summary...")
        skill_set: SkillSet = await _run_agent_json(
            self.skill_mapper_agent,
            prompt_lesson_summary.model_dump_json(indent=2)
            + "\n\nReturn ONLY JSON matching the SkillSet schema.",
            SkillSet,
        )
        results["skill_set"] = skill_set
        print(f"    Identified {len(skill_set.skills)} skills")

        # Stage 2: Diagnostic Building
        print("\n[2/7] Building diagnostic assessment...")
        diagnostic: Diagnostic = await _run_agent_json(
            self.diagnostic_builder_agent,
            skill_set.model_dump_json(indent=2)
            + "\n\nReturn ONLY JSON matching the Diagnostic schema.",
            Diagnostic,
        )
        results["diagnostic"] = diagnostic
        print(f"    Created diagnostic with {len(diagnostic.questions)} questions")

        # Stage 3: Generate Mock Student Results
        print(f"\n[3/7] Generating mock results for {num_students} students...")
        student_list = [f"Student_{i+1}" for i in range(num_students)]
        mock_results = generate_mock_diagnostic_results(
            student_list=student_list,
            diagnostic=diagnostic,
            skill_set=skill_set
        )
        print(f"    Generated {len(mock_results)} student results")

        # Stage 4: Group Students by Quartile
        print(f"\n[4/7] Grouping students into {num_groups} groups...")
        groups_result = profile_groups_by_quartile(
            skill_set=skill_set,
            diagnostic_results=mock_results,
            num_groups=num_groups
        )
        groups = groups_result.groups
        print(f"    Created {len(groups)} groups")

        # Stage 5: Label Groups
        print("\n[5/7] Labeling groups with descriptive names...")
        labeled_groups = []
        for i, group in enumerate(groups):
            labeled_group: GroupProfile = await _run_agent_json(
                self.group_labeler_agent,
                f"""
                Group mastery profile:
                {json.dumps(group.model_dump(), indent=2)}

                Lesson context:
                {prompt_lesson_summary.model_dump_json(indent=2)}
                """,
                GroupProfile,
            )
            labeled_groups.append(labeled_group)
            print(f"    Group {i+1}: {labeled_group.group_name} ({labeled_group.mastery_level})")

        results["groups"] = labeled_groups

        # Stage 6: Generate Teaching Packs for Each Group
        print("\n[6/7] Generating teaching packs for each group...")
        for i, group in enumerate(labeled_groups):
            print(f"\n   Group {i+1}/{len(labeled_groups)}: {group.group_name}")

            # Pack Planning
            print("       Planning pack...")
            pack_plan: PackPlan = await _run_agent_json(
                self.pack_planner_agent,
                f"""
                Lesson Summary:
                {prompt_lesson_summary.model_dump_json(indent=2)}

                Skill Set:
                {skill_set.model_dump_json(indent=2)}

                Group Profile:
                {group.model_dump_json(indent=2)}
                """,
                PackPlan,
            )
            print(f"          Created plan with {len(pack_plan.slide_outline)} slides")

            # Quiz Generation
            print("       Generating quiz...")
            quiz: Quiz = await _run_agent_json(
                self.quiz_practice_agent,
                f"""
                Lesson Summary:
                {prompt_lesson_summary.model_dump_json(indent=2)}

                Pack Plan:
                {pack_plan.model_dump_json(indent=2)}

                Group Profile:
                {group.model_dump_json(indent=2)}
                """,
                Quiz,
            )
            print(f"          Generated {len(quiz.questions)} questions")

            # Slide Drafting
            print("       Drafting slides...")
            slides: Slides = await _run_agent_json(
                self.slide_drafter_agent,
                f"""
                Pack Plan:
                {pack_plan.model_dump_json(indent=2)}

                Lesson Summary:
                {prompt_lesson_summary.model_dump_json(indent=2)}

                Group Profile:
                {group.model_dump_json(indent=2)}
                """,
                Slides,
            )
            print(f"          Drafted {len(slides.slides)} slides")

            # Video Drafting
            print("       Drafting video script...")
            video: Video = await _run_agent_json(
                self.video_drafter_agent,
                f"""
                Slides:
                {slides.model_dump_json(indent=2)}

                Lesson Summary:
                {prompt_lesson_summary.model_dump_json(indent=2)}

                Group Profile:
                {group.model_dump_json(indent=2)}
                """,
                Video,
            )
            print(f"          Created video script: {video.title}")

            # Compile teaching pack
            teaching_pack = {
                "group": group,
                "pack_plan": pack_plan,
                "slides": slides,
                "video": video,
                "quiz": quiz
            }
            results["teaching_packs"].append(teaching_pack)

        print("\n[7/7] Pipeline complete!")
        print(f"    Generated {len(results['teaching_packs'])} teaching packs")

        return results


# =====================================================
# GEMINI EVALUATOR

EVALUATION_SYSTEM_PROMPT = '''You are an expert middle-school STEM teacher with experience evaluating instructional materials.

You are given:
1) A ground-truth lesson summary with key_concepts and skills
2) A generated teaching pack (slides + quiz)

Your task is to evaluate the teaching pack using three metrics:

A. Content Accuracy (Acc)
For each slide and each quiz question, judge factual correctness against the lesson summary.

Score each unit:
- 1.0 = fully correct and aligned with the lesson summary
- 0.5 = partially correct or ambiguous and could mislead
- 0.0 = incorrect or contradicts the lesson summary

B. Concept Coverage (EM)
This is semantic coverage, not exact wording.
Steps:
1) Extract all concepts from key_concepts and all skills from the skill set (if provided).
2) For each concept or skill, score coverage in the teaching pack.

Score each concept:
- 1.0 = clearly taught with correct meaning and context
- 0.5 = mentioned but incomplete, unclear, or shallow
- 0.0 = not covered

C. Educational Soundness (ES)
Score each criterion from 0 to 1:
1) Grade level appropriateness
2) Logical progression
3) Quiz alignment with taught content
4) Cognitive load management

General rules:
- Be strict and objective
- Provide short explanations for each score
- Return JSON that matches the EvaluationResult schema
'''

# =====================================================

class GeminiEvaluator:
    """Uses Gemini to evaluate teaching pack quality"""

    # Evaluation criteria for Educational Soundness
    EDUCATIONAL_CRITERIA = [
        "Grade level appropriateness (suitable for the target grade)",
        "Logical progression (easy to hard, building on prior knowledge)",
        "Quiz alignment (questions test the skills actually taught)",
        "Cognitive load management (not overwhelming, focused on objectives)"
    ]

    def __init__(self, gemini_api_key: str, gemini_model: str = "gemini-2.5-flash"):
        """Initialize Gemini evaluator"""
        provider = GoogleProvider(api_key=gemini_api_key)
        self.model = GoogleModel(gemini_model, provider=provider)

        # Create evaluation agent
        self.eval_agent = PydanticAgent(
            model=self.model,
            output_type=EvaluationResult,
            system_prompt=EVALUATION_SYSTEM_PROMPT
        )

    async def evaluate(
        self,
        lesson_summary: LessonSummary,
        teaching_pack: Dict[str, Any],
        skill_set: Optional[SkillSet] = None,
        ground_truth: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        Evaluate a teaching pack using Gemini as judge

        Args:
            lesson_summary: The original lesson summary (ground truth)
            teaching_pack: The generated teaching pack to evaluate
            skill_set: Optional skill set with all identified skills
            ground_truth: Optional additional ground truth data

        Returns:
            EvaluationResult with all metrics
        """
        print("\n" + "=" * 80)
        print("EVALUATING TEACHING PACK WITH GEMINI")
        print("=" * 80)

        # Prepare evaluation prompt
        slides = teaching_pack["slides"]
        quiz = teaching_pack["quiz"]
        group = teaching_pack["group"]

        # Build ground truth section
        ground_truth_section = f"""
# GROUND TRUTH LESSON SUMMARY

{lesson_summary.model_dump_json(indent=2)}
"""

        # Add skill set if provided (for complete concept coverage evaluation)
        if skill_set:
            ground_truth_section += f"""

# GROUND TRUTH SKILLS

{skill_set.model_dump_json(indent=2)}

**NOTE**: For Concept Coverage (EM) metric, evaluate coverage of BOTH:
- All key_concepts from lesson summary above
- All skills from the skill set above
"""

        evaluation_prompt = f"""
{ground_truth_section}

# GENERATED TEACHING PACK

## Group Profile
{group.model_dump_json(indent=2)}

## Slides (Total: {len(slides.slides)})
{slides.model_dump_json(indent=2)}

## Quiz (Total: {len(quiz.questions)} questions)
{quiz.model_dump_json(indent=2)}

---

# YOUR TASK

Evaluate this teaching pack according to the three metrics defined in your system prompt:
1. Content Accuracy (for each slide and quiz question)
2. Concept Coverage / Semantic Match (for EACH key concept AND skill from ground truth)
3. Educational Soundness (4 criteria)

IMPORTANT for Concept Coverage:
- Extract ALL concepts from lesson summary's "key_concepts" array
- Extract ALL skills from the skill set (if provided)
- Evaluate SEMANTIC coverage (not exact wording) for each one
- Score each: 1.0 (covered correctly), 0.5 (partial/unclear), 0.0 (not covered)

Be strict and objective. Provide brief explanations.
"""

        # Add ground truth if provided
        if ground_truth:
            evaluation_prompt = f"""
# ADDITIONAL GROUND TRUTH

{json.dumps(ground_truth, indent=2, ensure_ascii=False)}

{evaluation_prompt}
"""

        print("\nSending evaluation request to Gemini...")
        result = await self.eval_agent.run(evaluation_prompt)
        evaluation: EvaluationResult = result.output

        print("\n" + "=" * 80)
        print("EVALUATION COMPLETE")
        print("=" * 80)
        print(f"\n Content Accuracy:        {evaluation.accuracy_total:.2%} ({evaluation.num_slides} slides + {evaluation.num_quiz_questions} quiz questions)")
        print(f" Concept Coverage:        {evaluation.coverage_total:.2%} ({evaluation.num_concepts} concepts/skills evaluated)")
        print(f" Educational Soundness:   {evaluation.educational_soundness_total:.2%} (4 criteria)")
        print(f"\n OVERALL SCORE:           {evaluation.overall_score:.2%}")
        print(f"   Formula: 0.4Acc + 0.3EM + 0.3ES")
        print("=" * 80)

        return evaluation


# =====================================================
# MAIN EXPERIMENT RUNNER
# =====================================================

async def run_experiment(
    lesson_summary_path: str,
    ground_truth_path: Optional[str] = None,
    output_dir: str = "results/experiments",
    num_groups: int = 3,
    num_students: int = 30,
    vllm_base_url: str = "http://localhost:8000/v1",
    vllm_model: str = "Qwen/Qwen3-4B",
    vllm_api_key: str | None = None,
    vllm_lora: str | None = None,
    gemini_model: str = "gemini-2.5-flash",
):
    """
    Run the complete MAS evaluation experiment

    Args:
        lesson_summary_path: Path to lesson summary JSON file
        ground_truth_path: Optional path to ground truth JSON file
        output_dir: Directory to save results
        num_groups: Number of student groups
        num_students: Total number of students
    """
    # Load API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    # Initialize pipeline and evaluator (needed for PDF parsing too)
    print("\n Initializing MAS Pipeline (vLLM)...")
    vllm_api_key = vllm_api_key or os.getenv("VLLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    pipeline = MASPipeline(vllm_base_url, vllm_model, vllm_api_key, vllm_lora)

    print(" Initializing Gemini Evaluator...")
    evaluator = GeminiEvaluator(gemini_api_key, gemini_model)

    # Load lesson summary (JSON or PDF)
    print(f"\n Loading lesson summary from: {lesson_summary_path}")
    lesson_summary_path_obj = Path(lesson_summary_path)
    if lesson_summary_path_obj.suffix.lower() == ".pdf":
        lesson_text = extract_text_from_pdf(str(lesson_summary_path_obj))
        print("[DEBUG] Calling LessonParserAgent...")
        lesson_summary = await _run_agent_json(
            pipeline.lesson_parser_agent,
            lesson_text + "\n\nReturn ONLY JSON matching the LessonSummary schema.",
            LessonSummary,
        )
        print("[DEBUG] LessonParserAgent finished")
    else:
        with open(lesson_summary_path, 'r', encoding='utf-8') as f:
            lesson_data = json.load(f)

        # Check if it's a full teaching pack or just a lesson summary
        if "lesson_summary" in lesson_data:
            lesson_summary = LessonSummary(**lesson_data["lesson_summary"])
        else:
            lesson_summary = LessonSummary(**lesson_data)

    _trim_lesson_content(lesson_summary)

    print(f"    Loaded: {lesson_summary.title}")
    print(f"    Subject: {lesson_summary.subject}")
    print(f"    Grade: {lesson_summary.grade}")
    print(f"    Key concepts: {len(lesson_summary.key_concepts)}")

    # Load ground truth if provided
    ground_truth = None
    gt_lesson_summary: Optional[LessonSummary] = None
    gt_skill_set: Optional[SkillSet] = None
    if ground_truth_path:
        print(f"\n Loading ground truth from: {ground_truth_path}")
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
        print(f"    Ground truth loaded")

        if isinstance(ground_truth, dict):
            if "lesson_summary" in ground_truth:
                gt_lesson_summary = _normalize_lesson_summary(ground_truth["lesson_summary"])
            if "skill_set" in ground_truth:
                try:
                    gt_skill_set = SkillSet(**ground_truth["skill_set"])
                except Exception:
                    gt_skill_set = None

    # Run pipeline
    print("\n" + "=" * 80)
    print("PHASE 1: GENERATING TEACHING PACKS")
    print("=" * 80)
    results = await pipeline.run_pipeline(
        lesson_summary=lesson_summary,
        num_groups=num_groups,
        num_students=num_students
    )

    # Export teaching pack file (same format as teaching_packs_*.json in output_dir)
    serialized_packs = [
        {
            "group": tp["group"].model_dump(),
            "pack_plan": tp["pack_plan"].model_dump(),
            "slides": tp["slides"].model_dump(),
            "video": tp["video"].model_dump(),
            "quiz": tp["quiz"].model_dump(),
        }
        for tp in results["teaching_packs"]
    ]
    output_file_name = export_final_results(
        lesson_summary,
        results["skill_set"],
        results["diagnostic"],
        results["groups"],
        serialized_packs,
        num_students,
        output_dir=output_dir,
    )
    teaching_pack_output_path = Path(output_dir) / output_file_name
    print(f"\n Teaching pack exported: {teaching_pack_output_path}")

    # Reload from exported file to ensure evaluation uses the generated JSON output
    teaching_packs_for_eval: List[Dict[str, Any]] = []
    with open(teaching_pack_output_path, 'r', encoding='utf-8') as f:
        exported_data = json.load(f)
    for pack in exported_data.get("teaching_packs", []):
        teaching_packs_for_eval.append({
            "group": GroupProfile(**pack["group"]),
            "pack_plan": PackPlan(**pack["pack_plan"]),
            "slides": Slides(**pack["slides"]),
            "video": Video(**pack["video"]),
            "quiz": Quiz(**pack["quiz"]),
        })

    # Evaluate each teaching pack
    print("\n" + "=" * 80)
    print("PHASE 2: EVALUATING TEACHING PACKS")
    print("=" * 80)

    evaluations = []
    eval_lesson_summary = gt_lesson_summary or lesson_summary
    eval_skill_set = gt_skill_set or results.get("skill_set")

    for i, teaching_pack in enumerate(teaching_packs_for_eval):
        print(f"\n Evaluating teaching pack {i+1}/{len(teaching_packs_for_eval)}...")
        print(f"   Group: {teaching_pack['group'].group_name}")

        evaluation = await evaluator.evaluate(
            lesson_summary=eval_lesson_summary,
            teaching_pack=teaching_pack,
            skill_set=eval_skill_set,
            ground_truth=ground_truth
        )

        evaluations.append({
            "group_id": teaching_pack["group"].group_id,
            "group_name": teaching_pack["group"].group_name,
            "evaluation": evaluation
        })

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save complete results
    results_file = output_path / f"experiment_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "lesson_summary": lesson_summary.model_dump(),
            "skill_set": results["skill_set"].model_dump() if results.get("skill_set") else None,
            "num_groups": num_groups,
            "num_students": num_students,
            "teaching_packs": serialized_packs,
            "teaching_pack_output_file": str(teaching_pack_output_path),
            "evaluations": [
                {
                    "group_id": e["group_id"],
                    "group_name": e["group_name"],
                    "evaluation": e["evaluation"].model_dump()
                }
                for e in evaluations
            ]
        }, f, indent=2, ensure_ascii=False)

    print(f"\n Results saved to: {results_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("EXPERIMENT SUMMARY")
    print("=" * 80)

    for eval_result in evaluations:
        eval_data = eval_result["evaluation"]
        print(f"\n {eval_result['group_name']}")
        print(f"   Content Accuracy:       {eval_data.accuracy_total:.2%}")
        print(f"   Concept Coverage:       {eval_data.coverage_total:.2%}")
        print(f"   Educational Soundness:  {eval_data.educational_soundness_total:.2%}")
        print(f"   Overall Score:          {eval_data.overall_score:.2%}")

    # Calculate average scores
    avg_accuracy = sum(e["evaluation"].accuracy_total for e in evaluations) / len(evaluations)
    avg_coverage = sum(e["evaluation"].coverage_total for e in evaluations) / len(evaluations)
    avg_soundness = sum(e["evaluation"].educational_soundness_total for e in evaluations) / len(evaluations)
    avg_overall = sum(e["evaluation"].overall_score for e in evaluations) / len(evaluations)

    print("\n" + "=" * 80)
    print("AVERAGE SCORES ACROSS ALL GROUPS")
    print("=" * 80)
    print(f"\n Avg Content Accuracy:       {avg_accuracy:.2%}")
    print(f" Avg Concept Coverage:       {avg_coverage:.2%}")
    print(f" Avg Educational Soundness:  {avg_soundness:.2%}")
    print(f"\n AVG OVERALL SCORE:          {avg_overall:.2%}")
    print("=" * 80)


# =====================================================
# CLI ENTRY POINT
# =====================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run MAS evaluation experiment with Qwen vLLM generation and Gemini as judge"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yaml",
        help="Path to YAML config file (default: config/default.yaml)"
    )
    parser.add_argument(
        "--lesson_summary",
        type=str,
        required=True,
        help="Path to lesson summary JSON file or PDF lesson file"
    )
    parser.add_argument(
        "--ground_truth",
        type=str,
        default=None,
        help="Path to ground truth JSON file (optional)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Directory to save results (default: from config)"
    )
    parser.add_argument(
        "--num_groups",
        type=int,
        default=None,
        help="Number of student groups (default: from config)"
    )
    parser.add_argument(
        "--num_students",
        type=int,
        default=None,
        help="Total number of students (default: from config)"
    )
    parser.add_argument(
        "--vllm_base_url",
        type=str,
        default=None,
        help="vLLM OpenAI-compatible base URL (default: from config)"
    )
    parser.add_argument(
        "--vllm_model",
        type=str,
        default=None,
        help="Model name served by vLLM (default: from config)"
    )
    parser.add_argument(
        "--vllm_lora",
        type=str,
        default=None,
        help="Optional LoRA name registered in vLLM (passes extra_body.lora)"
    )
    parser.add_argument(
        "--vllm_api_key",
        type=str,
        default=None,
        help="Optional API key for vLLM/OpenAI-compatible server"
    )
    parser.add_argument(
        "--gemini_model",
        type=str,
        default=None,
        help="Gemini model to use for evaluation (default: from config)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed (default: from config)"
    )

    args = parser.parse_args()

    config = load_config(args.config)
    num_groups = resolve_value(args.num_groups, config, ["evaluation", "num_groups"], 3)
    num_students = resolve_value(args.num_students, config, ["evaluation", "num_students"], 30)
    output_dir = resolve_value(args.output_dir, config, ["paths", "output_dir"], "results/experiments")
    seed = resolve_value(args.seed, config, ["seed"], None)

    vllm_base_url = resolve_value(args.vllm_base_url, config, ["models", "vllm", "base_url"], "http://localhost:8000/v1")
    vllm_model = resolve_value(args.vllm_model, config, ["models", "vllm", "model"], "Qwen/Qwen3-4B")
    vllm_lora = resolve_value(args.vllm_lora, config, ["models", "vllm", "lora"], None)
    vllm_api_key = resolve_value(args.vllm_api_key, config, ["models", "vllm", "api_key"], None)
    gemini_model = resolve_value(args.gemini_model, config, ["models", "mas", "evaluator"], "gemini-2.5-flash")

    set_seed(seed)

    # Run experiment
    asyncio.run(run_experiment(
        lesson_summary_path=args.lesson_summary,
        ground_truth_path=args.ground_truth,
        output_dir=output_dir,
        num_groups=num_groups,
        num_students=num_students,
        vllm_base_url=vllm_base_url,
        vllm_model=vllm_model,
        vllm_api_key=vllm_api_key,
        vllm_lora=vllm_lora,
        gemini_model=gemini_model,
    ))


if __name__ == "__main__":
    main()
