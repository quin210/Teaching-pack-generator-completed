"""
MAS Evaluation Experiment (Qwen3-4B SFT-GRPO-DPO via vLLM)
==========================================================

This script evaluates the Multi-Agent System (MAS) for teaching pack generation using three metrics:
1. Content Accuracy (Acc) - Factual correctness of slides and quiz
2. Exact Match / Semantic Coverage (EM) - Coverage of key concepts from lesson summary
3. Educational Soundness (ES) - Pedagogical appropriateness

Generation: Qwen3-4B with the SFT-GRPO-DPO LoRA adapter in vLLM
Evaluation: Gemini (configurable)

Usage:
    python experiments/mas_evaluation_experiment_vllm_qwen3_grpo_dpo.py --lesson_summary <path> --ground_truth <path>
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
# DEFAULTS
# =====================================================

DEFAULT_VLLM_MODEL = "Qwen/Qwen3-4B"
DEFAULT_VLLM_LORA = "qwen3-grpo-dpo"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


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


def _compact_raw_text(text: str, max_chars: int = 3500) -> str:
    """Normalize whitespace and trim raw lesson text for small context windows."""
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    trimmed = cleaned[:max_chars]
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    return trimmed + " ..."


def _compact_lesson_summary(lesson_summary: LessonSummary) -> LessonSummary:
    """Create a compact lesson summary for prompt usage."""
    compact = lesson_summary.model_copy(deep=True)
    compact.lesson_content = ""
    compact.examples = (compact.examples or [])[:3]
    if compact.definitions:
        items = list(compact.definitions.items())[:6]
        compact.definitions = {k: v for k, v in items}
    return compact


def _compact_pack_plan_for_quiz(pack_plan: PackPlan) -> Dict[str, Any]:
    """Reduce pack plan payload for quiz generation."""
    data = pack_plan.model_dump()
    data.pop("slide_outline", None)
    data.pop("differentiation_strategy", None)
    data["learning_objectives"] = (data.get("learning_objectives") or [])[:3]
    quiz_blueprint = data.get("quiz_blueprint")
    if isinstance(quiz_blueprint, list):
        data["quiz_blueprint"] = quiz_blueprint[:1]
    return data


def _compact_lesson_summary_for_quiz(lesson_summary: LessonSummary) -> Dict[str, Any]:
    """Minimize lesson summary context for quiz generation."""
    return {
        "title": lesson_summary.title,
        "subject": lesson_summary.subject,
        "grade": lesson_summary.grade,
        "key_concepts": (lesson_summary.key_concepts or [])[:6],
    }


def _fallback_quiz_from_plan(pack_plan: PackPlan, skill_set: SkillSet) -> Quiz:
    """Create a minimal valid quiz if the model output is unusable."""
    questions = []
    skills = []
    for qb in pack_plan.quiz_blueprint or []:
        if isinstance(qb, dict) and qb.get("skill_id"):
            skills.append(str(qb["skill_id"]))
    if not skills and skill_set.skills:
        skills = [skill_set.skills[0].skill_id]
    if not skills:
        skills = [""]

    num_q = 3
    for idx in range(num_q):
        skill_id = skills[idx % len(skills)]
        questions.append(
            {
                "question_id": f"q{idx+1}",
                "question_text": "Cu hi trc nghim v bi hc.",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "skill_id": skill_id,
                "difficulty": "medium",
                "hint": "",
                "explanation": "",
            }
        )

    return Quiz(
        questions=questions,
        practice_exercises=[],
        answer_key={},
        total_questions=len(questions),
        estimated_time=max(5, len(questions) * 2),
    )


def _compact_skill_set_for_prompt(skill_set: SkillSet) -> Dict[str, Any]:
    """Reduce skill set payload for small context windows."""
    return {
        "skills": [
            {
                "skill_id": s.skill_id,
                "name": s.name,
                "description": s.description,
                "weight": s.weight,
                "is_prerequisite": s.is_prerequisite,
            }
            for s in (skill_set.skills or [])[:6]
        ],
        "skill_dependencies": {},
    }


def _fallback_pack_plan(
    lesson_summary: LessonSummary,
    skill_set: SkillSet,
    group: GroupProfile,
) -> PackPlan:
    """Create a minimal valid pack plan if the model output is unusable."""
    objectives = (lesson_summary.key_concepts or [])[:3]
    slide_outline = [
        {"title": str(concept), "key_points": str(concept)}
        for concept in (lesson_summary.key_concepts or [])[:6]
    ]
    if not slide_outline:
        slide_outline = [{"title": "Overview", "key_points": "Key ideas and objectives"}]

    quiz_blueprint = []
    for skill in (skill_set.skills or [])[:3]:
        quiz_blueprint.append({"skill_id": skill.skill_id, "difficulty": "medium"})
    if not quiz_blueprint:
        quiz_blueprint = [{"skill_id": "", "difficulty": "medium"}]

    return PackPlan(
        group_id=group.group_id,
        learning_objectives=objectives,
        slide_outline=slide_outline,
        quiz_blueprint=quiz_blueprint,
        estimated_time=40,
        differentiation_strategy="iu chnh mc  h tr theo nhm.",
    )


def _compact_pack_plan_for_slides(pack_plan: PackPlan) -> Dict[str, Any]:
    """Reduce pack plan payload for slide drafting."""
    data = pack_plan.model_dump()
    data.pop("quiz_blueprint", None)
    data.pop("estimated_time", None)
    data.pop("differentiation_strategy", None)
    data["learning_objectives"] = (data.get("learning_objectives") or [])[:3]
    slide_outline = data.get("slide_outline")
    if isinstance(slide_outline, list):
        data["slide_outline"] = slide_outline[:8]
    return data


def _fallback_slides_from_plan(pack_plan: PackPlan) -> Slides:
    """Create minimal slides from the pack plan outline."""
    slides = []
    for idx, item in enumerate(pack_plan.slide_outline or [], start=1):
        title = ""
        content = ""
        if isinstance(item, dict):
            title = str(item.get("title") or item.get("slide_title") or "")
            content = str(item.get("key_points") or item.get("content") or "")
        if not title:
            title = f"Slide {idx}"
        slides.append(
            {
                "slide_id": f"slide_{idx}",
                "title": title,
                "content": content,
                "visual_notes": "",
                "speaker_notes": "",
            }
        )
    if not slides:
        slides = [
            {
                "slide_id": "slide_1",
                "title": "Overview",
                "content": "Key ideas and objectives",
                "visual_notes": "",
                "speaker_notes": "",
            }
        ]
    return Slides(slides=slides, generated_url=None)


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
                        if "options" not in fixed_q:
                            fixed_q["options"] = fixed_q.get("choices") or []
                        if not isinstance(fixed_q.get("options"), list):
                            fixed_q["options"] = [str(fixed_q["options"])]
                        diff = fixed_q.get("difficulty")
                        diff_norm = str(diff).lower() if diff is not None else "medium"
                        if diff_norm not in ("easy", "medium", "hard"):
                            diff_norm = "medium"
                        fixed_q["difficulty"] = diff_norm
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


async def _run_agent_json(
    agent: Any,
    prompt: str,
    model_cls: Any,
    retries: int = 2,
    max_tokens: int = 512,
) -> Any:
    last_err: Exception | None = None
    current_max_tokens = max_tokens
    parse_attempts = 0
    token_adjusts = 0
    json_adjusts = 0
    max_allowed: int | None = None
    while parse_attempts <= retries:
        try:
            result = await agent.run(prompt, model_settings={"max_tokens": current_max_tokens})
        except Exception as err:
            allowed = _extract_max_tokens_limit(err)
            if allowed is not None and token_adjusts < 10:
                max_allowed = allowed
                current_max_tokens = max(16, allowed - 64)
                last_err = err
                token_adjusts += 1
                continue
            msg = str(err)
            if (
                token_adjusts < 10
                and ("max_tokens" in msg or "maximum context length" in msg)
                and current_max_tokens > 32
            ):
                current_max_tokens = max(32, int(current_max_tokens * 0.6))
                last_err = err
                token_adjusts += 1
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
            if "Unclosed JSON object" in err_text and json_adjusts < 10:
                if max_allowed is None:
                    current_max_tokens += 64
                elif current_max_tokens < max_allowed - 8:
                    current_max_tokens = min(max_allowed - 8, current_max_tokens + 64)
                json_adjusts += 1
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
            + "\n\nKeep it concise: exactly 5 questions. Short options and rationale (<=10 words)."
            + "\nReturn ONLY JSON matching the Diagnostic schema.",
            Diagnostic,
            max_tokens=900,
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
        used_group_names: set[str] = set()
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
            raw_name = (labeled_group.group_name or "").strip()
            if not raw_name:
                raw_name = f"Group {i+1}"
            name = raw_name
            suffix = 1
            while name.lower() in used_group_names:
                suffix += 1
                name = f"{raw_name} {suffix}"
            labeled_group.group_name = name
            used_group_names.add(name.lower())
            labeled_groups.append(labeled_group)
            print(f"    Group {i+1}: {labeled_group.group_name} ({labeled_group.mastery_level})")

        results["groups"] = labeled_groups

        # Stage 6: Generate Teaching Packs for Each Group
        print("\n[6/7] Generating teaching packs for each group...")
        for i, group in enumerate(labeled_groups):
            print(f"\n   Group {i+1}/{len(labeled_groups)}: {group.group_name}")

            # Pack Planning
            print("      ... Planning pack...")
            compact_skill_set = _compact_skill_set_for_prompt(skill_set)
            group_context = json.dumps(
                {
                    "group_id": group.group_id,
                    "mastery_level": group.mastery_level,
                    "learning_pace": group.learning_pace,
                },
                indent=2,
                ensure_ascii=False,
            )
            pack_plan_prompt = f"""
                Lesson Summary (compact):
                {prompt_lesson_summary.model_dump_json(indent=2)}

                Skill Set (compact):
                {json.dumps(compact_skill_set, indent=2, ensure_ascii=False)}

                Group Profile (compact):
                {group_context}
                """.strip()
            pack_plan_prompt += (
                "\n\nConstraints:"
                "\n- slide_outline must have 6-8 items, each with title and key_points."
                "\n- quiz_blueprint must have at least 3 items."
                "\n- Keep all text short (<=10 words each)."
                "\nReturn ONLY JSON matching the PackPlan schema."
            )
            pack_plan: PackPlan
            try:
                pack_plan = await _run_agent_json(
                    self.pack_planner_agent,
                    pack_plan_prompt,
                    PackPlan,
                    max_tokens=480,
                )
            except ValueError as err:
                if "Unclosed JSON object" in str(err):
                    try:
                        lite_prompt = (
                            pack_plan_prompt
                            + "\n\nIMPORTANT: Return MINIMAL JSON only. "
                            + "Keep each field short and avoid extra text."
                        )
                        pack_plan = await _run_agent_json(
                            self.pack_planner_agent,
                            lite_prompt,
                            PackPlan,
                            retries=1,
                            max_tokens=320,
                        )
                    except Exception as inner_err:
                        print(f"[WARN] PackPlan JSON truncated. Using fallback. {inner_err}")
                        pack_plan = _fallback_pack_plan(lesson_summary, skill_set, group)
                else:
                    print(f"[WARN] PackPlan parse failed. Using fallback. {err}")
                    pack_plan = _fallback_pack_plan(lesson_summary, skill_set, group)
            except Exception as err:
                print(f"[WARN] PackPlan generation failed. Using fallback. {err}")
                pack_plan = _fallback_pack_plan(lesson_summary, skill_set, group)
            if not pack_plan.slide_outline:
                fallback = []
                for concept in (lesson_summary.key_concepts or [])[:6]:
                    fallback.append({"title": str(concept), "key_points": str(concept)})
                if not fallback:
                    fallback = [{"title": "Overview", "key_points": "Key ideas and objectives"}]
                pack_plan.slide_outline = fallback
            if not pack_plan.quiz_blueprint:
                first_skill = skill_set.skills[0].skill_id if skill_set.skills else ""
                pack_plan.quiz_blueprint = [{"skill_id": first_skill, "difficulty": "medium"}]
            print(f"         ... Created plan with {len(pack_plan.slide_outline)} slides")
            # Quiz Generation
            print("      ... Generating quiz...")
            compact_plan = _compact_pack_plan_for_quiz(pack_plan)
            lesson_context = json.dumps(
                _compact_lesson_summary_for_quiz(lesson_summary),
                indent=2,
                ensure_ascii=False,
            )
            group_context = json.dumps(
                {
                    "group_id": group.group_id,
                    "mastery_level": group.mastery_level,
                    "learning_pace": group.learning_pace,
                },
                indent=2,
                ensure_ascii=False,
            )
            quiz_prompt = f"""
                Lesson Summary (compact):
                {lesson_context}

                Pack Plan (compact):
                {json.dumps(compact_plan, indent=2, ensure_ascii=False)}

                Group Profile (compact):
                {group_context}
                """.strip()
            quiz_prompt += (
                "\n\nConstraints:"
                "\n- exactly 5 questions"
                "\n- each question has 4 options"
                "\n- practice_exercises must be []"
                "\n- answer_key must be {}"
                "\n- total_questions must be 5"
                "\n- estimated_time must be an integer (minutes)"
                "\n- keep explanations short (<=10 words)"
                "\nReturn ONLY JSON matching the Quiz schema."
            )
            quiz: Quiz
            try:
                quiz = await _run_agent_json(
                    self.quiz_practice_agent,
                    quiz_prompt,
                    Quiz,
                    max_tokens=480,
                )
            except ValueError as err:
                if "Unclosed JSON object" in str(err):
                    try:
                        lite_prompt = (
                            quiz_prompt
                            + "\n\nIMPORTANT: Return MINIMAL JSON only. "
                            + "Keep each field short and avoid extra text."
                        )
                        quiz = await _run_agent_json(
                            self.quiz_practice_agent,
                            lite_prompt,
                            Quiz,
                            retries=1,
                            max_tokens=320,
                        )
                    except Exception as inner_err:
                        print(f"[WARN] Quiz JSON truncated. Using fallback. {inner_err}")
                        quiz = _fallback_quiz_from_plan(pack_plan, skill_set)
                else:
                    print(f"[WARN] Quiz parse failed. Using fallback. {err}")
                    quiz = _fallback_quiz_from_plan(pack_plan, skill_set)
            except Exception as err:
                print(f"[WARN] Quiz generation failed. Using fallback. {err}")
                quiz = _fallback_quiz_from_plan(pack_plan, skill_set)
            print(f"         ... Generated {len(quiz.questions)} questions")

            # Slide Drafting
            print("       Drafting slides...")
            compact_plan = _compact_pack_plan_for_slides(pack_plan)
            group_context = json.dumps(
                {
                    "group_id": group.group_id,
                    "mastery_level": group.mastery_level,
                    "learning_pace": group.learning_pace,
                },
                indent=2,
                ensure_ascii=False,
            )
            slide_prompt = f"""
                Lesson Summary (compact):
                {prompt_lesson_summary.model_dump_json(indent=2)}

                Pack Plan (compact):
                {json.dumps(compact_plan, indent=2, ensure_ascii=False)}

                Group Profile (compact):
                {group_context}
                """.strip()
            slide_prompt += (
                "\n\nConstraints:"
                "\n- number of slides must match slide_outline count"
                "\n- keep each title/content short (<=12 words)"
                "\n- visual_notes and speaker_notes can be empty"
                "\nReturn ONLY JSON matching the Slides schema."
            )
            slides: Slides
            try:
                slides = await _run_agent_json(
                    self.slide_drafter_agent,
                    slide_prompt,
                    Slides,
                    max_tokens=480,
                )
            except ValueError as err:
                if "Unclosed JSON object" in str(err):
                    try:
                        lite_prompt = (
                            slide_prompt
                            + "\n\nIMPORTANT: Return MINIMAL JSON only. "
                            + "Keep each field short and avoid extra text."
                        )
                        slides = await _run_agent_json(
                            self.slide_drafter_agent,
                            lite_prompt,
                            Slides,
                            retries=1,
                            max_tokens=320,
                        )
                    except Exception as inner_err:
                        print(f"[WARN] Slides JSON truncated. Using fallback. {inner_err}")
                        slides = _fallback_slides_from_plan(pack_plan)
                else:
                    print(f"[WARN] Slides parse failed. Using fallback. {err}")
                    slides = _fallback_slides_from_plan(pack_plan)
            except Exception as err:
                print(f"[WARN] Slides generation failed. Using fallback. {err}")
                slides = _fallback_slides_from_plan(pack_plan)
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

    def __init__(self, gemini_api_key: str, gemini_model: str = DEFAULT_GEMINI_MODEL):
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

        # Normalize and clamp scores in case the judge returns invalid values
        def _clamp01(value: Any) -> float:
            try:
                val = float(value)
            except Exception:
                return 0.0
            if val < 0.0:
                return 0.0
            if val > 1.0:
                return 1.0
            return val

        def _safe_avg(values: List[float]) -> float:
            if not values:
                return 0.0
            return sum(values) / len(values)

        for score in evaluation.accuracy_scores:
            score.accuracy = _clamp01(score.accuracy)
        for coverage in evaluation.concept_coverage:
            coverage.coverage = _clamp01(coverage.coverage)
        for soundness in evaluation.educational_soundness:
            soundness.score = _clamp01(soundness.score)

        evaluation.accuracy_total = _safe_avg([s.accuracy for s in evaluation.accuracy_scores])
        evaluation.coverage_total = _safe_avg([c.coverage for c in evaluation.concept_coverage])
        evaluation.educational_soundness_total = _safe_avg([s.score for s in evaluation.educational_soundness])
        evaluation.overall_score = (
            0.4 * evaluation.accuracy_total
            + 0.3 * evaluation.coverage_total
            + 0.3 * evaluation.educational_soundness_total
        )
        evaluation.num_slides = len(teaching_pack["slides"].slides)
        evaluation.num_quiz_questions = len(teaching_pack["quiz"].questions)
        evaluation.num_concepts = len(evaluation.concept_coverage)

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
    vllm_model: str = DEFAULT_VLLM_MODEL,
    vllm_api_key: str | None = None,
    vllm_lora: str | None = DEFAULT_VLLM_LORA,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
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
        raw_text = extract_text_from_pdf(str(lesson_summary_path_obj))
        original_len = len(raw_text)
        max_chars = 3500
        attempt = 0
        while True:
            lesson_text = _compact_raw_text(raw_text, max_chars=max_chars)
            if attempt == 0 and len(lesson_text) < original_len:
                print(
                    f"[DEBUG] Trimmed lesson text from {original_len} to {len(lesson_text)} chars for context limits."
                )
            print("[DEBUG] Calling LessonParserAgent...")
            try:
                lesson_summary = await _run_agent_json(
                    pipeline.lesson_parser_agent,
                    lesson_text + "\n\nReturn ONLY JSON matching the LessonSummary schema.",
                    LessonSummary,
                )
                print("[DEBUG] LessonParserAgent finished")
                break
            except ModelHTTPError as err:
                if "maximum context length" in str(err) and max_chars > 800:
                    attempt += 1
                    max_chars = max(800, int(max_chars * 0.7))
                    print(f"[WARN] Context limit hit. Retrying with max_chars={max_chars}.")
                    continue
                raise
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
        description="Run MAS evaluation with Qwen3-4B SFT-GRPO-DPO (vLLM LoRA) and Gemini 2.0 Flash"
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
        "--config",
        type=str,
        default="config/default.yaml",
        help="Path to YAML config file (default: config/default.yaml)"
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
        help="LoRA name registered in vLLM (default: from config)"
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
    vllm_model = resolve_value(args.vllm_model, config, ["models", "vllm", "model"], DEFAULT_VLLM_MODEL)
    vllm_lora = resolve_value(args.vllm_lora, config, ["models", "vllm", "lora"], DEFAULT_VLLM_LORA)
    vllm_api_key = resolve_value(args.vllm_api_key, config, ["models", "vllm", "api_key"], None)
    gemini_model = resolve_value(args.gemini_model, config, ["models", "mas", "evaluator"], DEFAULT_GEMINI_MODEL)

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
