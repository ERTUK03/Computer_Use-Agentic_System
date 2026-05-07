from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings
from pydantic_ai.providers.openrouter import OpenRouterProvider
import os
from pydantic_ai import Agent
from utils.prompt_loading import load_prompt

def get_planner(hooks):
    model = OpenRouterModel(
        os.getenv("PLANNER_MODEL"),
        provider=OpenRouterProvider(api_key=os.getenv("PROVIDER_KEY"))
    )

    settings = OpenRouterModelSettings(
        openrouter_reasoning={
            'effort': os.getenv("REASONING"),
        }
    )
    
    planner = Agent(  
        model,
        name="planner",
        instructions=(load_prompt("planner")),
        model_settings=settings, capabilities=[hooks]
    )
    return planner