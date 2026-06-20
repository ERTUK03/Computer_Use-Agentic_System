import logfire
import os
import re
from .engine_base import EngineBase
from ..Agents.State_Executor.state_executor import get_executor
from ..utils.message_parsing import parse_messages

logfire.configure()
logfire.instrument_pydantic_ai()

class Engine(EngineBase):
    def __init__(self):
        super().__init__()
        
    async def set_client(self, memories, client_id, server=None):
        self.client_id=client_id
        
        if server:
            await self.set_server(server)

    async def set_server(self, server):
        self.server = server
        self.executor = get_executor(self.server, self.hooks)

    async def execute(self, task):
        self.wrap_log = []
    
        result = await self.executor.run(task)
    
        exec_log = self.wrap_log[:]
        exec_stats = parse_messages(exec_log)
    
        exec_stats.pop("history", None)
        
        return result, exec_stats
