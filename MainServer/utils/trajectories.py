from weaviate.classes.query import MetadataQuery
from weaviate.classes.tenants import Tenant
import random
from .embeddings import embed, cosine

class TrajectoriesManager():
    def __init__(self, trajectories, client_id, trajectory_num, trajectory_threshold):
        existing = trajectories.tenants.get()
        
        if client_id not in [t for t in existing]:
            trajectories.tenants.create([Tenant(name=client_id)])

        self.trajectory_num = trajectory_num
        self.user_trajectories = trajectories.with_tenant(tenant=client_id)
        self.trajectory_threshold = trajectory_threshold

    async def get_trajectories(self, task):
        response = self.user_trajectories.query.near_text(
            query=task,
            limit=self.trajectory_num,
            target_vector="task",
            distance=self.trajectory_threshold,
            return_metadata=MetadataQuery(distance=True)
        )
        
        res_trajectories=[]
        
        for o in response.objects:
            res_trajectories.append({"task": o.properties["task"],"trajectory":o.properties["trajectory"]})
    
        return res_trajectories
    
    async def consolidate_trajectories(self, res_trajectories, trajectory, evaluation, task):   
        if not res_trajectories and evaluation.output.success:
            self.user_trajectories.data.insert({
                "task": task,
                "trajectory": trajectory
            })
            return