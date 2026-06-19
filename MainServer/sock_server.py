from weaviate.classes.config import Configure
import weaviate.classes as wvc
import weaviate
from aiohttp import web
import aiohttp
from dotenv import load_dotenv
from pathlib import Path
import os, re, json, asyncio
import importlib
import aiosqlite

BASE_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
env_path = BASE_DIR / "config.env"

load_dotenv(env_path)

server_type = os.getenv("SERVER_TYPE")

module = importlib.import_module(
    f".{server_type}_engine",
    package=__package__
)

vdb_client = weaviate.connect_to_local()

if not vdb_client.collections.exists("Memories"):
    memories = vdb_client.collections.create(
        "Memories",
        vector_config=Configure.Vectors.text2vec_ollama( 
            api_endpoint=os.getenv("API_ENDPOINT"), 
            model=os.getenv("EMBEDDING_MODEL"),
            name="task",
            source_properties=["task"],
        ),
        multi_tenancy_config=Configure.multi_tenancy(
            enabled=True,
            auto_tenant_creation=True
        )
    )

else:
    memories = vdb_client.collections.use("Memories")

connections = []

class WSConnection:
    def __init__(self, request):
        self.request = request
        self.ws = web.WebSocketResponse()
        self.client_id=None
        self.server=None

        self.handlers = {
            "IdentifyClient": self.identify_client,
            "SetServer": self.set_server,
            "Task": self.handle_task,
            "Close": self.close
        }
        
    async def handle(self):
        await self.ws.prepare(self.request)
        print('websocket connection opened')
        
        self.engine = module.Engine()
        
        connections.append(self)

        await self.receive_messages()
        return self.ws

    async def identify_client(self, data):
        self.client_id=data["msg_content"]
        res = await self.request.app["db"].execute(
            "SELECT server_address FROM routing WHERE client_id=?",
            (self.client_id,)
        )
        server = await res.fetchone()
        if server:
            self.server=server[0]
        await self.engine.set_client(memories, self.client_id, self.server)

    async def set_server(self, data):
        self.server=data["msg_content"]
        res = await self.request.app["db"].execute(
            "SELECT server_address FROM routing where client_id=?",
            (self.client_id,)
        )
        server = await res.fetchone()
        if server:
            await self.request.app["db"].execute(
                "UPDATE routing SET server_address=? WHERE client_id=?",
                (self.server,self.client_id)
            )
        else:
            await self.request.app["db"].execute(
                "INSERT INTO routing VALUES(?, ?)",
                (self.client_id, self.server)
            )
        await self.request.app["db"].commit()
        await self.engine.set_server(self.server)
    
    async def handle_task(self, data):
        if not self.client_id:
            await self.send_error("No client id")
        elif not self.server:
            await self.send_error("No server specified")
        else:
            if await self.engine.check_server():
                result, stats = await self.engine.execute(data["msg_content"])
                await self.respond({"result":result.output, "stats":stats})
            else:
                await self.send_error("No server connection")

    async def receive_messages(self):
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        await self.send_error("Invalid JSON")
                        continue
                    handler = self.handlers.get(data["msg_type"])
                    if handler:
                        await handler(data)
                    else:
                        await self.send_error("Unknown message type")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print("WebSocket error")
                    break
        finally:
            if self in connections:
                connections.remove(self)
            print('websocket connection closed')

    async def close(self, data=None):
        if self.ws and not self.ws.closed:
            await self.ws.close()
        print("Connection closed")

    async def send_message(self, message_type, message_content):
        message = {
            "msg_type": message_type,
            "msg_content": message_content
        }
        await self.ws.send_str(json.dumps(message))

    async def respond(self, response):
        await self.send_message("Task_response", response)

    async def send_error(self, error):
        await self.send_message("Error", error)
        
async def websocket_handler(request):
    connection = WSConnection(request)
    return await connection.handle()

async def startup(app):
    app["db"] = await aiosqlite.connect(os.getenv("ROUTING_DB"))

    await app["db"].execute("""
        CREATE TABLE IF NOT EXISTS routing (
            client_id TEXT PRIMARY KEY,
            server_address TEXT
        )
    """)
    
    await app["db"].commit()

async def cleanup(app):
    vdb_client.close()
    await app["db"].close()

app = web.Application()
app.on_startup.append(startup)
app.on_cleanup.append(cleanup)
app.add_routes([web.get('/ws', websocket_handler)])

web.run_app(app, port=int(os.getenv("PORT")))
