import gradio as gr
import asyncio
from .client import Client
import json

client = Client()

with gr.Blocks() as demo:
    gr.Markdown("# WebSocket Client")

    with gr.Row(equal_height=True):
        ws_url = gr.Textbox(
            value="http://localhost:8090/ws",
            label="WebSocket URL"
        )

        connect_btn = gr.Button("Connect")
        connect_status = gr.Textbox(label="connect_status")

    with gr.Row(equal_height=True):
        client_id = gr.Textbox(
            value="user_1",
            label="Client ID"
        )

        identify_client_btn = gr.Button("Identify Client")
        identify_client_status = gr.Textbox(label="identify_client_status")
        
    with gr.Row(equal_height=True):
        mcp_server = gr.Textbox(
            value="http://localhost:8000/mcp",
            label="MCP Server"
        )

        set_server_btn = gr.Button("Set Server")
        set_server_status = gr.Textbox(label="set_server_status")

    with gr.Row(equal_height=True):
        close_btn = gr.Button("Close")
        close_status = gr.Textbox(label="close_status")


    connect_btn.click(
        fn=client.connect,
        inputs=[ws_url],
        outputs=connect_status,
    )

    identify_client_btn.click(
        fn=client.identify_client,
        inputs=[client_id],
        outputs=identify_client_status,
    )

    set_server_btn.click(
        fn=client.set_server,
        inputs=[mcp_server],
        outputs=set_server_status,
    )

    close_btn.click(
        fn=client.close,
        inputs=[],
        outputs=close_status,
    )

    gr.Markdown("## Task")

    task = gr.Textbox(label="Task")
    run_btn = gr.Button("Run Task")
    output = gr.JSON(label="Response")

    run_btn.click(
        fn=client.send_task,
        inputs=task,
        outputs=output,
    )

demo.launch()