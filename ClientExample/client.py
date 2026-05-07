import aiohttp, asyncio, json
from aiohttp import web

class Client:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.ws = None
        
    async def connect(self, host):
        self.ws = await self.session.ws_connect(host)
        print("Connection established")
        asyncio.create_task(self.receive_messages())

    async def receive_messages(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    print("Invalid JSON")
                    continue
                if data["msg_type"]=='Close':
                    await self.close()
                    break
                elif data["msg_type"]=="Task_response":
                    print(data["msg_content"]["result"])
                    print(data["msg_content"]["stats"])
                elif data["msg_type"]=="Error":
                    print(data["msg_content"])
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("WebSocket error")
                break

    async def send_message(self, message_type, message_content):
        message = {
            "msg_type": message_type,
            "msg_content": message_content
        }
        await self.ws.send_str(json.dumps(message))

    async def send_task(self, content):
        await self.send_message("Task", content)

    async def identify_client(self, client_id):
        await self.send_message("IdentifyClient", client_id)

    async def set_server(self, server):
        await self.send_message("SetServer", server)
        
    async def close(self):
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self.session:
            await self.session.close()
        print("Connection closed")

async def main():
    client_id="user_1"
    mcp_server='http://localhost:8000/mcp'
    server="http://localhost:8090/ws"
    client = Client()
    await client.connect(server)
    await asyncio.sleep(1)
    await client.identify_client(client_id)
    await client.set_server(mcp_server)
    await asyncio.sleep(1)
    await client.send_task("Open Youtube")
    await asyncio.sleep(30)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
