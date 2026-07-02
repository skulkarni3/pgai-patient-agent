"""
review_calls.py

Reads all call transcripts from transcripts/call_N.txt (saved by record_calls.py)
and asks Claude to critique PGAI, the customer rep. Two passes:

1. Per-call: each transcript reviewed on its own for process failures
   (self-contradiction, unfollowed escalation promises, ignored questions, etc).
   Written to bug_reports/call_N_bug_report.txt.
2. Cross-call consistency: all transcripts compared together for cases where
   PGAI gave different answers to the same question in different calls (hours,
   pricing, policies, etc). Written to bug_reports/consistency_report.txt.

Pivot Point Orthopedics is a fake clinic, so there's no external source of
truth to fact-check a single call against — these two passes are the only
ways to catch a factual bug without one: PGAI contradicting itself within a
call, or contradicting itself across calls.

Usage:
    python review_calls.py
    python review_calls.py --call 3   # just re-run call_3.txt (skips consistency pass)
"""

import os
import re
import argparse
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-5"

TRANSCRIPTS_DIR = Path(__file__).parent / "transcripts"
BUG_REPORTS_DIR = Path(__file__).parent / "bug_reports"

client = Anthropic(api_key=ANTHROPIC_API_KEY)

PER_CALL_INSTRUCTIONS = """\
You are reviewing a transcript of a phone call to Pivot Point Orthopedics' \
customer support AI, PGAI. The call was placed by a test agent roleplaying a \
patient (Kevin Henrikson) — the patient's phrasing, tone, or behavior is NOT \
what you're evaluating. Only critique PGAI, the customer service rep.

Pivot Point Orthopedics is a fake clinic made up for this test — there is no \
real-world source of truth for its hours, providers, or policies. Do NOT flag \
something as wrong just because it sounds implausible to you. Only flag an \
issue if it's verifiable from this transcript alone: PGAI contradicting \
something it itself said earlier in the SAME call, failing to actually do \
what it claimed, or a clear process failure.

Evaluate PGAI against:
- Did it contradict itself later in the same call (e.g. states different \
hours, prices, or policies at two different points)?
- Did it actually act on requests (submit a refill, book a real slot) or just \
vaguely defer ("someone will call you back", redirect to a portal)?
- Did it disclose appointment/prescription/insurance details before verifying \
the patient's identity (DOB)?
- Did it promise an escalation or transfer ("let me connect you to the front \
desk") and then never follow through, just continuing the same conversation?
- Did it give clinical advice (dosage, treatment decisions) it should have \
deferred to a provider?
- Did it state precise structured data (CPT codes, exact dollar amounts) \
instantly with no hedging or "let me check," when a real rep would need to look it up?
- Did it feel robotic — looping, giving generic non-answers, or ignoring parts \
of a multi-part question?

Example of a good bug report:
Bug: Agent offers to transfer the patient but never follows through.
Details: When asked "can I bring my kids into the waiting room?", PGAI said \
"I can connect you to our front desk, would you like me to do that?" The \
patient agreed, but PGAI just moved on to the next topic — no transfer \
happened and the question was never answered.

Write a concise bug report in that style. For each real issue found, include: \
what happened, why it's a problem, and a short quote from the transcript \
showing where. Skip severity/formatting boilerplate. If PGAI handled the call \
well, say so in one or two sentences instead of manufacturing issues.
"""

CONSISTENCY_INSTRUCTIONS = """\
You are checking transcripts of multiple separate test calls to Pivot Point \
Orthopedics' customer support AI, PGAI. Each call was placed independently. \
Pivot Point Orthopedics is a fake clinic — there's no external source of \
truth for its hours, providers, pricing, or policies, so you can't fact-check \
a single call. But real-world facts don't change from call to call, so if \
PGAI gives two different answers to the same or a similar question in \
different calls, at least one of them is wrong.

Compare the calls and find contradictions in things like: office hours, \
address, accepted insurance plans, copay/pricing amounts, CPT codes, provider \
names and availability, and parking/accessibility policies. Ignore \
differences that are legitimately caller-specific (e.g. different insurance \
plans for different patients) — only flag things that should be constant \
across all callers.

Example of a good bug report:
Bug: Office hours are inconsistent across calls.
Calls: call_2, call_7
Details: In call_2, PGAI said "we're open 7am-5pm Monday through Friday, \
closed weekends." In call_7, PGAI said "we're open 9am-3pm on Saturdays and \
Sundays." Both can't be true — callers are getting contradictory information.

Write a concise report in that style, one entry per contradiction. If nothing \
is inconsistent, say so plainly instead of manufacturing issues.
"""


def call_number(path: Path) -> int:
    match = re.search(r"call_(\d+)\.txt$", path.name)
    return int(match.group(1)) if match else 0


def load_transcripts(call_num: int = None) -> list:
    paths = sorted(TRANSCRIPTS_DIR.glob("call_*.txt"), key=call_number)
    if call_num is not None:
        paths = [p for p in paths if call_number(p) == call_num]
    return [(call_number(p), p.read_text().strip()) for p in paths if p.read_text().strip()]


def extract_text(response) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return ""


def review_single_call(n: int, transcript: str):
    print(f"Reviewing call_{n}...")
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=PER_CALL_INSTRUCTIONS,
            messages=[{"role": "user", "content": f"Transcript:\n\n{transcript}"}],
        )
    except Exception as e:
        print(f"   Error analyzing call_{n}: {e}")
        return

    report = extract_text(response)
    if not report:
        print(f"   Warning: no text in response for call_{n} (stop_reason={response.stop_reason}) — skipping, not writing an empty file.")
        return

    out_path = BUG_REPORTS_DIR / f"call_{n}_bug_report.txt"
    out_path.write_text(report)
    print(f"   Saved: {out_path.name}")


def check_consistency(transcripts: list):
    if len(transcripts) < 2:
        print(f"\nSkipping consistency check — need at least 2 transcripts, found {len(transcripts)}.")
        return

    print(f"\nChecking consistency across calls: {[n for n, _ in transcripts]}")
    prompt = "\n\n".join(f"=== Call {n} ===\n{text}" for n, text in transcripts)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=CONSISTENCY_INSTRUCTIONS,
        messages=[{"role": "user", "content": prompt}],
    )

    out_path = BUG_REPORTS_DIR / "consistency_report.txt"
    out_path.write_text(extract_text(response))
    print(f"Saved: {out_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Analyze call transcripts and write bug reports")
    parser.add_argument("--call", type=int, help="Only review this call number (skips consistency check)")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not set in .env")
        exit(1)

    BUG_REPORTS_DIR.mkdir(exist_ok=True)

    transcripts = load_transcripts(call_num=args.call)
    if not transcripts:
        print(f"No matching transcripts found in {TRANSCRIPTS_DIR}")
        return

    for n, text in transcripts:
        review_single_call(n, text)

    if args.call is None:
        check_consistency(transcripts)

    print(f"\nDone. Bug reports saved to {BUG_REPORTS_DIR}")


if __name__ == "__main__":
    main()
