import aiohttp
import asyncio
import json
import aiosqlite
from datetime import datetime

class Client:
    def __init__(self, logging=False):
        self.logging = logging
        self.session = None
        self.ws = None
        self.responses = asyncio.Queue()
        self.conn = None

    async def init_db(self):
        if not self.logging or self.conn:
            return
    
        self.conn = await aiosqlite.connect("logs.db")
    
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                dict1 TEXT,
                dict2 TEXT
            )
        """)
    
        await self.conn.commit()
    
    async def save_run(self, dict1, dict2):
        await self.conn.execute("""
            INSERT INTO runs (timestamp, dict1, dict2)
            VALUES (?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            json.dumps(dict1),
            json.dumps(dict2)
        ))
    
        await self.conn.commit()

    async def connect(self, host):
        try:
            if self.logging:
                await self.init_db()
    
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

                content = data.get("msg_content", {})

                if isinstance(content, dict):  
                    result = content.get("result")
                    stats = content.get("stats")
                    history = content.get("history")
                    if self.logging:
                        await self.save_run(stats, history)
                    await self.responses.put((result, stats, history))
                else:
                    await self.responses.put(content)

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
        if self.conn:
            await self.conn.close()
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        return "Closed"