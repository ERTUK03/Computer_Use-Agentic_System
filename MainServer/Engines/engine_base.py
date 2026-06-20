from pydantic_ai import Agent, ModelRequestContext, RunContext
from pydantic_ai.capabilities import Hooks, WrapModelRequestHandler
from pydantic_ai.messages import ModelResponse
from abc import ABC, abstractmethod

class EngineBase(ABC):
    def __init__(self):
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

    @abstractmethod
    async def set_client(self, memories, client_id, server=None):
        pass

    @abstractmethod
    async def set_server(self, server):
        pass

    @abstractmethod
    async def execute(self, task):
        pass
    
    async def check_server(self):
        return await self.executor.check_server()
