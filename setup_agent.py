"""
setup_agent.py

One-time script to create the patient agent in Retell.
Run this once, then use record_calls.py (or demo_test/make_call.py for a one-off call).

Usage:
    python setup_agent.py
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()

RETELL_API_KEY = os.getenv("RETELL_API_KEY")
VOICE_ID = os.getenv("VOICE_ID", "11labs-John")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

PROMPTS_DIR = Path(__file__).parent / "prompts"

HEADERS = {
    "Authorization": f"Bearer {RETELL_API_KEY}",
    "Content-Type": "application/json",
}

BASE_URL = "https://api.retellai.com"


def load_system_prompt() -> str:
    prompt_path = PROMPTS_DIR / "patient_persona.txt"
    with open(prompt_path, "r") as f:
        return f.read().strip()


def create_llm() -> dict:
    """Create a Retell LLM config with our patient persona."""
    system_prompt = load_system_prompt()

    payload = {
        "model": "gpt-4o",
        "general_prompt": system_prompt,
        "model_temperature": 0.7,
    }

    response = requests.post(
        f"{BASE_URL}/create-retell-llm",
        headers=HEADERS,
        json=payload,
    )

    if not response.ok:
        print(f"Error creating LLM: {response.status_code} {response.text}")
        response.raise_for_status()

    llm_data = response.json()
    print(f"✅ LLM created: {llm_data['llm_id']}")
    return llm_data


def create_agent(llm_id: str) -> dict:
    """Create a Retell agent that uses our LLM and an ElevenLabs voice."""
    payload = {
        "response_engine": {"type": "retell-llm", "llm_id": llm_id},
        "agent_name": "PGAI Patient Tester — Kevin Henrikson",
        # ElevenLabs voice via Retell's integration
        "voice_id": VOICE_ID,
        # Voice settings
        "voice_speed": 1.0,
        "voice_temperature": 1.0,
        # Responsiveness: how quickly to interrupt / respond
        "responsiveness": 1.0,
        # Enable interruption (real patients do interrupt)
        "enable_backchannel": True,
        # End call options
        "end_call_after_silence_ms": 10000,
        # Post-call webhook to receive transcript
        **({"webhook_url": WEBHOOK_URL} if WEBHOOK_URL else {}),
    }

    response = requests.post(
        f"{BASE_URL}/create-agent",
        headers=HEADERS,
        json=payload,
    )

    if not response.ok:
        print(f"Error creating agent: {response.status_code} {response.text}")
        response.raise_for_status()

    agent_data = response.json()
    print(f"✅ Agent created: {agent_data['agent_id']}")
    return agent_data


def main():
    print("Setting up PGAI patient test agent in Retell...\n")

    # Step 1: Create LLM config
    llm = create_llm()

    # Step 2: Create agent with that LLM
    agent = create_agent(llm["llm_id"])

    # Step 3: Save IDs so record_calls.py / make_call.py can use them
    config = {
        "llm_id": llm["llm_id"],
        "agent_id": agent["agent_id"],
    }

    config_path = Path(__file__).parent / "agent_ids.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n🎉 Done! Agent config saved to agent_ids.json")
    print(f"\nNext steps:")
    print(f"  Record a batch (10 calls): python record_calls.py")
    print(f"  Then analyze for bugs:     python review_calls.py")
    print(f"\n  Or for a one-off test call: python demo_test/make_call.py")
    print(f"                        (see demo_test/README.md)")
    print(f"\nAgent ID: {agent['agent_id']}")


if __name__ == "__main__":
    main()
