import logfire
from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings
from pydantic_ai import Agent, ModelRequestContext, RunContext
from pydantic_ai.capabilities import Hooks, WrapModelRequestHandler
from pydantic_ai.messages import ModelResponse
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai import Tool
from weaviate.classes.query import MetadataQuery
import os
import random
import re
import json
from Agents.Evaluator.evaluator import get_evaluator
from Agents.Executor.executor import get_executor
from utils.message_parsing import parse_messages
from utils.embeddings import embed, cosine
from pydantic_ai.capabilities import Hooks, WrapModelRequestHandler

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
        self.user_memories = memories.with_tenant(tenant=self.client_id)
        self.evaluator = get_evaluator()
        if server:
            self.server=server
            self.executor=get_executor(self.server, self.hooks)

    async def set_server(self, server):
        self.server=server
        self.executor = get_executor(self.server, self.hooks)

    async def get_tips(self, task):
        response = self.user_memories.query.near_text(
            query=task,
            limit=self.tip_num,
            target_vector="task",
            distance=self.tip_threshold,
            return_metadata=MetadataQuery(distance=True)
        )

        res_tips=[]
        tips=[]
        
        for o in response.objects:
            res_tips.append({"task_id": o.uuid.hex,"tips":o.properties["tips"]})
            tip_to_add=[]
            for i, tip in enumerate(o.properties["tips"]):
                if (random.uniform(0,1)<=tip["successes"]/tip["times_used"]):
                    tip_to_add.append({"id":i, "tip":tip["tip"]})
            tips.append(tip_to_add)

        return res_tips, tips

    async def summarize_tips(self, res_tips, tips, evaluation_json):
        for group_num in range(len(tips)):
            tip_num=0
            while tip_num<len(tips[group_num]):
                res_tips[group_num]["tips"][tips[group_num][tip_num]["id"]]["times_used"]+=1
                if evaluation_json["success"]:
                     res_tips[group_num]["tips"][tips[group_num][tip_num]["id"]]["successes"]+=1
                if res_tips[group_num]["tips"][tips[group_num][tip_num]["id"]]["successes"]/res_tips[group_num]["tips"][tips[group_num][tip_num]["id"]]["times_used"]<0.3:
                    res_tips[group_num]["tips"].pop(tips[group_num][tip_num]["id"])
                    tip_num-=1
                
                tip_num+=1

    async def consolidate_tips(self, res_tips, evaluation_json, task):
        if not res_tips:
            self.user_memories.data.insert({
                "task": task,
                "tips": [{"tip": tip,"times_used":1,"successes":1} for tip in evaluation_json["tips"]]
            })
            break
        
        group_num=0
        while group_num<len(res_tips):
            tip_num=0
            unique_flag=[]
            for new_tip in evaluation_json["tips"]:
                unique_flag.append(True)
            while tip_num<len(res_tips[group_num]["tips"]):
                for i, new_tip in enumerate(evaluation_json["tips"]):
                    v1 = embed(new_tip)
                    v2 = embed(res_tips[group_num]["tips"][tip_num]["tip"])
                    if(cosine(v1,v2)>self.consolidate_threshold):
                        unique_flag[i]=False
                if True not in unique_flag:
                    break
                tip_num+=1
            for i in range(len(unique_flag)):
                if(unique_flag[i]):
                    res_tips[group_num].append(evaluation_json["tips"][i])
        
            self.user_memories.data.update(
                uuid=res_tips[group_num]["task_id"],
                properties={"tips": res_tips[group_num]["tips"]}
            )
    
            group_num+=1

    async def execute(self, task):
        self.wrap_log=[]
        
        res_tips, tips = await self.get_tips(task)
        
        result = await self.executor.run([
            task,
            "Tips: ",
            " ".join([tip["tip"] for tip_group in tips for tip in tip_group])
        ])
        
        exec_stats = parse_messages(self.wrap_log)

        evaluation_json = await self.evaluator.run(
            [f"Task: {task} \n"]+[mes for message in exec_stats["history"] for mes in message["content"]]
        )

        eval_stats = parse_messages(self.wrap_log[len(exec_stats):])        
        
        await self.summarize_tips(res_tips, tips, evaluation_json)
        await self.consolidate_tips(res_tips, evaluation_json, task)

        for element in eval_stats:
            exec_stats[element]+=eval_stats[element]
            
        exec_stats.pop("history", None)
        
        return result, exec_stats

    async def check_server(self):
        return await self.executor.check_server()
