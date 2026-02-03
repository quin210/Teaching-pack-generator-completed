"""
Pydantic models for the Teaching Pack Generator system
Define schemas for lessons, skills, groups, teaching packs, errors
"""
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


# ============= LESSON MODELS =============

class LessonSummary(BaseModel):
    """Lesson summary after parsing"""
    title: str = Field(description="Lesson title")
    subject: str = Field(description="Subject (Math, Vietnamese, ...)")
    grade: str = Field(description="Grade level (1, 2, 3, ...)")
    key_concepts: List[str] = Field(description="Main concepts")
    definitions: Dict[str, str] = Field(default_factory=dict, description="Concept definitions")
    examples: List[str] = Field(default_factory=list, description="Examples in the document")
    lesson_content: str = Field(description="Full lesson content")


class Skill(BaseModel):
    """A specific skill"""
    skill_id: str = Field(description="Unique ID of skill")
    name: str = Field(description="Skill name")
    description: str = Field(description="Detailed description")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Weight in this lesson")
    is_prerequisite: bool = Field(default=False, description="Is this a prerequisite")


class SkillSet(BaseModel):
    """Set of skills for a lesson"""
    skills: List[Skill] = Field(description="List of skills")
    skill_dependencies: Dict[str, List[str]] = Field(
        default_factory=dict, 
        description="Dependencies between skills (skill_id -> [prerequisite_ids])"
    )


# ============= DIAGNOSTIC MODELS =============

class DiagnosticQuestion(BaseModel):
    """A question in the diagnostic"""
    question_id: str
    question_text: str
    options: List[str] = Field(description="Answer choices (if MCQ)")
    correct_answer: str
    skill_id: str = Field(description="Skill being assessed")
    difficulty: Literal["easy", "medium", "hard"]
    rationale: str = Field(description="Explanation of answer")


class Diagnostic(BaseModel):
    """Diagnostic question set"""
    questions: List[DiagnosticQuestion]
    total_questions: int = Field(description="Total number of questions")
    skills_covered: List[str] = Field(description="Skills covered")


class StudentDiagnosticResult(BaseModel):
    """Diagnostic result for one student"""
    student_id: str
    student_name: str
    answers: Dict[str, str] = Field(description="question_id -> student_answer")
    score: float = Field(ge=0.0, le=1.0, description="Proportion correct")
    skill_mastery: Dict[str, float] = Field(description="skill_id -> mastery level (0-1)")
    misconceptions: List[str] = Field(default_factory=list, description="Common errors")


# ============= GROUPING MODELS =============

class GroupProfile(BaseModel):
    """Profile of a student group"""
    group_id: str
    group_name: str = Field(description="Readable name (e.g., Building Foundations, Standard, Strong, Advanced)")
    description: str = Field(description="Group characteristics description")
    mastery_level: Literal["low", "medium", "high", "advanced"] = Field(
        description="Overall mastery level"
    )
    skill_mastery: Dict[str, float] = Field(description="Average mastery of group for each skill")
    common_misconceptions: List[str] = Field(default_factory=list)
    learning_pace: Literal["slow", "moderate", "fast"]
    students: List[str] = Field(description="List of student_ids")
    recommended_activities: List[str] = Field(default_factory=list)


class GroupingResult(BaseModel):
    """Grouping result"""
    groups: List[GroupProfile]
    rationale: str = Field(description="Explanation of grouping method")
    total_students: int


# ============= TEACHING PACK MODELS =============

class Slide(BaseModel):
    """A single slide in a presentation"""
    slide_id: str = Field(description="Unique slide identifier")
    title: str = Field(description="Slide title")
    content: str = Field(description="Main slide content")
    visual_notes: Optional[str] = Field(default=None, description="Notes for visual elements")
    speaker_notes: Optional[str] = Field(default=None, description="Speaker notes")


class Slides(BaseModel):
    """Collection of slides for a teaching pack"""
    slides: List[Slide] = Field(description="List of slides")
    generated_url: Optional[str] = Field(default=None, description="URL to generated slide deck if available")


class QuizQuestion(BaseModel):
    """A quiz question"""
    question_id: str
    question_text: str
    options: List[str]
    correct_answer: str
    skill_id: str
    difficulty: Literal["easy", "medium", "hard"]
    hint: str = Field(description="Hint for students")
    explanation: str = Field(description="Explanation of correct answer")


class PracticeExercise(BaseModel):
    """A practice exercise"""
    exercise_id: str
    title: str
    instructions: str
    problems: List[str] = Field(description="List of practice problems")
    answer_key: List[str] = Field(description="Answers for each problem")
    difficulty: Literal["easy", "medium", "hard"]


class Quiz(BaseModel):
    """Quiz for a teaching pack"""
    questions: List[QuizQuestion] = Field(description="List of quiz questions")
    practice_exercises: List[PracticeExercise] = Field(description="List of practice exercises")
    answer_key: Dict[str, str] = Field(default_factory=dict, description="question_id -> correct_answer with explanation")
    total_questions: int = Field(description="Total number of questions")
    estimated_time: int = Field(description="Estimated time in minutes")


class TeachingPack(BaseModel):
    """Complete teaching pack for a group"""
    group_id: str
    group_name: str
    learning_objectives: List[str]
    slides: List[Slide]
    quiz: List[QuizQuestion]
    practice_exercises: List[PracticeExercise]
    total_estimated_time: int = Field(description="Total time in minutes")
    differentiation_notes: str = Field(description="How this pack is differentiated")


# ============= VERIFICATION MODELS =============

class ErrorType(str, Enum):
    """Types of validation errors"""
    GROUNDING = "grounding"  # Not from source
    CURRICULUM = "curriculum"  # Grade-inappropriate
    QUIZ_VALIDITY = "quiz_validity"  # Invalid question
    TEACH_TEST_ALIGNMENT = "teach_test_alignment"  # Mismatch between taught and tested


class ValidationError(BaseModel):
    """A validation error"""
    error_type: ErrorType
    severity: Literal["critical", "warning"]
    location: str = Field(description="Where the error is (slide_id, question_id, etc.)")
    description: str = Field(description="What's wrong")
    suggestion: str = Field(description="How to fix")


class VerificationReport(BaseModel):
    """Complete verification report"""
    pack_id: str
    is_valid: bool = Field(description="Overall pass/fail")
    errors: List[ValidationError]
    warnings: List[ValidationError]
    timestamp: str
    recommendations: List[str] = Field(default_factory=list, description="General improvement suggestions")


# ============= SYSTEM MODELS =============

class SystemInput(BaseModel):
    """Input to the entire system"""
    lesson_source: str = Field(description="Path to PDF or lesson text")
    student_list: List[str] = Field(description="List of student names")
    student_scores: Optional[Dict[str, float]] = Field(
        default=None, 
        description="Previous test scores (optional)"
    )
    diagnostic_results: Optional[List[StudentDiagnosticResult]] = Field(
        default=None,
        description="Pre-existing diagnostic results (optional)"
    )
    num_groups: int = Field(default=4, description="Number of groups to create")


class SystemOutput(BaseModel):
    """Output from the entire system"""
    lesson_summary: LessonSummary
    skill_set: SkillSet
    diagnostic: Optional[Diagnostic] = None
    diagnostic_results: List[StudentDiagnosticResult]
    grouping_result: GroupingResult
    teaching_packs: List[TeachingPack]
    verification_reports: List[VerificationReport]
    processing_log: List[str] = Field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None


# ============= INTERMEDIATE MODELS =============

class PackPlan(BaseModel):
    """Teaching pack outline (intermediate step)"""
    group_id: str
    learning_objectives: List[str]
    slide_outline: List[Dict[str, str]]  # [{"title": "...", "key_points": "..."}]
    quiz_blueprint: List[Dict[str, str]]  # [{"skill_id": "...", "difficulty": "..."}]
    estimated_time: int
    differentiation_strategy: str


class Video(BaseModel):
    """Educational video content"""
    title: str = Field(description="Video title")
    duration_seconds: int = Field(description="Target duration")
    script: str = Field(description="Narration script")
    visual_description: str = Field(description="Description of visuals and animations")
    key_concepts: List[str] = Field(description="Concepts covered in video")
    generated_url: Optional[str] = Field(default=None, description="URL to generated video if available")
    thumbnail_url: Optional[str] = Field(default=None, description="URL to video thumbnail if available")
