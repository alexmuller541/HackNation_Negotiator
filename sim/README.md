# Text-mode negotiation simulator

Tests the caller prompt against the persona cards **without burning ElevenLabs minutes**. The caller is a Claude agent with the same three tools the voice agent will have (`log_quote_item`, `get_best_bid`, `log_outcome`); the counterparty is a second Claude playing the persona card, hidden policy and all.

## Setup (once)

```bash
python3 -m pip install --user anthropic
export ANTHROPIC_API_KEY=sk-ant-...   # or put it in .env and `source` it
```

## Run

```bash
cd ~/HackNation_Negotiator
python3 sim/negotiate.py personas/tough-negotiator.md
python3 sim/negotiate.py personas/lowballer.md
python3 sim/negotiate.py personas/upseller.md
python3 sim/negotiate.py personas/stonewaller.md
```

Run order matters: quotes persist in `sim/quotes.json`, so the second call onward has real leverage for `get_best_bid` — that's how you rehearse the demo's "can you beat $X?" moment. Delete `sim/quotes.json` to reset the market.

Each run prints the live dialogue, an eval summary (outcome, price movement, red flags, disclosure check, cost), and writes a full transcript + structured record to `sim/runs/`.

## Cost

Defaults: caller = `claude-opus-4-8` (the negotiation quality matters), persona = `claude-haiku-4-5`. A full run is typically **$0.20–0.50**. For cheap bulk iteration:

```bash
CALLER_MODEL=claude-sonnet-5 python3 sim/negotiate.py personas/upseller.md
```

## Iterating (Alex's loop, works from a phone via Claude Code web)

1. Edit `prompts/caller.md` or a persona card.
2. Ask whoever has a terminal (or a Claude Code session on the repo) to run the sim against the affected personas.
3. Check the eval summary against `evals/golden-calls.md` — cases 2, 3, 5, and 10 must pass before any demo recording.
