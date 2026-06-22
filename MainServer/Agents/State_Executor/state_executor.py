from pydantic_ai import BinaryContent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from ..utils.load_model import load_full_model
import base64
from pydantic_ai.messages import BinaryContent

def decode_image(content: dict) -> BinaryContent:
    data = content["data"] + "=" * (4 - len(content["data"]) % 4)
    return BinaryContent(
        data=base64.urlsafe_b64decode(data),
        media_type=content["media_type"]
    )

async def process_tool_call(ctx, call_tool, name, args):
    result = await call_tool(name, args)
    
    if (
        isinstance(result, dict)
        and isinstance(result.get("content"), dict)
        and result["content"].get("kind") == "binary"
    ):
        return decode_image(result["content"])
    
    return result

class StateExecutor:
    def __init__(self, server, hooks):
        self.server = MCPServerStreamableHTTP(
            server,
            include_instructions=True,
            process_tool_call=process_tool_call
        )

        model_name = "state_executor"

        self.state_executor = load_full_model(
            model_name,
            toolsets=[self.server],
            capabilities=hooks,
            include_prompt=True
        )

    async def run(self, task):
        result = await self.state_executor.run(["Task: "]+task)

        return result

    async def check_server(self):
        try:
            async with self.server:
                return True
        except Exception:
            return False

def get_executor(server, hooks=None):
    return StateExecutor(server, hooks)