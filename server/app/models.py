from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

Letter = Literal["A","B","C","D","E","F"]

class GradeRequestConfig(BaseModel):
    # Each question may have one or multiple correct answers
    correct_answers: Dict[int, Union[Letter, List[Letter]]]

class BoxResult(BaseModel):
    question: int
    selected: List[Letter] = Field(default_factory=list)
    is_correct: Optional[bool] = None
    confidences: Dict[Letter, float] = Field(default_factory=dict)

class GradeResult(BaseModel):
    total_questions: int
    correct_count: int
    score_percent: float
    per_question: List[BoxResult]
    debug: Optional[Dict] = None
