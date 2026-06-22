import os
import re
from ...utils.load_model import load_full_model

class GrounderAgent:
    def __init__(self, agent, reorder_image_first=False):
        self.agent = agent
        self.reorder_image_first = reorder_image_first

    def parse_boxes(self, answer: str, image_width: int, image_height: int) -> list[dict]:
        boxes = []
        for m in re.finditer(r"<box><(\d+)><(\d+)><(\d+)><(\d+)></box>", answer):
            x1, y1, x2, y2 = [int(g) for g in m.groups()]
            boxes.append({
                "x1": round(x1 / 1000 * image_width),
                "y1": round(y1 / 1000 * image_height),
                "x2": round(x2 / 1000 * image_width),
                "y2": round(y2 / 1000 * image_height),
            })
        return boxes

    async def run(self, messages, image_size=[1920,1080]):
        if self.reorder_image_first:
            images = [m for m in messages if not isinstance(m, str)]
            texts = [m for m in messages if isinstance(m, str)]
            messages = images + texts

        grounding_agent_result = await self.agent.run(messages)

        if self.reorder_image_first:
            boxes = self.parse_boxes(grounding_agent_result.output, image_size[0], image_size[1])
            return boxes

        content = re.sub(r"```json\s*|\s*```", "", grounding_agent_result.output.strip())
    
        return json.loads(content)

def get_grounder(hooks=None):
    model_name = "grounder"
    
    agent = load_full_model(
        model_name, 
        capabilities = hooks,
        include_prompt=False
    )

    return GrounderAgent(
        agent,
        reorder_image_first=os.getenv("GROUNDER_SOURCE") == "local"
    )