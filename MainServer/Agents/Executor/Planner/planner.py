from pydantic_ai import Agent
from ....utils.prompt_loading import load_prompt
from ...utils.load_model import load_model

def get_planner(hooks=None):
    model, settings = load_model("Planner")
    
    planner = Agent(  
        model,
        name="planner",
        instructions=(load_prompt("planner")),
        model_settings=settings, capabilities=[hooks] if hooks is not None else []
    )
    return planner