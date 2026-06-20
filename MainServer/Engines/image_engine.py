import logfire
import os
import re
from .engine_base import EngineBase
from ..Agents.Evaluator.evaluator import get_evaluator
from ..Agents.Executor.executor import get_executor
from ..utils.message_parsing import parse_messages
from ..utils.tips import MemoriesManager

logfire.configure()
logfire.instrument_pydantic_ai()

class Engine(EngineBase):
    def __init__(self):
        super().__init__()
        self.tip_num = int(os.getenv("TIP_NUM"))
        self.tip_threshold = float(os.getenv("TIP_THRESHOLD"))
        self.consolidate_threshold = float(os.getenv("CONSOLIDATE_THRESHOLD"))
        
    async def set_client(self, memories, client_id, server=None):
        self.client_id=client_id
        self.MemoriesManager = MemoriesManager(
            memories, 
            client_id, 
            self.tip_num, 
            self.tip_threshold, 
            self.consolidate_threshold
        )
        self.evaluator = get_evaluator(self.hooks)
        if server:
            await self.set_server(server)

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
