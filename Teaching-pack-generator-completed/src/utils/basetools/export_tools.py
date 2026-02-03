"""
Export Tools
Export teaching packs to various formats (JSON, PDF, DOCX, etc.)
"""
import json
from typing import List
from models.teaching_pack_models import TeachingPack, SystemOutput


def export_to_json(teaching_packs: List[TeachingPack], output_path: str) -> None:
    """
    Export teaching packs to JSON file
    
    Args:
        teaching_packs: List of teaching packs
        output_path: Output file path
    """
    data = [pack.model_dump() for pack in teaching_packs]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_system_output(system_output: SystemOutput, output_path: str) -> None:
    """
    Export complete system output to JSON
    
    Args:
        system_output: Complete system output
        output_path: Output file path
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(system_output.model_dump(), f, ensure_ascii=False, indent=2)


def format_pack_for_display(pack: TeachingPack) -> str:
    """
    Format teaching pack for readable display
    
    Args:
        pack: Teaching pack
    
    Returns:
        Formatted string
    """
    output = f"""
{'='*60}
TEACHING PACK: {pack.group_name}
{'='*60}

GROUP ID: {pack.group_id}
ESTIMATED TIME: {pack.total_estimated_time} minutes

LEARNING OBJECTIVES:
{chr(10).join(f"  {i+1}. {obj}" for i, obj in enumerate(pack.learning_objectives))}

DIFFERENTIATION STRATEGY:
{pack.differentiation_notes}

{'='*60}
SLIDES ({len(pack.slides)} slides)
{'='*60}
"""
    
    for i, slide in enumerate(pack.slides, 1):
        output += f"""
Slide {i}: {slide.title}
Time: {slide.estimated_time} min

Content:
{slide.content}

Teacher Notes:
{slide.teacher_notes}

{'-'*60}
"""
    
    output += f"""
{'='*60}
QUIZ ({len(pack.quiz)} questions)
{'='*60}
"""
    
    for i, q in enumerate(pack.quiz, 1):
        output += f"""
Question {i} ({q.difficulty}):
{q.question_text}

Options:
{chr(10).join(f"  {opt}" for opt in q.options)}

Correct Answer: {q.correct_answer}
Hint: {q.hint}

{'-'*60}
"""
    
    return output
