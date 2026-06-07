from pydantic_ai import Agent, ModelRequestContext, RunContext, Tool, ToolOutput, BinaryContent
from pydantic_ai.messages import ModelResponse
from pydantic_ai.mcp import MCPServerStreamableHTTP
from Agents.Executor.Planner.planner import get_planner
from Agents.Executor.Grounder.grounder import get_grounder
from utils.prompt_loading import load_prompt
import os, re, json, time
from Agents.utils.load_model import load_model

class Executor:
    def __init__(self, server, hooks):
        self.server = MCPServerStreamableHTTP(server, include_instructions=True)
        
        executor_model, settings = load_model("EXECUTOR")

        filtered_server = self.server.filtered(lambda ctx, tool_def: tool_def.name!="screenshot")
        
        self.planner = get_planner(hooks)
        self.grounder = get_grounder(hooks)

        self.executor = Agent(  
            executor_model,
            name="executor",
            instructions=(load_prompt("executor")),
            toolsets=[filtered_server],
            tools=[
                Tool(self.get_coordinates, takes_ctx=False),
                Tool(self.get_plan, takes_ctx=False),
                Tool(self.wait, takes_ctx=False),
                Tool(self.get_screenshot, takes_ctx=False)
            ],
            model_settings=settings,
            output_type=[ToolOutput(self.end_conversation, name='end_conversation')],
            capabilities=[hooks] if hooks is not None else []
        )

    async def get_screenshot(self) -> str:
        """Returns a screenshot of the environment"""
        ret_image = await self.server.direct_call_tool(name="screenshot", args={})
        
        image = ret_image["content"]["image"]
        image_type = ret_image["content"]["format"]
        image_size = ret_image["content"]["size"]

        return BinaryContent(data=image, media_type=image_type)

    async def get_screenshot_size(self) -> str:
        ret_image = await self.server.direct_call_tool(name="screenshot", args={})
        
        image = ret_image["content"]["image"]
        image_type = ret_image["content"]["format"]
        image_size = ret_image["content"]["size"]

        return BinaryContent(data=image, media_type=image_type), image_size

    async def get_plan(self, task: str):
        """Returns a step-by-step plan of completing a task specified by 'task' argument"""
        screenshot = await self.get_screenshot()
        generated_plan = await self.planner.run([task,screenshot])
    
        return generated_plan.output

    async def get_coordinates(self, element: str) -> str:
        """Returns bounding boxes that contain elements in environment.
    
        Args:
            element: specifies what element to return bounding boxes for.
        """
        screenshot, img_size = await self.get_screenshot_size()

        grounding_agent_result = await self.grounder.run([
                f"Find {element} in the image and return only its location in the form of coordinates of a bounding box.",
                screenshot
            ], img_size)
    
        return grounding_agent_result

    async def end_conversation(self, output: str) -> str:
        """Ends conversation when task is completed"""
        return output

    async def wait(self) -> str:
        """A small break to allow environment to load"""
        time.sleep(2)
        return {
            "status": "OK"
        }

    async def run(self, task):
        screenshot = await self.get_screenshot()
        
        result = await self.executor.run(task+[screenshot])

        return result

    async def check_server(self):
        try:
            async with self.server:
                return True
        except Exception:
            return False

def get_executor(server, hooks=None):
    return Executor(server, hooks)