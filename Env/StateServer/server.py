from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from io import BytesIO
from functools import wraps
import asyncio
import time
import weakref
from PIL import Image
import io
from typing import Literal, Optional
from pydantic_ai import BinaryContent
import dictdiffer
from .utils import launch_and_connect
from .utils import extract_live_ui_tree
import json

load_dotenv()

server = FastMCP("Executor server")

class ClientState:
    __slots__ = ("app", "dlg", "live_tree", "aliases")

    def __init__(self):
        self.app = None
        self.dlg = None
        self.live_tree = None
        self.aliases = None


_client_states: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def get_state(ctx: Context) -> ClientState:
    """Fetch (or lazily create) the ClientState for the calling client's session."""
    session = ctx.session
    state = _client_states.get(session)
    if state is None:
        state = ClientState()
        _client_states[session] = state
    return state


def return_func(func):
    @wraps(func)
    async def inner(*args, **kwargs):
        # Don't log ctx in the call log -- it's noisy and not JSON-serializable.
        log_kwargs = {k: v for k, v in kwargs.items() if k != "ctx"}
        print(f"Called function: {func.__name__} with arguments: {log_kwargs}")
        result = {"status": "OK"}
        try:
            output = await func(*args, **kwargs)
            if output is not None:
                result["content"] = output
        except Exception as e:
            result["status"] = "Failed"
            result["error"] = str(e)
        return result
    return inner


@server.tool()
@return_func
async def launch_app(app_name: str, ctx: Context):
    """
    Launches app specified by 'app_name' parameter and returns its current state.
    """
    state = get_state(ctx)

    def _do_launch():
        if state.dlg:
            try:
                win = state.dlg
                win.close()
            except RuntimeError:
                pass

        app, dlg = launch_and_connect(app_name)
        app.top_window().wait("exists visible ready", timeout=20)

        live_tree, aliases = extract_live_ui_tree(dlg)
        time.sleep(1)
        live_tree, aliases = extract_live_ui_tree(dlg)
        
        return app, dlg, live_tree, aliases
    
    state.app, state.dlg, state.live_tree, state.aliases = await asyncio.to_thread(_do_launch)

    return state.live_tree


@server.tool()
@return_func
async def take_action(
    action: Literal[
        "click_input",
        "capture_as_image",
        "double_click",
        "scroll",
        "input_text",
    ],
    element_title: str,
    element_type: str,
    ctx: Context,
    index: int = 0,
    text: Optional[str] = None,
    scroll_amount: int = 0,
):
    """
    Interact with UI elements. capture_as_image returns an image of a specified element.

    Supported actions:
    - click_input
    - double_click
    - capture_as_image
    - scroll
    - input_text
    """
    state = get_state(ctx)

    def _do_action():
        nonlocal element_title
        try:
            if element_title in state.aliases:
                element_title = state.aliases[element_title]

            target = state.app.top_window().child_window(
                title=element_title,
                control_type=element_type,
                found_index=index
            )

            # Ensure control exists
            target.wait("exists ready", timeout=5)

            # --- CLICK ---
            if action == "click_input":
                target.click_input()
                return "Success"

            # --- DOUBLE CLICK ---
            elif action == "double_click":
                target.double_click_input()
                return "Success"

            # --- CAPTURE IMAGE ---
            elif action == "capture_as_image":
                result = target.capture_as_image()

                if isinstance(result, Image.Image):
                    result = result.resize(
                        (result.size[0] // 2, result.size[1] // 2)
                    )

                    buf = io.BytesIO()
                    result.save(buf, format="PNG")

                    return BinaryContent(
                        data=buf.getvalue(),
                        media_type="image/png"
                    )

                return "Capture failed"

            # --- SCROLL ---
            elif action == "scroll":
                target.set_focus()

                steps = abs(scroll_amount)
                key = "{PGDN}" if scroll_amount < 0 else "{PGUP}"

                for _ in range(steps):
                    target.type_keys(key)

                return "Success"

            # --- INPUT TEXT ---
            elif action == "input_text":
                if text is None:
                    return "text parameter required"

                target.set_focus()

                try:
                    # Best for Edit controls
                    target.set_edit_text(text)
                except Exception:
                    # Fallback for generic controls
                    target.type_keys(text, with_spaces=True)

                return "Success"

            else:
                return f"Unsupported action: {action}"

        except Exception as e:
            return str(e)
            
    return await asyncio.to_thread(_do_action)


@server.tool()
@return_func
async def check_state(ctx: Context):
    """
    Use for full state of the environment.
    """
    state = get_state(ctx)
    state.live_tree, state.aliases = await asyncio.to_thread(extract_live_ui_tree, state.dlg)
    return state.live_tree


@server.tool()
@return_func
async def check_partial_state(ctx: Context):
    """
    Use to check changes in environment. Prefer over full state.
    """
    state = get_state(ctx)
    new_live_tree, new_aliases = await asyncio.to_thread(extract_live_ui_tree, state.dlg)
    state.aliases = new_aliases
    diff = list(dictdiffer.diff(state.live_tree, new_live_tree))
    state.live_tree = new_live_tree

    if len(json.dumps(diff, ensure_ascii=False)) >= len(json.dumps(state.live_tree, ensure_ascii=False)):
        return state.live_tree
    else:
        return diff

if __name__ == "__main__":
    server.run(transport="streamable-http")