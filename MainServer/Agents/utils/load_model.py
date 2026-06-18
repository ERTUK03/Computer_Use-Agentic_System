import os
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openrouter import OpenRouterModelSettings

def load_model(model_name):
    model_source = os.getenv(f"{model_name}_SOURCE")
    model_url = os.getenv(f"{model_name}_MODEL")
    model_settings = os.getenv(f"{model_name}_SETTINGS")
    
    if model_source == "local":
        model = OpenAIModel(
            model_name="local",
            provider=OpenAIProvider(
                base_url=model_url,
                api_key="not-needed",
            )
        )
    elif model_source == "openrouter":
        model = OpenRouterModel(
            model_url,
            provider=OpenRouterProvider(api_key=os.getenv("PROVIDER_KEY"))
        )

    if model_settings == "True":
        settings = settings = OpenRouterModelSettings(
            openrouter_reasoning={
                'effort': os.getenv("REASONING")
            }
        )
        return model, settings
        
    return model