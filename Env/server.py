import pyautogui
from dotenv import load_dotenv, dotenv_values, set_key
from mcp.server.fastmcp import FastMCP
from io import BytesIO
from functools import wraps
import time, os, base64, platform
from PIL import Image

load_dotenv()

server = FastMCP("Executor server")

def return_func(func):
    @wraps(func)
    async def inner(*args, **kwargs):
        print(f"Called function: {func.__name__} with arguments: {args}")
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
async def move(f_x: int, f_y: int, l_x: int, l_y: int) -> dict:
    """Move cursor to specified position.

    Args:
        f_x: x coordinate of top-left of the bounding box.
        f_y: y coordinate of top-left of the bounding box.
        l_x: x coordinate of bottom-right of the bounding box.
        l_y: y coordinate of bottom-right of the bounding box.
    """
    pyautogui.moveTo(f_x+l_x, f_y+l_y)

@server.tool()
@return_func
async def press_key(key: str) -> dict:
    """Allows to press a specified key.

    Args:
        key: a key to press('enter','esc')
    """
    pyautogui.press(key)

@server.tool()
@return_func
async def click(button: str) -> dict:
    """Performs a click of a mouse.

    Args:
        button: Specifies which button to click ("left", "middle" or "right")
    """
    pyautogui.click(button=button)

@server.tool()
@return_func
async def doubleClick() -> dict:
    """Performs a double left click.
    
    Args:
        None
    """
    pyautogui.doubleClick()

@server.tool()
@return_func
async def scroll(scroll_value: int) -> dict:
    """Allows for scrolling.
    
    Args:
        scroll_value: specifies how many clicks to scroll (e.g. -1000 or 1200) negative in down, positive is up.
    """
    time.sleep(1)
    pyautogui.scroll(scroll_value)

@server.tool()
@return_func
async def write(text: str) -> dict:
    """Allows for writing text.

    Args:
        text: text to write
    """
    pyautogui.write(text, interval=0.1)

@server.tool()
@return_func
async def write_secret(secret: str) -> dict:
    """Allows to automatically write a secret.

    Args:
        secret: name of secret to write
    """
    pyautogui.write(os.getenv(secret), interval=0.1)

ratio=2
og_size = pyautogui.size()
new_size = tuple([x//ratio for x in og_size])

def screenshot_linux():
    cursor = Image.open("cursor.png").convert("RGBA")

    cursor = cursor.resize((32,32))

    return cursor

def screenshot_windows():
    import win32gui
    import win32ui
    import win32con
    
    flags, hcursor, _ = win32gui.GetCursorInfo()

    icon_info = win32gui.GetIconInfo(hcursor)
    hbmColor = icon_info[4]
    hbmMask = icon_info[3]

    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    hbmp = win32ui.CreateBitmap()

    width = 40
    height = 40

    hbmp.CreateCompatibleBitmap(hdc, width, height)

    hdc_mem = hdc.CreateCompatibleDC()
    hdc_mem.SelectObject(hbmp)
    
    win32gui.DrawIconEx(
        hdc_mem.GetHandleOutput(),
        0, 0,
        hcursor,
        width, height,
        0, None,
        win32con.DI_NORMAL
    )

    bmpinfo = hbmp.GetInfo()
    bmpstr = hbmp.GetBitmapBits(True)

    img = Image.frombuffer(
        'RGBA',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRA', 0, 1
    )

    return img

@server.tool()
@return_func
async def screenshot() -> dict:
    system = platform.system()

    screenshot = pyautogui.screenshot()
    x, y = pyautogui.position()

    cursor = screenshot_windows() if system=="Windows" else screenshot_linux()

    screenshot.paste(cursor, (x, y), cursor)
        
    image = screenshot.resize(new_size)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    img_bytes = buffer.getvalue()

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    return {
        "image": img_b64,
        "format": "image/png",
        "size": list(new_size)
    }

@server.tool()
@return_func
async def get_all_secrets():
    """Returns a list of all known secrets.

    Args:
        None
    """
    env_dict = dotenv_values(".env")
    keys = list(env_dict.keys())
    return keys

@server.tool()
@return_func
async def add_secret(secret_name: str, secret_value: str) -> dict:
    """Adds a secret to a list of known secrets.
    
    Args:
        secret_name: name for the new secret
        secret_value: value of new secret
    """
    set_key(".env", secret_name, secret_value)

if __name__ == "__main__":
    server.run(transport="streamable-http")
