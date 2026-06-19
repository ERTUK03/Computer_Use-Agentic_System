from weaviate.classes.query import MetadataQuery
from weaviate.classes.tenants import Tenant
import random
from .embeddings import embed, cosine

class MemoriesManager():
    def __init__(self, memories, client_id, tip_num, tip_threshold, consolidate_threshold):
        existing = memories.tenants.get()
        
        if client_id not in [t for t in existing]:
            memories.tenants.create([Tenant(name=client_id)])
            
        self.user_memories = memories.with_tenant(tenant=client_id)
        self.tip_num = tip_num
        self.tip_threshold = tip_threshold
        self.consolidate_threshold = consolidate_threshold

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
    
    async def consolidate_tips(self, res_tips, tips, evaluation, task):
        for group_num in range(len(tips)):
            tip_num = 0
            while tip_num < len(tips[group_num]):
                tip_id = tips[group_num][tip_num]["id"]
                tip_data = res_tips[group_num]["tips"][tip_id]
    
                tip_data["times_used"] += 1
                if evaluation.output.success:
                    tip_data["successes"] += 1
    
                if tip_data["successes"] / tip_data["times_used"] < 0.3:
                    res_tips[group_num]["tips"].pop(tip_id)
                    tip_num -= 1
    
                tip_num += 1
        
        if not res_tips:
            self.user_memories.data.insert({
                "task": task,
                "tips": [{"tip": tip, "times_used": 1, "successes": 1} for tip in evaluation.output.tips]
            })
            return
    
        group_num = 0
        while group_num < len(res_tips):
            tip_num = 0
            unique_flag = [True] * len(evaluation.output.tips)
    
            while tip_num < len(res_tips[group_num]["tips"]):
                for i, new_tip in enumerate(evaluation.output.tips):
                    v1 = embed(new_tip)
                    v2 = embed(res_tips[group_num]["tips"][tip_num]["tip"])
                    if cosine(v1, v2) > self.consolidate_threshold:
                        unique_flag[i] = False
                if True not in unique_flag:
                    break
                tip_num += 1
    
            for i, is_unique in enumerate(unique_flag):
                if is_unique:
                    res_tips[group_num]["tips"].append({
                        "tip": evaluation.output.tips[i],
                        "times_used": 1,
                        "successes": 1
                    })
    
            self.user_memories.data.update(
                uuid=res_tips[group_num]["task_id"],
                properties={"tips": res_tips[group_num]["tips"]}
            )
    
            group_num += 1