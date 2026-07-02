## PGAI Patient Agent 
The goal of this repository is to test Pretty Good AI's (PGAI) customer support agent across their core workflows: insurance verification, appointment scheduling, and prescription refills.

--
## Project Structure

```
pgai-patient-agent/
├── README.md              ← you are here
├── .env.example           ← copy to .env and fill in keys
├── requirements.txt
├── setup_agent.py         ← ONE-TIME: creates the Retell agent 
├── record_calls.py        ← batch ten calls saving audio + transcripts
├── review_calls.py        ← generates bug reports based on transcripts 
├── prompts/
│   └── patient_persona.txt ← the agent's system prompt 
├── transcripts/           ← call transcripts saved here 
├── audio/                 ← mp3 call recordings saved here 
├── bug_reports/           ← bug reports for each call + consistency report saved here 
├── demo_test/ 
│  └──logs/                ← call metadata saved here (you can check status)
│  └──make_call.py         ← run this to trigger a test call
│  └──webhook_server.py    ← receives transcripts after each call
    
```

---
## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create your `.env` file:**
   ```bash
   cp .env.example .env
   ```
   You will need to create a free Retell account and buy a phone number ($2/month) to obtain the secrets required for the .env:

   - `RETELL_API_KEY` — Dashboard → Settings → API Keys
   - `RETELL_FROM_NUMBER` — Dashboard → Phone Numbers 
   - `PGAI_PHONE_NUMBER` — Ask PGAI to provide test phone number 
   - `ANTHROPIC_API_KEY` - console.anthropic.com → API keys (Ensure you have $5 credit in Billing)
   - `WEBHOOK_URL` [OPTIONAL] - Read docs in demo_test to obtain url
   - `VOICE_ID` [OPTIONAL]- To get a list of voice ids run this command:
   ```bash
   source .env
   curl -s -H "Authorization: Bearer $RETELL_API_KEY" https://api.retellai.com/list-voices | python3 -m json.tool
   ```

3. **Create the agent in Retell (one-time):**
   ```bash
   python setup_agent.py
   ```
   This creates the agent and saves its ID to `agent_ids.json`.

4. **Record a batch of test calls:**
   ```bash
   python record_calls.py            # 10 calls by default
   python record_calls.py --count 3  # fewer, for a quick test
   ```
   Triggers calls one at a time, waits for each to end, and saves the recording as `audio/call_N.mp3` and the transcript as `transcripts/call_N.txt`. Polls Retell's `get-call` endpoint directly.

5. **Analyze the calls for bugs:**
   ```bash
   python review_calls.py
   python review_calls.py --call 3   # skips the consistency pass
   ```
   Writes `bug_reports/call_N_bug_report.txt` to report self-contradiction within a call and contradiction across calls.

---

