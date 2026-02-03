from pydantic import BaseModel
from typing import Literal, List, Optional

class Flashcard(BaseModel):
    id: Optional[int] = None
    type: Literal["definition", "term", "principle", "purpose", "classification"]
    front: str
    back: str
    difficulty: Optional[Literal["easy", "medium", "hard", "advanced"]] = None

class FlashcardGroup(BaseModel):
    group_name: str
    proficiency_level: Optional[str] = None
    flashcards: List[Flashcard]

class FlashcardSet(BaseModel):
    groups: List[FlashcardGroup]
