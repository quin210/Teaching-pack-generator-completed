# src/api/app_context.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from llm.base import AgentClient

# prompts
from data.prompts.teaching_pack_prompts import (
    LESSON_PARSER_PROMPT, SKILL_MAPPER_PROMPT, DIAGNOSTIC_BUILDER_PROMPT,
    GROUP_LABELER_PROMPT, PACK_PLANNER_PROMPT,
    QUIZ_PRACTICE_PROMPT, SLIDE_DRAFTER_PROMPT, VIDEO_DRAFTER_PROMPT
)
from data.prompts.flashcard_prompts import (
    FLASHCARD_GENERATOR_PROMPT, FLASHCARD_GROUP_GENERATOR_PROMPT
)
from data.prompts.study_prompts import THEORY_QUESTION_GENERATOR_PROMPT

# models
from models.teaching_pack_models import (
    LessonSummary, SkillSet, Diagnostic, GroupProfile, PackPlan, Slides, Quiz
)
from models.flashcard_models import FlashcardSet
from models.study_models import TheoryQuestionSet

# tools
from utils.basetools.pdf_parser import extract_text_from_pdf

# ====== OUTPUT DIR ======
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# ====== MODEL ======
provider = GoogleProvider(api_key=os.getenv("GEMINI_API_KEY"))
model = GoogleModel("gemini-2.0-flash", provider=provider)

# ====== AGENTS ======
lesson_parser_agent = AgentClient(
    model=model, system_prompt=LESSON_PARSER_PROMPT, tools=[extract_text_from_pdf]
).create_agent(result_type=LessonSummary)

skill_mapper_agent = AgentClient(
    model=model, system_prompt=SKILL_MAPPER_PROMPT, tools=[]
).create_agent(result_type=SkillSet)

diagnostic_builder_agent = AgentClient(
    model=model, system_prompt=DIAGNOSTIC_BUILDER_PROMPT, tools=[]
).create_agent(result_type=Diagnostic)

group_labeler_agent = AgentClient(
    model=model, system_prompt=GROUP_LABELER_PROMPT, tools=[]
).create_agent(result_type=GroupProfile)

pack_planner_agent = AgentClient(
    model=model, system_prompt=PACK_PLANNER_PROMPT, tools=[]
).create_agent(result_type=PackPlan)

slide_drafter_agent = AgentClient(
    model=model, system_prompt=SLIDE_DRAFTER_PROMPT, tools=[]
).create_agent(result_type=Slides)

quiz_practice_agent = AgentClient(
    model=model, system_prompt=QUIZ_PRACTICE_PROMPT, tools=[]
).create_agent(result_type=Quiz)

theory_question_agent = AgentClient(
    model=model, system_prompt=THEORY_QUESTION_GENERATOR_PROMPT, tools=[]
).create_agent(result_type=TheoryQuestionSet)

flashcard_agent = AgentClient(
    model=model, system_prompt=FLASHCARD_GENERATOR_PROMPT, tools=[]
).create_agent(result_type=FlashcardSet)

flashcard_group_agent = AgentClient(
    model=model, system_prompt=FLASHCARD_GROUP_GENERATOR_PROMPT, tools=[]
).create_agent(result_type=FlashcardSet)

video_drafter_agent = AgentClient(
    model=model, system_prompt=VIDEO_DRAFTER_PROMPT, tools=[]
).create_agent()
