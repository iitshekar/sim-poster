"""Posts one simulation a day to a Telegram channel, followed by a quiz.

Settings come from environment variables (set as GitHub Secrets/Variables):
  TELEGRAM_BOT_TOKEN  the token from @BotFather (secret)
  TELEGRAM_CHAT_ID    the channel, e.g. @iitshekar
  DRY_RUN=1           print instead of posting (for testing)
"""
import datetime
import json
import os
import sys
import urllib.request

START = datetime.date(2026, 10, 7)  # day 0 of the rotation


def pick(posts, today):
    """Rotate through posts in order, one per day."""
    return posts[(today - START).days % len(posts)]


def api(token, method, payload):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if not body.get("ok"):
        raise RuntimeError(f"{method} failed: {body}")
    return body


def build(post):
    text = (
        f"<b>{post['title']}</b>  ·  {post['level']}\n\n"
        f"{post['text']}\n\n"
        f"▶️ Try it free: {post['url']}\n"
        "Works on phones, tablets and laptops."
    )
    q = post["quiz"]
    poll = {
        "question": q["question"],
        "options": [{"text": o} for o in q["options"]],
        "type": "quiz",
        "correct_option_id": q["correct"],
        "explanation": q["explanation"],
        "is_anonymous": True,
    }
    return text, poll


def main():
    with open(os.path.join(os.path.dirname(__file__), "posts.json"), encoding="utf-8") as f:
        posts = json.load(f)
    post = pick(posts, datetime.date.today())
    text, poll = build(post)

    if os.environ.get("DRY_RUN") == "1":
        print(text, "\n", json.dumps(poll, ensure_ascii=False, indent=1))
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        sys.exit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    api(token, "sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML"})
    api(token, "sendPoll", {"chat_id": chat, **poll})
    print(f"Posted: {post['title']}")


if __name__ == "__main__":
    main()
