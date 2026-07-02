### Architecture

Retell is the backbone of this setup — setup_agent.py creates a Retell Agent (GPT-5o under the hood) with the patient persona as its system prompt, then wires it to an ElevenLabs voice (John) to make the voice agent that places calls. Once that's set up, Retell handles the full STT → LLM → TTS pipeline on their end.

For a batch of calls, record_calls.py fires off a call, polls Retell's API, and grabs the recording + transcript. Once the transcripts are saved, review_calls.py is a separate step that uses Claude to analyze each call and flag inconsistencies across the entire batch of calls. Since we don't have a source of ground truth for Pivot Point Orthopedics, it made sense to create a consistency report that cross checks facts provided by the PGAI agent across calls.

For quick one-off testing there's also make_call.py + webhook_server.py, which works a bit differently. You run webhook_server.py locally, expose it with ngrok, and register that public URL on the agent so Retell pushes the transcript to you the second a call ends instead of you having to go ask for it. It's handy for a single call since you get the transcript instantly with no polling, but it needs two terminals running plus a live ngrok tunnel — which is why I moved to the polling approach in record_calls.py once I started running calls in batches.

Finally, a few pivots were made to the prompts during testing:

* Prompt: The very first prompt had generic questions about a primary care clinic including questions about insurance verifications and prior authorization. After making a PGAI test account and making a test call myself, I tailored my questions to -
1. Exclude questions about insurance verification + prior auths
2. Exclude map of different insurances and synthetic member IDs 
3. Include more specific questions on orthopedic ailments and physical therapy
4. Include an example conversation flow 

You can notice the difference in persona in the demo_call and the calls there after. I had prompted the agent to be "annoying and pack as many questions as they can" which lead to the agent profusely apologizing and long responses. Fine tuning the prompt shaped the agent to be direct and assertive.

* Bug Reports: Initially, the agent was in charge of the bug reports as well which led to poor results. To ensure the agent wasn't overwhelmed, I decided to split the task and have an LLM analyze the transcripts instead.

