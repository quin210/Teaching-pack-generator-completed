"""
Student Grouping Utilities
Helper functions for profiling and grouping students
"""
from typing import List, Dict, Optional
from statistics import mean
from models.teaching_pack_models import (
    SkillSet, StudentDiagnosticResult, GroupProfile, GroupingResult
)


def profile_groups_by_quartile(
    skill_set: SkillSet,
    diagnostic_results: List[StudentDiagnosticResult],
    num_groups: int = 4,
    student_scores: Optional[Dict[str, float]] = None
) -> GroupingResult:
    """
    Group students based on diagnostic results using quartile method
    
    Args:
        skill_set: Defined skills
        diagnostic_results: Diagnostic results for each student
        num_groups: Number of groups to create (default 4)
        student_scores: Previous test scores (optional)
    
    Returns:
        GroupingResult with groups and rationale
    """
    # Calculate overall mastery for each student
    students_mastery = []
    for result in diagnostic_results:
        overall = mean(result.skill_mastery.values())
        students_mastery.append({
            'student_id': result.student_id,
            'student_name': result.student_name,
            'overall_mastery': overall,
            'skill_mastery': result.skill_mastery,
            'misconceptions': result.misconceptions,
            'score': student_scores.get(result.student_name, None) if student_scores else None
        })
    
    # Sort by overall mastery
    students_mastery.sort(key=lambda x: x['overall_mastery'])
    
    # Split into groups (quartile-based)
    group_size = len(students_mastery) // num_groups
    groups = []
    
    for i in range(num_groups):
        start_idx = i * group_size
        end_idx = start_idx + group_size if i < num_groups - 1 else len(students_mastery)
        group_students = students_mastery[start_idx:end_idx]
        
        # Calculate group statistics
        avg_mastery = {}
        for skill in skill_set.skills:
            skill_values = [s['skill_mastery'].get(skill.skill_id, 0.0) for s in group_students]
            avg_mastery[skill.skill_id] = mean(skill_values)
        
        # Collect common misconceptions
        all_misconceptions = []
        for s in group_students:
            all_misconceptions.extend(s['misconceptions'])
        
        # Determine mastery level
        overall_avg = mean(avg_mastery.values())
        if overall_avg < 0.4:
            mastery_level = "low"
            learning_pace = "slow"
        elif overall_avg < 0.6:
            mastery_level = "medium"
            learning_pace = "moderate"
        elif overall_avg < 0.8:
            mastery_level = "high"
            learning_pace = "moderate"
        else:
            mastery_level = "advanced"
            learning_pace = "fast"
        
        group = GroupProfile(
            group_id=f"group_{i+1}",
            group_name=f"Group {i+1}",  # Will be labeled by agent
            description="",  # Will be added by labeler agent
            mastery_level=mastery_level,
            skill_mastery=avg_mastery,
            common_misconceptions=list(set(all_misconceptions))[:5],  # Top 5 unique
            learning_pace=learning_pace,
            students=[s['student_id'] for s in group_students],
            recommended_activities=[]  # Will be added by labeler agent
        )
        groups.append(group)
    
    return GroupingResult(
        groups=groups,
        rationale=f"Students grouped into {num_groups} levels based on diagnostic mastery scores using quartile method",
        total_students=len(students_mastery)
    )
