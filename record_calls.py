"""
record_calls.py

Makes a batch of outbound test calls to PGAI, waits for each one to finish,
and saves the recording to audio/ and the transcript to transcripts/.

Doesn't use webhook_server.py — it polls Retell's get-call endpoint directly,
so no ngrok tunnel is needed for this script to work.

Usage:
    python record_calls.py
    python record_calls.py --count 5
    python record_calls.py --to +18005551234
"""

import os
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()

RETELL_API_KEY = os.getenv("RETELL_API_KEY")
FROM_NUMBER = os.getenv("RETELL_FROM_NUMBER")
PGAI_PHONE_NUMBER = os.getenv("PGAI_PHONE_NUMBER")

HEADERS = {
    "Authorization": f"Bearer {RETELL_API_KEY}",
    "Content-Type": "application/json",
}

BASE_URL = "https://api.retellai.com"
AUDIO_DIR = Path(__file__).parent / "audio"
TRANSCRIPTS_DIR = Path(__file__).parent / "transcripts"

CALL_POLL_INTERVAL_S = 5
CALL_TIMEOUT_S = 600          # give up waiting for the call to end after 10 min
RECORDING_POLL_INTERVAL_S = 3
RECORDING_TIMEOUT_S = 60      # recording_url shows up shortly after call ends


def load_agent_id() -> str:
    import json
    config_path = Path(__file__).parent / "agent_ids.json"
    if not config_path.exists():
        raise FileNotFoundError(
            "agent_ids.json not found. Run `python setup_agent.py` first."
        )
    with open(config_path) as f:
        return json.load(f)["agent_id"]


def start_call(agent_id: str, to_number: str) -> str:
    payload = {
        "from_number": FROM_NUMBER,
        "to_number": to_number,
        "override_agent_id": agent_id,
    }
    response = requests.post(
        f"{BASE_URL}/v2/create-phone-call", headers=HEADERS, json=payload
    )
    response.raise_for_status()
    return response.json()["call_id"]


def get_call(call_id: str) -> dict:
    response = requests.get(f"{BASE_URL}/v2/get-call/{call_id}", headers=HEADERS)
    response.raise_for_status()
    return response.json()


def wait_for_call_to_end(call_id: str) -> dict:
    elapsed = 0
    while elapsed < CALL_TIMEOUT_S:
        call = get_call(call_id)
        status = call.get("call_status")
        if status == "ended":
            return call
        if status in ("error", "not_connected"):
            raise RuntimeError(f"Call {call_id} did not connect ({status}): {call.get('disconnection_reason')}")
        time.sleep(CALL_POLL_INTERVAL_S)
        elapsed += CALL_POLL_INTERVAL_S
    raise TimeoutError(f"Call {call_id} did not end within {CALL_TIMEOUT_S}s")


def wait_for_recording(call_id: str) -> str:
    elapsed = 0
    while elapsed < RECORDING_TIMEOUT_S:
        call = get_call(call_id)
        recording_url = call.get("recording_url")
        if recording_url:
            return recording_url
        time.sleep(RECORDING_POLL_INTERVAL_S)
        elapsed += RECORDING_POLL_INTERVAL_S
    raise TimeoutError(f"recording_url not available for call {call_id} after {RECORDING_TIMEOUT_S}s")


def save_recording(recording_url: str, mp3_path: Path):
    response = requests.get(recording_url, stream=True)
    response.raise_for_status()
    with open(mp3_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def save_transcript(transcript: str, txt_path: Path):
    with open(txt_path, "w") as f:
        f.write(transcript or "")


def run_batch(count: int, to_number: str):
    AUDIO_DIR.mkdir(exist_ok=True)
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    agent_id = load_agent_id()

    for i in range(1, count + 1):
        print(f"\n[{i}/{count}] Calling {to_number}...")
        try:
            call_id = start_call(agent_id, to_number)
            print(f"   Call ID: {call_id} — waiting for it to end...")

            call = wait_for_call_to_end(call_id)
            print(f"   Call ended. Waiting for recording...")

            recording_url = wait_for_recording(call_id)

            mp3_path = AUDIO_DIR / f"call_{i}.mp3"
            txt_path = TRANSCRIPTS_DIR / f"call_{i}.txt"

            save_recording(recording_url, mp3_path)
            save_transcript(call.get("transcript", ""), txt_path)

            print(f"   Saved: audio/{mp3_path.name}, transcripts/{txt_path.name}")
        except Exception as e:
            print(f"   Error on call {i}: {e}")
            print(f"   Skipping to next call.")

    print(f"\nDone. Recordings saved to {AUDIO_DIR}, transcripts saved to {TRANSCRIPTS_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Make a batch of test calls to PGAI and record them")
    parser.add_argument("--count", type=int, default=10, help="Number of calls to make")
    parser.add_argument("--to", default=PGAI_PHONE_NUMBER, help="Phone number to call")
    args = parser.parse_args()

    if not args.to:
        print("Error: PGAI_PHONE_NUMBER not set in .env and --to not provided.")
        exit(1)

    run_batch(count=args.count, to_number=args.to)


if __name__ == "__main__":
    main()
