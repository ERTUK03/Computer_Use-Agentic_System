from .get_app_pid import get_app_pid
import time
from pywinauto import Application, Desktop
import subprocess

def _list_explorer_window_titles():
    titles = set()
    for w in Desktop(backend="uia").windows(class_name="CabinetWClass"):
        try:
            t = w.window_text().strip()
            if t:
                titles.add(t)
        except Exception:
            continue
    return titles


def _connect_explorer_folder_window(path: str | None, timeout: int = 15):
    before = _list_explorer_window_titles()
    
    if path:
        subprocess.Popen(["explorer.exe", f"/n,{path}"])
    else:
        subprocess.Popen(["explorer.exe", "/n"])

    new_title = None
    for _ in range(timeout):
        time.sleep(1)
        after = _list_explorer_window_titles()
        added = after - before
        if added:
            # If multiple new windows appeared, just take one -- ambiguous
            # but better than failing outright.
            new_title = next(iter(added))
            break

    if new_title is None:
        raise Exception(
            "Could not find a new File Explorer window"
            + (f" for path '{path}'" if path else "")
            + " after launching"
        )

    app = Application(backend="uia").connect(title=new_title, class_name="CabinetWClass", timeout=5)
    return app, app.top_window().wrapper_object()


def launch_and_connect(name: str):
    lname = name.strip().lower()
    if lname == "explorer" or lname.startswith("explorer:"):
        path = name.split(":", 1)[1] if ":" in name else None
        return _connect_explorer_folder_window(path)

    # Check if already running
    pid = get_app_pid(name)
    
    if not pid:
        result = subprocess.run(
            ["powershell", "-Command", f"Get-StartApps | Where-Object {{$_.Name -like '*{name}*'}}"],
            capture_output=True, encoding="utf-8", errors="replace"
        )
        lines = [l for l in result.stdout.strip().splitlines() if name.lower() in l.lower()]
        if not lines:
            raise Exception(f"App '{name}' not found")
        
        app_id = lines[0].split()[-1]
        subprocess.Popen(f"explorer.exe shell:AppsFolder\\{app_id}")
        
        for _ in range(10):
            time.sleep(1)
            pid = get_app_pid(name)
            if pid:
                break
        
        if not pid:
            try:   
                print(f"Connecting to {name}")
                app = Application(backend="uia").connect(best_match=name, timeout=10)
                return app, app.top_window().wrapper_object()
            except:
                raise Exception(f"Could not find {name} process after launching")
    
    print(f"Connecting to {name} (PID: {pid})")
    app = Application(backend="uia").connect(process=pid, timeout=10)
    return app, app.top_window().wrapper_object()