# Agent Tool Definitions (cleaning · three-agent) — paste into ElevenLabs dashboard

Webhook tools. Maxim maps these into each agent's tool form; Umra owns the endpoints and replaces `BACKEND_URL`. Names, descriptions, and parameter schemas below are the contract — keep them in sync with Umra's `/tools/*` routes and the text simulator (`sim/negotiate.py`), which mocks the same tools.

**Which agent gets which tool** (from the v4 plan):

| Agent | Tools |
|---|---|
| **1 — Interviewer** | *(none)* — transcript → Aleks's `POST /specs` |
| **2 — Caller** (Round 1) | `log_quote_item`, `log_outcome` |
| **3 — Closer** (Round 2) | `get_best_bid`, `log_quote_item`, `log_outcome` |

`call_id` and `spec_id` are provided by Maxim as EL dynamic variables / session context — the **agent never supplies them**. The agent-facing parameters are only the ones the model fills from the conversation.

---

## log_quote_item  (Caller + Closer)

- **Description (agent-facing):** Log one itemized fee or line the cleaning company just quoted, immediately when you hear it. Call once per line — base/labor rate, per-cleaner hourly, trip/travel fee, each add-on (fridge, oven, windows, baseboards, laundry), supplies, tax.
- **Method / URL:** `POST BACKEND_URL/tools/log_quote_item`
- **Agent parameters:**

```json
{
  "type": "object",
  "properties": {
    "label":  { "type": "string", "description": "What the charge is for, e.g. 'inside oven' or 'per-cleaner hourly'" },
    "amount": { "type": "number", "description": "Dollar amount for this line" },
    "disclosed_voluntarily": { "type": "boolean", "description": "false if you had to press for it" },
    "negotiable": { "type": "boolean", "description": "true if the rep indicated flexibility" }
  },
  "required": ["label", "amount"]
}
```

- **Server adds from context:** `call_id`. (Umra's core endpoint is `{call_id, label, amount}`; `disclosed_voluntarily` / `negotiable` are optional extras the report uses — safe to ignore server-side if unused.)

---

## get_best_bid  (Closer only)

- **Description (agent-facing):** Get the current best competing itemized quote from other companies for this same job, to use as negotiation leverage. Returns null if no competing quote exists yet — in that case you must NOT imply one exists.
- **Method / URL:** `GET BACKEND_URL/tools/get_best_bid?spec_id={spec_id}`
- **Agent parameters:** none (`spec_id` comes from session context; the current company is excluded server-side).
- **Returns:** `{ "best_bid": 355, "company": "SparkleClean", "pricing_model": "flat" }` or `{ "best_bid": null }`

---

## log_outcome  (Caller + Closer)

- **Description (agent-facing):** Record the structured outcome of this call. MUST be called exactly once before the call ends. Never end a call without it. Never end on a vague number.
- **Method / URL:** `POST BACKEND_URL/tools/log_outcome`
- **Agent parameters:**

```json
{
  "type": "object",
  "properties": {
    "outcome":       { "type": "string", "enum": ["quote", "callback", "declined"] },
    "initial_total": { "type": "number", "description": "First total quoted, before negotiation (Closer: the Round-1 price)" },
    "final_total":   { "type": "number", "description": "Total after this call" },
    "pricing_model": { "type": "string", "description": "flat | hourly | per_cleaner" },
    "conditions":    { "type": "array", "items": { "type": "string" }, "description": "e.g. 'biweekly commitment', 'weekday slot', 'cash only'" },
    "callback_contact": { "type": "string", "description": "Name, if outcome is callback" },
    "callback_window":  { "type": "string", "description": "Time window, if outcome is callback" },
    "notes":         { "type": "string", "description": "What moved the price (which lever), or why declined" }
  },
  "required": ["outcome"]
}
```

- **Server adds from context:** `call_id`. (Umra's core endpoint is `{call_id, outcome, total, pricing_model}` — map `total` = `final_total`; the rest feeds the ranked report's price-drop callout and red-flag reasons.)

---

## Outcome vocabulary (keep aligned across agents, endpoints, and the sim)
`quote` · `callback` · `declined` — never a fourth value, never a vague "around two hundred".
