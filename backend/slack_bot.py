# backend/slack_bot.py
import os, requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

API = os.environ.get("API_BASE", "http://127.0.0.1:8000")
app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.event("file_shared")
def on_file_shared(body, client, say):
    file_id = body["event"]["file_id"]
    info = client.files_info(file=file_id)["file"]
    url = info["url_private_download"]
    # 봇 토큰으로 파일 다운로드
    data = requests.get(url, headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}, timeout=60).content
    r = requests.post(f"{API}/api/summarize", files={"file": (info["name"], data)})
    summary = r.json().get("summary","(no summary)")
    say(thread_ts=body["event"].get("ts"), text=f"*Summary for* `{info['name']}`\n```\n{summary[:3600]}\n```")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
