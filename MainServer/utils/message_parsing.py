from pydantic_ai.messages import *
from pydantic_ai import BinaryContent, ImageUrl, AudioUrl, DocumentUrl
import pydantic_ai
import json

_VALID_CONTENT_TYPES = (str, BinaryContent, ImageUrl, AudioUrl, DocumentUrl)

def _sanitize_content_item(item):
    """Ensure every content item is either a plain string or a type
    pydantic_ai's model layer recognizes. Anything else (dicts, numbers,
    bounding boxes, etc.) gets stringified so it can't blow up later."""
    if isinstance(item, _VALID_CONTENT_TYPES):
        return item
    return json.dumps(item, ensure_ascii=False)


def append_history(stats, content, timestamp):
    stats["history"].append({
        "content": content,
        "timestamp": timestamp.isoformat()
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
        
        for part in event.parts:
            
            if(isinstance(part, UserPromptPart)):
                if isinstance(part.content, str):
                    content = [part.content]
                else:
                    content = [_sanitize_content_item(item) for item in part.content]
                
                result = [f"Agent {agent} received user prompt: "] + content
                
                append_history(stats,
                               result,
                               event.timestamp)
    
            elif(isinstance(part, ToolReturnPart)):
                if isinstance(part.content, list):
                    tool_content = [_sanitize_content_item(item) for item in part.content]
                elif isinstance(part.content, dict):
                    tool_content = [json.dumps(part.content, ensure_ascii=False)]
                else:
                    tool_content = [_sanitize_content_item(part.content)]
    
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