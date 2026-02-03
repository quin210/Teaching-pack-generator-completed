"""
Homogeneous Grouping Utilities

This module groups students with similar proficiency levels for a target subject.
"""

from typing import List, Dict
from loguru import logger
from llm.base import AgentClient, model
import json


async def heterogeneous_grouping_by_subject(
    students: List[Dict],
    subject: str,
    num_groups: int = 4,
) -> Dict[str, List[Dict]]:
    """
    Group students into homogeneous groups using an AI agent.

    Strategy:
    - Convert student records to text
    - Ask the AI agent to group by similar proficiency in the target subject
    - Parse the response and return grouped students

    Args:
        students: List of student dicts with format:
            {"student_id": "...", "full_name": "...", "subject_scores": {"Math": 8.5, "Language": 7.0}}
        subject: Target subject used for grouping
        num_groups: Number of groups to create

    Returns:
        Dict with group_id as key and list of students as value
    """
    try:
        ai_result = await ai_grouping_by_subject(students, subject, num_groups)

        groups: Dict[str, List[Dict]] = {}
        student_id_to_data = {s["student_id"]: s for s in students}

        for group_id, group_info in ai_result.items():
            student_ids = group_info["students"]
            group_students = [student_id_to_data[sid] for sid in student_ids if sid in student_id_to_data]
            groups[group_id] = group_students
            logger.info(f"{group_id}: {len(group_students)} students")

        return groups
    except Exception as exc:
        logger.error(f"AI grouping failed: {exc}, falling back to even distribution")
        return distribute_evenly(students, num_groups)


AI_GROUPING_SYSTEM_PROMPT = """
You are an expert in grouping students by proficiency.

Task: Split students into homogeneous groups based on the target subject score.

Grouping rules:
1. Students in the same group should have similar proficiency in the target subject.
2. Do not mix very high and very low proficiency students in the same group.
3. Use the target subject score as the primary signal.
4. Use related subjects only when the target subject score is missing.
5. Balance group sizes (difference at most +/- 1 student).

Output:
- Return JSON only, no extra text.
"""

AI_GROUPING_USER_TEMPLATE = """
STUDENT LIST:
{students_text}

TARGET SUBJECT: {subject}

Create {num_groups} homogeneous groups based on the target subject score.

Guidance:
- Prefer the score for "{subject}" as the main signal.
- If a student does not have a score for "{subject}", use similar subjects: {similar_subjects}
- If no similar subjects exist, use the average score across all subjects.
- If only qualitative notes exist, use them as a weak signal:
  * "excellent" -> high
  * "good" -> upper mid
  * "average" -> mid
  * "needs support" -> low

For each group, return:
- level: advanced | high | medium | foundation
- characteristics: short description
- recommended_exercises: suitable practice type

Return JSON in this format:
{
  "group_1": {
    "students": ["student_id1", "student_id2"],
    "reasoning": "...",
    "level": "foundation",
    "characteristics": "...",
    "recommended_exercises": "..."
  }
}
"""


async def ai_grouping_by_subject(
    students: List[Dict],
    subject: str,
    num_groups: int,
) -> Dict[str, Dict]:
    """
    Use an AI agent to group students based on subject scores.
    """
    logger.info(
        f"AI grouping: {len(students)} students into {num_groups} homogeneous groups by {subject}"
    )

    student_descriptions = []
    for student in students:
        info_parts = [f"Name: {student['full_name']} (ID: {student['student_id']})"]

        subject_scores = student.get("subject_scores", {})
        if subject_scores:
            score_parts = []
            if subject in subject_scores and subject_scores[subject] is not None:
                score_parts.append(f"{subject}: {subject_scores[subject]} (target)")

            other_scores = [
                f"{subj}: {score}"
                for subj, score in subject_scores.items()
                if subj != subject and score is not None
            ]
            if other_scores:
                score_parts.extend(other_scores)

            if score_parts:
                info_parts.append(f"Scores: {', '.join(score_parts)}")

        if student.get("grade_level"):
            info_parts.append(f"Grade Level: {student['grade_level']}")
        if student.get("notes"):
            info_parts.append(f"Notes: {student['notes']}")

        student_descriptions.append(f"- {' | '.join(info_parts)}")

    students_text = "\n".join(student_descriptions)

    similar_subjects_map = {
        "Math": "Physics, Chemistry, CS",
        "Language": "History, Geography, Civics",
        "English": "Second Language, Literature",
        "Physics": "Math, Chemistry, Technology",
        "Chemistry": "Math, Physics, Biology",
        "Biology": "Chemistry, Geography",
        "History": "Geography, Language",
        "Geography": "History, Biology",
        "CS": "Math, Technology",
        "Technology": "CS, Physics, Chemistry",
    }

    similar_subjects = similar_subjects_map.get(subject, "other subjects")

    user_message = AI_GROUPING_USER_TEMPLATE.format(
        students_text=students_text,
        subject=subject,
        similar_subjects=similar_subjects,
        num_groups=num_groups,
    )

    try:
        agent_client = AgentClient(
            system_prompt=AI_GROUPING_SYSTEM_PROMPT, tools=[], model=model
        )
        agent = agent_client.create_agent()

        logger.info("Calling AI agent for grouping")
        result = await agent.run(user_message)

        response_text = str(result.output).strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        ai_groups = json.loads(response_text)

        final_groups: Dict[str, Dict] = {}
        student_id_to_data = {s["student_id"]: s for s in students}
        used_students = set()

        for group_id, group_info in ai_groups.items():
            student_ids = group_info["students"]
            valid_student_ids = [
                sid
                for sid in student_ids
                if sid in student_id_to_data and sid not in used_students
            ]
            used_students.update(valid_student_ids)

            if valid_student_ids:
                group_students = [student_id_to_data[sid] for sid in valid_student_ids]
                num_students = len(valid_student_ids)

                ai_level = group_info.get("level", "unknown")
                avg_score = 0.0
                if ai_level == "unknown":
                    scores = [
                        s.get("subject_scores", {}).get(subject, 0)
                        for s in group_students
                        if subject in s.get("subject_scores", {})
                    ]
                    qualitative_levels = []
                    for student in group_students:
                        level = str(student.get("grade_level", "")).lower()
                        if "excellent" in level:
                            qualitative_levels.append(9)
                        elif "good" in level:
                            qualitative_levels.append(7)
                        elif "average" in level:
                            qualitative_levels.append(5)
                        elif "needs support" in level:
                            qualitative_levels.append(3)

                    all_scores = [s for s in scores + qualitative_levels if s > 0]
                    if all_scores:
                        avg_score = round(sum(all_scores) / len(all_scores), 2)
                        if avg_score >= 8.0:
                            ai_level = "advanced"
                        elif avg_score >= 6.5:
                            ai_level = "high"
                        elif avg_score >= 5.0:
                            ai_level = "medium"
                        else:
                            ai_level = "foundation"
                    else:
                        ai_level = "unknown"

                final_groups[group_id] = {
                    "students": valid_student_ids,
                    "reasoning": group_info.get("reasoning", "No reasoning provided"),
                    "level": ai_level,
                    "characteristics": group_info.get(
                        "characteristics", "No characteristics provided"
                    ),
                    "recommended_exercises": group_info.get(
                        "recommended_exercises", "No recommendations provided"
                    ),
                    "profile": {
                        "num_students": num_students,
                        "avg_score": avg_score,
                        "min_score": 0,
                        "max_score": 0,
                        "score_range": "N/A",
                        "diversity": 0,
                        "level": ai_level,
                    },
                }
                logger.info(
                    f"{group_id}: {num_students} students, level: {ai_level}, reasoning: {group_info.get('reasoning', '')[:50]}..."
                )

        all_assigned = set()
        for group in final_groups.values():
            all_assigned.update(group["students"])

        remaining_students = [sid for sid in student_id_to_data.keys() if sid not in all_assigned]
        if remaining_students and final_groups:
            logger.info(f"Assigning {len(remaining_students)} remaining students evenly to groups")
            group_keys = list(final_groups.keys())
            for i, sid in enumerate(remaining_students):
                group_idx = i % len(group_keys)
                final_groups[group_keys[group_idx]]["students"].append(sid)

        logger.info(f"AI grouping completed: {len(final_groups)} groups created")
        return final_groups

    except Exception as exc:
        logger.error(f"AI grouping failed: {exc}")
        logger.info("Falling back to even distribution")
        return distribute_evenly_as_dict(students, num_groups)


def distribute_evenly(students: List[Dict], num_groups: int) -> Dict[str, List[Dict]]:
    """Distribute students evenly across groups when no scores are available."""
    groups = {f"group_{i+1}": [] for i in range(num_groups)}
    group_keys = list(groups.keys())

    for i, student in enumerate(students):
        group_idx = i % num_groups
        groups[group_keys[group_idx]].append(student)

    return groups


def distribute_evenly_as_dict(students: List[Dict], num_groups: int) -> Dict[str, Dict]:
    """Distribute students evenly and return in the expected dict format."""
    even_groups = distribute_evenly(students, num_groups)

    formatted_groups = {}
    for group_id, group_students in even_groups.items():
        formatted_groups[group_id] = {
            "students": [s["student_id"] for s in group_students],
            "reasoning": "Even distribution (no scores available)",
        }

    return formatted_groups
