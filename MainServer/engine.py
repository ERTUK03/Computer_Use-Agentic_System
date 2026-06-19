import logfire
from pydantic_ai import Agent, ModelRequestContext, RunContext
from pydantic_ai.capabilities import Hooks, WrapModelRequestHandler
from pydantic_ai.messages import ModelResponse
import os
import re
from .Agents.Evaluator.evaluator import get_evaluator
from .Agents.Executor.executor import get_executor
from .utils.message_parsing import parse_messages
from .utils.tips import MemoriesManager

logfire.configure()
logfire.instrument_pydantic_ai()

class Engine:
    def __init__(self):
        self.tip_num = int(os.getenv("TIP_NUM"))
        self.tip_threshold = float(os.getenv("TIP_THRESHOLD"))
        self.consolidate_threshold = float(os.getenv("CONSOLIDATE_THRESHOLD"))
        self.server=None
        self.client_id=None
        
        self.hooks = Hooks()
    
        self.wrap_log: list = []

        @self.hooks.on.model_request
        async def log_request(
            ctx: RunContext[None], *, request_context: ModelRequestContext, handler: WrapModelRequestHandler
        ) -> ModelResponse:
            self.wrap_log.append({"event": request_context.messages[-1],
                                  "agent": ctx.agent.name})
            response = await handler(request_context)
            self.wrap_log.append({"event": response,
                                  "agent": ctx.agent.name})
            return response
        
    async def set_client(self, memories, client_id, server=None):
        self.client_id=client_id
        self.MemoriesManager = MemoriesManager(
            memories, 
            client_id, 
            self.tip_num, 
            self.tip_threshold, 
            self.consolidate_threshold
        )
        self.evaluator = get_evaluator()
        if server:
            self.server=server
            self.executor=get_executor(self.server, self.hooks)

    async def set_server(self, server):
        self.server = server
        self.executor = get_executor(self.server, self.hooks)

    async def execute(self, task):
        self.wrap_log = []
    
        res_tips, tips = await self.MemoriesManager.get_tips(task)
    
        result = await self.executor.run([
            task,
            "Tips: ",
            " ".join([tip["tip"] for tip_group in tips for tip in tip_group])
        ])
    
        exec_log = self.wrap_log[:]
        exec_stats = parse_messages(exec_log)
    
        evaluation = await self.evaluator.run(
            [f"Task: {task} \n"] + [mes for message in exec_stats["history"] for mes in message["content"]]
        )
    
        eval_log = self.wrap_log[len(exec_log):] 
        eval_stats = parse_messages(eval_log)
        
        await self.MemoriesManager.consolidate_tips(res_tips, tips, evaluation, task)
    
        for key in eval_stats:
            if key != "history":
                exec_stats[key] = exec_stats.get(key, 0) + eval_stats[key]
    
        exec_stats.pop("history", None)
    
        return result, exec_stats

    async def check_server(self):
        return await self.executor.check_server()
