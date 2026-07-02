"""
make_call.py

Triggers an outbound call from the patient agent to PGAI's phone number.

Usage:
    python make_call.py
    python make_call.py --to +18005551234   # override the target number
    python make_call.py --dry-run           # print config without calling
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
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
LOGS_DIR = Path(__file__).parent / "logs"


def load_agent_id() -> str:
    config_path = Path(__file__).parent.parent / "agent_ids.json"
    if not config_path.exists():
        raise FileNotFoundError(
            "agent_ids.json not found. Run `python setup_agent.py` first."
        )
    with open(config_path) as f:
        return json.load(f)["agent_id"]


def make_call(to_number: str, dry_run: bool = False) -> dict:
    agent_id = load_agent_id()

    payload = {
        "from_number": FROM_NUMBER,
        "to_number": to_number,
        "override_agent_id": agent_id,
        "metadata": {
            "test_run": True,
            "target": "pgai_customer_support",
            "timestamp": datetime.utcnow().isoformat(),
        },
    }

    if dry_run:
        print("DRY RUN — would send:")
        print(json.dumps(payload, indent=2))
        return {}

    print(f"📞 Calling {to_number}...")
    response = requests.post(
        f"{BASE_URL}/v2/create-phone-call",
        headers=HEADERS,
        json=payload,
    )

    if not response.ok:
        print(f"Error making call: {response.status_code}")
        print(response.text)
        response.raise_for_status()

    call_data = response.json()

    # Save call metadata locally so we can match up transcripts later
    LOGS_DIR.mkdir(exist_ok=True)
    call_id = call_data.get("call_id", "unknown")
    log_path = LOGS_DIR / f"call_{call_id}_meta.json"
    with open(log_path, "w") as f:
        json.dump(call_data, f, indent=2)

    print(f"✅ Call initiated!")
    print(f"   Call ID:    {call_id}")
    print(f"   Status:     {call_data.get('call_status', 'unknown')}")
    print(f"   Log saved:  {log_path}")
    print(f"\nThe transcript will arrive via webhook when the call ends.")
    print(f"(Make sure webhook_server.py is running in another terminal.)")

    return call_data


def main():
    parser = argparse.ArgumentParser(description="Make an outbound test call to PGAI")
    parser.add_argument("--to", default=PGAI_PHONE_NUMBER, help="Phone number to call")
    parser.add_argument("--dry-run", action="store_true", help="Print config without calling")
    args = parser.parse_args()

    if not args.to:
        print("Error: PGAI_PHONE_NUMBER not set in .env and --to not provided.")
        exit(1)

    make_call(to_number=args.to, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
