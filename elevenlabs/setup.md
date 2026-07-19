# ElevenLabs Dashboard Setup (phone-friendly, Alex's lane)

> **STATUS: agents exist but must be reconfigured before demo.** The existing agent IDs are in [created.json](created.json). Their original moving prompts and placeholder webhook URL are not compatible with the merged cleaning backend. Update the prompts and tool URLs using [tools.md](tools.md) after the backend has a public HTTPS URL.
>
> **Person D:** the four tools point at placeholder URLs (`backend-placeholder.negotiator.example`) — update each tool's URL via dashboard or API once the backend is deployed. Voice is the stock demo voice; pick better ones in the dashboard (free).

All of this is **free to configure** — only conversation minutes burn credits. Do the full setup before dialing anything.

## Agent 1: The Interviewer (intake)

1. ElevenLabs dashboard → **Agents** → Create agent → name it `negotiator-interviewer`.
2. **First message:** "Hi! I’m your cleaning assistant. I’ll ask a few questions so cleaners can give you a comparable quote — ready?"
3. **System prompt:** paste [prompts/interviewer.md](../prompts/interviewer.md), then append the `interview_questions` list from [verticals/cleaning.yaml](../verticals/cleaning.yaml).
4. **Tool:** `save_job_spec` (see [tools.md](tools.md)) → Person D wires the webhook URL.
5. Voice: pick something warm/neutral. Keep model settings default (latency matters more than quality here).

## Agent 2: The Caller (negotiator)

1. Create agent → `negotiator-caller`.
2. **First message:** leave EMPTY / set to wait — the counterparty answers the phone first. If the platform requires one, use: "Hi, is this {{company_name}}?"
3. **System prompt:** paste [prompts/caller.md](../prompts/caller.md). Use dynamic variables for `{company_name}`, `{spec_id}`, `{call_id}`, and `{job_spec_json}`.
4. **Tools:** `log_quote_item`, `get_best_bid`, `log_outcome` (see [tools.md](tools.md)).
5. Turn-taking: enable interruptions (barge-in) — the brief explicitly judges this.

## Testing discipline (credits!)

- Iterate prompts in **text mode first**: `python3 sim/negotiate.py personas/tough-negotiator.md` (see [sim/README.md](../sim/README.md)). Only dial to verify voice behavior.
- One ~60s sanity call after setup to confirm the account/voice pipeline works. Then stop until the backend is deployed (hour-6 checkpoint).
- Tool calls fail until Person B's endpoints are publicly reachable — don't burn minutes testing tools against localhost.
- Keep every good recording — demo backup material.
