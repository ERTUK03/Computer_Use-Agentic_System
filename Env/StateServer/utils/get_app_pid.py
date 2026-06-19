import subprocess

def get_app_pid(name: str):
    result = subprocess.run(
        ["powershell", "-Command", 
         f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Process | Where-Object {{$_.Name -like '*{name}*' -and $_.MainWindowTitle -ne ''}} | Select-Object -First 1 -ExpandProperty Id"],
        capture_output=True, encoding="utf-8", errors="replace"
    )
    pid = result.stdout.strip()
    return int(pid) if pid else None