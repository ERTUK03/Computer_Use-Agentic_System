import os
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic import BaseModel, field_validator
from typing import List
from ...utils.prompt_loading import load_prompt
from ..utils.load_model import load_model

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
    model, settings = load_model("EVALUATOR")
    
    evaluator = Agent(
        model,
        name="evaluator",
        output_type=EvaluatorOutput,
        instructions=load_prompt("evaluator"),
        model_settings=settings,
        capabilities=[hooks] if hooks is not None else []
    )

    return evaluator