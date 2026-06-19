from pydantic_ai.messages import *
import pydantic_ai
import json

def append_history(stats, content, timestamp):
    stats["history"].append({
        "content": content,
        "timestamp": timestamp
    })

def parse_messages(result):
    stats = {
        "history":[],
        "combined_cost":0.,
        "input_tokens":0,
        "output_tokens":0,
        "cache_read_tokens":0,
        "cache_write_tokens":0
    }
    
    for mess in result:
        event=mess["event"]
        agent=mess["agent"]

        part=event.parts[0]
        
        if(isinstance(part, UserPromptPart)):
            if isinstance(part.content, str):
                content = [part.content]
            else:
                content = part.content
            
            result = [f"Agent {agent} received user prompt: "] + content
            
            append_history(stats,
                           result,
                           event.timestamp)

        elif(isinstance(part, ToolReturnPart)):
            if isinstance(part.content, list) or isinstance(part.content, dict):
                tool_content = [json.dumps(part.content)]
            else:
                tool_content = [part.content]

            append_history(stats,
                           [f"Tool {part.tool_name} returned to agent {agent}: "]+tool_content,
                           event.timestamp)

        if(isinstance(part, TextPart)):
            append_history(stats,
                           [f"Agent {agent} returned: {part.content}"],
                           event.timestamp)
        
        elif(isinstance(part, ToolCallPart)):
            append_history(stats,
                           [f"Agent {agent} called tool: {part.tool_name} with arguments: {part.args}"],
                           event.timestamp)
            
        if(isinstance(event, ModelResponse)):
            cost = (event.provider_details or {}).get("cost")
            if cost is not None:
                stats["combined_cost"] += cost
            stats["input_tokens"]+=event.usage.input_tokens
            stats["output_tokens"]+=event.usage.output_tokens
            stats["cache_read_tokens"]+=event.usage.cache_read_tokens
            stats["cache_write_tokens"]+=event.usage.cache_write_tokens
    return stats