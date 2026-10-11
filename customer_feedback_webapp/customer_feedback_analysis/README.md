# Customer Feedback Analyser: web app

A customer types feedback on a web page, sees the sentiment (positive / neutral / negative),
and negative feedback is sent to the business owner on Telegram.

```
Browser (frontend/index.html) -> POST /predict -> clean_text -> TF-IDF -> Logistic Regression
                                                  -> if negative -> Telegram message to owner
```

## Add it to your existing project

Copy these into your `customer_feedback_analysis/` project (it already has `src/data/preprocess.py` and `models/`):

- `src/api/app.py` (replaces your Phase 12/13 version)
- `src/alerts/telegram_alert.py` (replaces your Phase 13 version)
- `frontend/index.html`, `tests/test_webapp.py`, `.env.example`, `.gitignore`

Then:

```bash
pip install python-dotenv pytest httpx      # also add python-dotenv to requirements.txt
cp .env.example .env                        # then fill in TELEGRAM_BOT_TOKEN
```

## Connect Telegram

1. Revoke and replace your bot token first if it was ever shared or screenshotted: in @BotFather send `/revoke`, pick the bot, and paste the new token into `.env`.
2. Open your bot in Telegram (t.me/cus_feedback_bot) and press Start / send any message.
3. `python -m src.alerts.telegram_alert chat-id` prints your chat id. Put it in `.env` as `TELEGRAM_CHAT_ID`.
4. `python -m src.alerts.telegram_alert test` should buzz your phone.

If the owner is a different person, they must message the bot first, and you use their chat id.
For a group, add the bot to the group; the id is a negative number.

## Run

```bash
uvicorn src.api.app:app --reload
```

Open http://127.0.0.1:8000. `GET /health` shows whether Telegram is configured.
API docs: http://127.0.0.1:8000/docs. The `/predict` contract from the guide still works (`{"text": "..."}`);
the response adds `confidence`, `scores`, and `owner_alerted`.

## Test

```bash
pytest -q
```

Telegram is mocked in the tests, so nothing is sent.

## Behaviour worth knowing

- Alerts are sent after the response, so Telegram slowness never delays the customer, and a Telegram failure never breaks the form.
- Each visitor is limited to 5 submissions per minute (`RATE_LIMIT_PER_MIN`) so nobody can flood the owner's phone. Behind a reverse proxy, run uvicorn with `--proxy-headers` so the real visitor IP is used.
- Feedback is not stored. The only record is the Telegram message.
- Text is rejected if it is empty or has no words left after cleaning (for example only symbols).
