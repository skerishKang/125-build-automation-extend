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
    # 1) 즉시 수신 확인 메시지
    ack_msg = None
    try:
        ack_msg = say(
            thread_ts=body["event"].get("ts"),
            text=f"📥 `{info['name']}` 파일을 받았어요. 분석 중입니다…"
        )
    except Exception:
        ack_msg = None

    # 2) 파일 다운로드 및 분석
    try:
        data = requests.get(
            url,
            headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"},
            timeout=60
        ).content
        # 진행 단계 업데이트: 다운로드 완료
        if ack_msg and ack_msg.get("ts") and ack_msg.get("channel"):
            try:
                client.chat_update(
                    channel=ack_msg["channel"],
                    ts=ack_msg["ts"],
                    text=f"📥 `{info['name']}` 다운로드 완료. 요약 생성 중…"
                )
            except Exception:
                pass

        r = requests.post(
            f"{API}/api/summarize",
            files={"file": (info["name"], data)},
            timeout=120
        )
        try:
            summary = r.json().get("summary", "(no summary)")
        except Exception:
            summary = (r.text or "(no summary)")
        final_text = f"*Summary for* `{info['name']}`\n```\n{summary[:3600]}\n```"

        # 3) 완료 시 기존 메시지 업데이트 (실패 시 새 메시지)
        if ack_msg and ack_msg.get("ts") and ack_msg.get("channel"):
            try:
                client.chat_update(
                    channel=ack_msg["channel"],
                    ts=ack_msg["ts"],
                    text=final_text
                )
                return
            except Exception:
                pass

        # 업데이트 실패하거나 ack가 없으면 새 메시지로 전달
        say(thread_ts=body["event"].get("ts"), text=final_text)

    except Exception as e:
        err_text = f"`{info['name']}` 처리 중 오류가 발생했어요: {e}"
        if ack_msg and ack_msg.get("ts") and ack_msg.get("channel"):
            try:
                client.chat_update(channel=ack_msg["channel"], ts=ack_msg["ts"], text=err_text)
                return
            except Exception:
                pass
        say(thread_ts=body["event"].get("ts"), text=err_text)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
