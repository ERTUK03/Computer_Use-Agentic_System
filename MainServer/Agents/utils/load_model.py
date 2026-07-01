import os
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openrouter import OpenRouterModelSettings
from .prompt_loading import load_prompt
from pydantic_ai import Agent, Tool, ToolOutput, BinaryContent
from pydantic_ai.mcp import MCPServerStreamableHTTP

def load_model(model_name, include_prompt=True):
    result = {}
    
    upper_model_name = model_name.upper()
    
    model_source = os.getenv(f"{upper_model_name}_SOURCE")
    model_url = os.getenv(f"{upper_model_name}_MODEL")
    model_settings = os.getenv(f"{upper_model_name}_SETTINGS")

    model = None
    settings = None
    prompt = None
    
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

    if include_prompt:
        prompt = load_prompt(model_name)
        
    return model, settings, prompt

def load_full_model(
    model_name, 
    output_type = str, 
    capabilities = None, 
    tools = (),
    toolsets = None, 
    include_prompt=True
):
    model, settings, prompt = load_model(model_name, include_prompt)
    
    agent = Agent(
        model,
        name=model_name,
        output_type=output_type,
        instructions=prompt,
        model_settings=settings,
        capabilities=capabilities,
        tools = tools,
        toolsets = toolsets
    )

    return agent