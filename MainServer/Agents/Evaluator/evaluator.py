from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai import Agent, RunContext, ModelRetry
from utils.prompt_loading import load_prompt
import os

def get_evaluator():
    model = OpenRouterModel(
        os.getenv("EVALUATOR_MODEL"),
        provider=OpenRouterProvider(api_key=os.getenv("PROVIDER_KEY"))
    )

    settings = OpenRouterModelSettings(
        openrouter_reasoning={
            'effort': os.getenv("REASONING"),
        }
    )
    
    evaluator = Agent(  
        model,
        name="evaluator",
        instructions=(load_prompt("evaluator")),
        model_settings=settings
    )

    @evaluator.output_validator
    async def validate_sql(ctx: RunContext, output: Output) -> Output:
        if isinstance(output, InvalidRequest):
            return output
        try:
            output_json = json.loads(output)
        except json.JSONDecodeError:
            raise ModelRetry('Response is not a valid JSON.')
        else:
            return output_json
    
    return evaluator