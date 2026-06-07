import gradio as gr
import asyncio
from client import Client
import json

client = None

async def connect_client(ws_url, client_id, mcp_server):
    global client

    if client:
        await client.close()

    client = Client()

    await client.connect(ws_url)
    await client.identify_client(client_id)
    await client.set_server(mcp_server)

    return "Connected"

async def run_task(task):
    global client

    if client is None:
        return "Not connected"

    await client.send_task(task)

    response = await client.wait_for_response()

    return json.dumps(response, indent=2)


with gr.Blocks() as demo:
    gr.Markdown("# WebSocket Client")

    with gr.Row():
        ws_url = gr.Textbox(
            value="URL",
            label="WebSocket URL"
        )

        client_id = gr.Textbox(
            value="USER",
            label="Client ID"
        )

    mcp_server = gr.Textbox(
        value="SERVER",
        label="MCP Server"
    )

    connect_btn = gr.Button("Connect")
    status = gr.Textbox(label="Status")

    connect_btn.click(
        fn=connect_client,
        inputs=[ws_url, client_id, mcp_server],
        outputs=status,
    )

    gr.Markdown("## Task")

    task = gr.Textbox(label="Task")
    run_btn = gr.Button("Run Task")
    output = gr.Code(label="Response", language="json")

    run_btn.click(
        fn=run_task,
        inputs=task,
        outputs=output,
    )

demo.launch()