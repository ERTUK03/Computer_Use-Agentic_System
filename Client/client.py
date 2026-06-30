import aiohttp
import asyncio
import json

class Client:
    def __init__(self):
        self.session = None
        self.ws = None
        self.responses = asyncio.Queue()

    async def connect(self, host):
        try:
            self.session = aiohttp.ClientSession()
            self.ws = await self.session.ws_connect(host)
            asyncio.create_task(self.receive_messages())
            return "Connected"
        except Exception as e:
            return e

    async def receive_messages(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue

                await self.responses.put(data["msg_content"])

    async def identify_client(self, client_id):
        if self.ws:
            await self.ws.send_json({
                "msg_type": "IdentifyClient",
                "msg_content": client_id
            })

            return await self.responses.get()
        else:
            return "Not connected"

    async def set_server(self, server):
        if self.ws:
            await self.ws.send_json({
                "msg_type": "SetServer",
                "msg_content": server
            })
    
            return await self.responses.get()
        else:
            return "Not connected"
    

    async def send_task(self, task):
        if self.ws:
            await self.ws.send_json({
                "msg_type": "Task",
                "msg_content": task
            })
    
            return await self.responses.get()
        else:
            return "Not connected"
    
    async def close(self):
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        return "Closed"