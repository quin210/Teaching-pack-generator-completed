from pydantic import BaseModel
from typing import List, Optional

class TheoryQuestion(BaseModel):
    id: Optional[int] = None
    question: str
    answer: str

class GroupTheoryQuestionSet(BaseModel):
    group_name: str
    group_description: Optional[str] = None
    questions: List[TheoryQuestion]

# Wrapper for the AI response
class TheoryQuestionSet(BaseModel):
    groups: List[GroupTheoryQuestionSet]
