from pydantic import BaseModel, field_validator
from typing import List
from ..utils.load_model import load_full_model

class EvaluatorOutput(BaseModel):
    success: bool
    confidence: float
    score: int
    goal_completion_reason: str
    good: List[str]
    insights: List[str]
    tips: List[str]

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    @field_validator("score")
    @classmethod
    def score_range(cls, v):
        if not (1 <= v <= 10):
            raise ValueError("score must be between 1 and 10")
        return v

def get_evaluator(hooks=None):
    model_name = "evaluator"

    evaluator = load_full_model(
        model_name,
        output_type = EvaluatorOutput,
        capabilities = hooks
    )

    return evaluator