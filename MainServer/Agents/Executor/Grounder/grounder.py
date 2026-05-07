from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai import Agent
import os

def get_grounder(hooks):
    model = OpenRouterModel(
        os.getenv("GROUNDER_MODEL"),
        provider=OpenRouterProvider(api_key=os.getenv("PROVIDER_KEY"))
    )
    
    grounder = Agent(  
        model,
        name="grounder", capabilities=[hooks]
    )
            
    return grounder