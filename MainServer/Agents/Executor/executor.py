from pydantic_ai import Agent, Tool, ToolOutput, BinaryContent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from .Planner.planner import get_planner
from .Grounder.grounder import get_grounder
import re, time
from ..utils.load_model import load_full_model

class Executor:
    def __init__(self, server, hooks):
        self.server = MCPServerStreamableHTTP(server, include_instructions=True)

        model_name = "executor"

        filtered_server = self.server.filtered(lambda ctx, tool_def: tool_def.name not in ["screenshot", "screenshot_size"])
        
        self.planner = get_planner(hooks)
        self.grounder = get_grounder(hooks)

        self.executor = load_full_model(
            model_name,
            capabilities=hooks,
            toolsets=[filtered_server],
            tools=[
                Tool(self.get_coordinates, takes_ctx=False),
                Tool(self.get_plan, takes_ctx=False),
                Tool(self.wait, takes_ctx=False),
                Tool(self.get_screenshot, takes_ctx=False)
            ]
        )

    async def get_screenshot(self) -> str:
        """Returns a screenshot of the environment"""
        ret_image = await self.server.direct_call_tool(name="screenshot", args={})
        
        image = ret_image["content"]["image"]
        image_type = ret_image["content"]["format"]

        return BinaryContent(data=image, media_type=image_type)

    async def get_screenshot_size(self):
        ret_size = await self.server.direct_call_tool(name="screenshot_size", args={})
        
        image_size = ret_size["content"]

        return image_size

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
        screenshot = await self.get_screenshot()
        img_size = await self.get_screenshot_size()

        grounding_agent_result = await self.grounder.run([
                f"Find {element} in the image and return only its location in the form of coordinates of a bounding box.",
                screenshot
            ], img_size)
    
        return grounding_agent_result

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