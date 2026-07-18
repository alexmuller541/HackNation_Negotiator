# The Negotiator

Voice agents that call, compare, and haggle — ElevenLabs challenge, Hack-Nation 6th Global AI Hackathon. Vertical: **local moving**. Full plan in [PLAN.md](PLAN.md).

## Team roles

| Who | Role | Owns |
|-----|------|------|
| A (frontend) | Dashboard | `frontend/` — intake/spec confirmation, live call board, ranked report |
| B | Backend/orchestrator | `backend/`, tool endpoints (`log_quote_item`, `get_best_bid`, `log_outcome`), red-flag + ranking engine |
| Alex (phone-based) | Conversation design + ElevenLabs config | `prompts/`, `personas/`, `verticals/`, `evals/`, `demo/`, `docs/`, EL dashboard, credit chase |
| D | Voice integration + doc intake | EL tool wiring, web-call sessions, photo/PDF → job spec |

## Hard rules (agreed hour 0)

1. **Prompts are files.** Agents load system prompts from `prompts/` and config from `verticals/` — never hardcoded. Alex iterates on these from a phone; a merged PR changes agent behavior with zero code.
2. **Schemas are the contract.** `schemas/job_spec.schema.json` and `schemas/quote.schema.json` — both intake paths produce the former, every call produces exactly one of the latter.
3. **Backend is publicly reachable by hour 6** (deploy or ngrok) so ElevenLabs tool calls and phone-side testing work. Localhost-only blocks half the team.
4. **Voice minutes are the scarce resource.** Iterate in text mode against `personas/` + `evals/golden-calls.md` first; dial only to verify.

## Repo layout

```
prompts/      system prompts for interviewer & caller agents
personas/     role-player cards (hidden floors + concession rules)
verticals/    per-vertical config — swap file, not code
schemas/      job spec + quote JSON schemas (the contract)
evals/        golden-call checklist, run before burning minutes
demo/         demo script + success-criteria mapping
docs/         the four conversation requirements (judge-facing)
backend/      orchestrator, tool endpoints, ranking (B)
frontend/     dashboard (A)
```

## Working from a phone (Alex)

Sessions run on [claude.ai/code](https://claude.ai/code) against this repo (needs the Claude GitHub app connected). Kickoff prompt to paste at the start of each session:

> I'm working from my phone on the-negotiator repo (ElevenLabs "The Negotiator" hackathon — see PLAN.md). I own conversation design: prompts/, personas/, verticals/moving.yaml, evals/, demo/, docs/. The prompts are loaded as files by the agents, so my changes ship behavior. Read PLAN.md and docs/conversation-requirements.md first, keep edits inside my directories, and open a PR when done. This session's task: [TASK]
