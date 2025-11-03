# tools/watch_folder.py
import os, time, requests, pathlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

API = os.environ.get("API_BASE", "http://127.0.0.1:8000")
WATCH = os.environ.get("WATCH_DIR", r"G:\dropin")
OUT = os.environ.get("OUT_DIR", r"G:\dropin\out")

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        path = event.src_path
        try:
            with open(path, "rb") as f:
                r = requests.post(f"{API}/api/summarize", files={"file": (os.path.basename(path), f)})
            r.raise_for_status()
            pathlib.Path(OUT).mkdir(parents=True, exist_ok=True)
            with open(os.path.join(OUT, os.path.basename(path)+".summary.txt"), "w", encoding="utf-8") as w:
                w.write(r.json().get("summary",""))
            print("OK:", path)
        except Exception as e:
            print("ERR:", path, e)

if __name__ == "__main__":
    from watchdog.observers import Observer
    obs = Observer()
    obs.schedule(Handler(), WATCH, recursive=False)
    obs.start()
    print(f"Watching {WATCH} → results in {OUT}")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()