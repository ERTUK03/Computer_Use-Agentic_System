from .get_app_pid import get_app_pid
import time
from pywinauto import Application
import subprocess

def launch_and_connect(name: str):
    # Check if already running
    pid = get_app_pid(name)
    
    if not pid:
        # Launch it
        result = subprocess.run(
            ["powershell", "-Command", f"Get-StartApps | Where-Object {{$_.Name -like '*{name}*'}}"],
            capture_output=True, encoding="utf-8", errors="replace"
        )
        lines = [l for l in result.stdout.strip().splitlines() if name.lower() in l.lower()]
        if not lines:
            raise Exception(f"App '{name}' not found")
        
        app_id = lines[0].split()[-1]
        subprocess.Popen(f"explorer.exe shell:AppsFolder\\{app_id}")
        
        # Wait for it to appear
        for _ in range(15):
            time.sleep(1)
            pid = get_app_pid(name)
            if pid:
                break
        
        if not pid:
            raise Exception(f"Could not find {name} process after launching")
    
    print(f"Connecting to {name} (PID: {pid})")
    app = Application(backend="uia").connect(process=pid, timeout=15)
    return app, app.top_window().wrapper_object()