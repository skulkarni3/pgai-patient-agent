# Demo_test 
This is a separate flow for triggering a single ad-hoc call instead of
a batch. The main workflow (`record_calls.py` + `review_calls.py` at the
project root) doesn't need any of this — only use it if you specifically want to test one call manually and watch the transcript arrive in real time.

This test doesn't get the audio file but you can get the transcript from a webhook server. When you run webhook_server.py, it opens up a local host server. To let Recall push it's transcript to our server, we can use Cloudfare (similar to ngrok but you don't need to make an account) to make our server reachable from the internet.

## Setup

1. **Install Cloudflare** (not a Python package, so it's not in `requirements.txt`):
   ```bash
   brew install cloudflared
   ```

2. **Start the webhook server** (in one terminal, from the project root):
   ```bash
   python demo_test/webhook_server.py
   ```

3. **Expose local server with Cloudflare** (in another terminal):
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
   Copy the `https://xxx.trycloudflare.com ` URL and set `WEBHOOK_URL=https://xxx.trycloudflare.com/webhook` in `.env`, then re-run `python setup_agent.py` so it registers the webhook URL on the agent. 

   Important: Don't forget to add /webhook at the end of the url path! After setting it in .env, make sure to `python setup_agent.py` remake the agent with so it registers the url.

4. **Make the call:**
   ```bash
   python demo_test/make_call.py
   python demo_test/make_call.py --to +18005551234   # call a different number
   python demo_test/make_call.py --dry-run           # print API payload without calling
   ```

Retell sends the transcript to the webhook, saved to `demo_test/` folder. Call metadata for `make_call.py` is saved to `demo_test/logs/.`

## Waiting for the call to finish? Check call status! 
Don't want to wait around for the webhook, or want to check on a call that's
already in progress? Query Retell directly:

1. **Find the call_id.** Every call made with `make_call.py` prints its
   `call_id` and saves it to `demo_test/logs/call_<call_id>_meta.json`.

2. **Paste it into this curl command** (from the project root):
   ```bash
   source .env
   curl -s -H "Authorization: Bearer $RETELL_API_KEY" \
     https://api.retellai.com/v2/get-call/<call_id> | python3 -m json.tool
   ```

3. **Check `call_status` in the response:**
   - `"registered"` or `"ongoing"` — still in progress
   - `"ended"` — done; the response will also include `transcript` and `recording_url`
   - `"error"` / `"not_connected"` — the call didn't go through

You can also watch calls live in the Retell dashboard at https://dashboard.retellai.com → Calls
