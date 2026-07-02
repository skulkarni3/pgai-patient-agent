"""
webhook_server.py

FastAPI server that receives post-call webhooks from Retell.
When a call ends, Retell POSTs the full transcript and call data here.
We save the transcript as demo_test/call_0.txt (overwritten each run, since
this is for one-off manual testing, not a batch) and print a summary.

Usage:
    python webhook_server.py

In a separate terminal, expose it with ngrok or cloudflared, see README.md.
"""

import json
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from retell.lib import verify as retell_verify_signature

load_dotenv()

RETELL_API_KEY = os.getenv("RETELL_API_KEY", "")
DEMO_DIR = Path(__file__).parent

app = FastAPI(title="PGAI Patient Agent — Webhook Server")


@app.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-retell-signature", "")

    # Retell always sends a signature; only skip the check if we have no API key to verify against.
    if RETELL_API_KEY and not retell_verify_signature(body.decode("utf-8"), RETELL_API_KEY, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(body)
    event_type = data.get("event")
    call = data.get("call", {})
    call_id = call.get("call_id", "unknown")

    print(f"\n{'='*60}")
    print(f"📥 Webhook received: {event_type}")
    print(f"   Call ID: {call_id}")

    if event_type == "call_ended":
        save_transcript(call_id, call)
        print_call_summary(call)

    elif event_type == "call_started":
        print(f"   Call started at {call.get('start_timestamp')}")

    elif event_type == "call_analyzed":
        # Retell sends analysis results after the call
        save_analysis(call_id, call)

    return {"status": "ok"}


def save_transcript(call_id: str, call: dict):
    """Save the transcript as demo_test/call_0.txt, matching record_calls.py's format."""
    path = DEMO_DIR / "call_0.txt"
    with open(path, "w") as f:
        f.write(call.get("transcript", ""))

    print(f"   💾 Transcript saved: {path}")


def save_analysis(call_id: str, call: dict):
    path = DEMO_DIR / "call_0_analysis.json"
    with open(path, "w") as f:
        json.dump(call, f, indent=2)
    print(f"   📊 Analysis saved: {path}")


def print_call_summary(call: dict):
    """Print a human-readable summary of the call to the terminal."""
    duration = call.get("duration_ms", 0) / 1000
    transcript = call.get("transcript", "")
    sentiment = call.get("call_analysis", {}).get("user_sentiment", "unknown")
    summary = call.get("call_analysis", {}).get("call_summary", "")

    print(f"\n📋 CALL SUMMARY")
    print(f"   Duration:  {duration:.0f}s")
    print(f"   Sentiment: {sentiment}")

    if summary:
        print(f"\n   Summary:\n   {summary}")

    if transcript:
        print(f"\n📝 TRANSCRIPT EXCERPT (last 500 chars):")
        print(f"   {transcript[-500:]}")

    print(f"\n{'='*60}\n")


@app.get("/")
async def health():
    return {"status": "running", "demo_dir": str(DEMO_DIR)}


if __name__ == "__main__":
    print("Starting webhook server on http://localhost:8000")
    print("Expose with: ngrok http 8000")
    print("Then add to .env: WEBHOOK_URL=https://your-url.ngrok.io/webhook\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
