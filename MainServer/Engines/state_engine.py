import logfire
import os
import re
from .engine_base import EngineBase
from ..Agents.State_Executor.state_executor import get_executor
from ..utils.state_message_parsing import parse_messages
from ..Agents.Evaluator.evaluator import get_evaluator
from ..utils.trajectories import TrajectoriesManager
import json

logfire.configure()
logfire.instrument_pydantic_ai()

class Engine(EngineBase):
    def __init__(self):
        super().__init__()
        self.trajectory_threshold = float(os.getenv("TRAJECTORY_THRESHOLD"))
        self.trajectory_num = int(os.getenv("TRAJECTORY_NUM"))
        
    async def set_client(self, trajectories, client_id, server=None):
        self.client_id=client_id
        self.TrajectoriesManager = TrajectoriesManager(
            trajectories, 
            client_id,
            self.trajectory_num,
            self.trajectory_threshold
        )
        self.evaluator = get_evaluator(self.hooks)
        if server:
            await self.set_server(server)

    async def set_server(self, server):
        self.server = server
        self.executor = get_executor(self.server, self.hooks)

    async def execute(self, task):
        self.wrap_log = []
    
        res_trajectories = await self.TrajectoriesManager.get_trajectories(task)
    
        result = await self.executor.run([
            task,
            "Past trajectories: ",
            " ".join([json.dumps(res_trajectory) for res_trajectory in res_trajectories])
        ])
    
        exec_log = self.wrap_log[:]
        exec_stats = parse_messages(exec_log)

        trajectory = [
            (lambda text:
                text if len(text) <= 200 else text[:200] + "<TEXT_TRUNCATED>"
            )("\n".join(step["content"]))
            for step in exec_stats["history"]
        ]
    
        evaluation = await self.evaluator.run(trajectory)
    
        eval_log = self.wrap_log[len(exec_log):] 
        eval_stats = parse_messages(eval_log)
        
        await self.TrajectoriesManager.consolidate_trajectories(
            res_trajectories,
            trajectory,
            evaluation,
            task
        )
    
        for key in eval_stats:
            if key != "history":
                exec_stats[key] = exec_stats.get(key, 0) + eval_stats[key]

        exec_stats.pop("history", None)
    
        return result, exec_stats