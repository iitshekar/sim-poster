"""Posts the next NEW simulation to a Telegram channel, followed by a quiz.

Each simulation is posted once. posts.json is the queue: the first entry
without a "posted" date goes out, then gets stamped with today's date.
Add new simulations to the end of posts.json to keep the channel going.

The job runs daily but only posts when EVERY_DAYS have passed since the
last post (a manual "Run workflow" posts straight away).

Settings (GitHub Secrets/Variables):
  TELEGRAM_BOT_TOKEN  the token from @BotFather (secret)
  TELEGRAM_CHAT_ID    the channel, e.g. @iitshekar_sims
  DRY_RUN=1           print instead of posting (for testing)
  FORCE=1             post now, ignoring the gap (set for manual runs)
"""
import datetime
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "posts.json")
EVERY_DAYS = 3


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
    with open(QUEUE, encoding="utf-8") as f:
        posts = json.load(f)

    today = datetime.date.today()
    dates = [datetime.date.fromisoformat(p["posted"]) for p in posts if p.get("posted")]
    if dates and os.environ.get("FORCE") != "1":
        gap = (today - max(dates)).days
        if gap < EVERY_DAYS:
            print(f"Last post was {gap} day(s) ago. Next post in {EVERY_DAYS - gap} day(s).")
            return

    waiting = [p for p in posts if not p.get("posted")]
    if not waiting:
        # Fail on purpose: GitHub emails you, which is your reminder to add a simulation.
        sys.exit("Queue empty: no new simulation to post today. Add one to posts.json.")
    post = waiting[0]
    text, poll = build(post)

    if os.environ.get("DRY_RUN") == "1":
        print(text, "\n", json.dumps(poll, ensure_ascii=False, indent=1))
        print(f"\n{len(waiting) - 1} more waiting after this one.")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        sys.exit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    api(token, "sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML"})
    api(token, "sendPoll", {"chat_id": chat, **poll})

    post["posted"] = today.isoformat()
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Posted: {post['title']}. {len(waiting) - 1} left in the queue.")


if __name__ == "__main__":
    main()
