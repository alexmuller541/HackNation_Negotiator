# Frontend ↔ Backend contract alignment

For Nimra. Her frontend (`frontend/the-negotiator`) is fully built and runs on mocks (`NEXT_PUBLIC_USE_MOCKS=true`), so nothing here is blocking. But `lib/types.ts` and `lib/api.ts` were written against an assumed API that differs from what the backend actually is. This note maps every difference so the fix is confined to those **two files**.

## The one mental-model shift

| Frontend assumes | Reality |
|---|---|
| a **`jobId`** threaded through every call | the unit of work is a **`spec_id`** (a UUID from the `specs` table). **Treat `jobId` === `spec_id`** — same string, minimal rename. |
| upload returns an id, then you **poll** `getJobSpec` until extraction finishes | extraction is **synchronous** — `POST /intake/doc` returns the full draft spec in the response. The Processing page becomes a spinner during that one request, not a poll loop. |
| the spec is **flat** (`cleaningType`, `houseSizeSqft`, …) | the spec is **nested** (`property{}`, `clean_type`, `frequency`, `condition{}`, `add_ons{}`, `access{}`, `schedule{}`) — snake_case, more fields. Full shape below. |

## Endpoint map (`lib/api.ts`)

| Fn | Frontend assumed | Real endpoint | Exists? |
|---|---|---|---|
| `uploadJobDocument(file)` | `POST /upload` → `{jobId}` | `POST /intake/doc` — multipart, field **`file`** → `{ job_spec, missing_fields, intake_source }` | ✅ built (`backend/intake_router.py`) |
| `getJobSpec(jobId)` | `GET /job/:id` (poll) | not needed — the spec comes back from `/intake/doc`. To reload a saved one: `GET /specs/{spec_id}` | intake ✅ · `GET /specs/{id}` = Umra TODO |
| `updateJobSpec(jobId, patch)` | `PUT /job/:id` | edit client-side, then persist the whole spec with `POST /specs` | `POST /specs` ✅ built |
| `confirmJobSpec(jobId)` | `POST /job/:id/confirm` → `{started}` | `POST /specs` (spec) → `{spec_id}`, then `PATCH /specs/{spec_id}/confirm`, then the orchestrator starts the calls | `POST /specs` ✅ · confirm + call-start = Umra TODO |
| `getNegotiationProgress(jobId)` | `GET /job/:id/negotiation` | `GET /calls?spec_id={spec_id}` (poll ~5s) **or** Supabase Realtime on `calls` + `quotes` | Umra TODO · Realtime **live now** |
| `getQuoteReport(jobId)` | `GET /job/:id/report` | `GET /report/{spec_id}` | Umra TODO |
| `getCompanyDetail(jobId, cid)` | `GET /job/:id/company/:cid` | derive from the report, or a single-call fetch | Umra TODO |
| `getCallTranscript(jobId, cid)` | `GET /job/:id/company/:cid/transcript` returning `lines[]` | backend stores a **`transcript_url`** on the call (a link, not line-by-line JSON) — shape needs a team decision | Umra TODO |

**Honest status:** the **intake half** (`/intake/doc`, `/specs`) is real and callable today. The **calls/report half** (progress, report, company, transcript) is still Umra's TODO — the frontend can't wire those until she builds them, so keep those functions on mocks for now.

## Type map (`lib/types.ts`)

### `JobSpec` — replace the flat shape with the real nested one
```ts
// what the backend returns / accepts (snake_case, nested):
interface JobSpec {
  property: {
    type: "apartment" | "house" | "condo" | "townhouse" | "other" | null;
    sqft: number | null;
    bedrooms: number | null;
    bathrooms: number | null;
    levels: number | null;
  };
  clean_type: "standard" | "deep" | "move_out" | null;
  frequency: "one_time" | "weekly" | "biweekly" | "monthly" | null;
  condition: {
    clutter_level: "light" | "moderate" | "heavy" | null;
    pets: boolean | null;
    weeks_since_last_clean: number | null;
  };
  add_ons: { fridge: boolean; oven: boolean; windows: boolean; baseboards: boolean; laundry: boolean };
  access: { parking: string | null; entry: string | null; walk_up_floor: number | null };
  schedule: { preferred_date: string | null; flexibility_days: number | null; time_window: string | null };
  notes: string | null;
  confirmed_by_user: boolean;
  intake_source: "document" | "voice_interview" | "both" | null;
}
```
Field-by-field from the old shape:
| Old (flat) | New |
|---|---|
| `jobId` | `spec_id` (returned by `POST /specs`, kept alongside the spec in app state) |
| `status` (JobStatus enum) | keep as **client-only** UI state — the backend doesn't return it. `missing_fields` (string[]) tells you if the spec is ready. |
| `cleaningType` (`"Deep Cleaning"`) | `clean_type` (`"deep"`) — note enum values, not display strings |
| `houseSizeSqft` | `property.sqft` |
| `bedrooms` / `bathrooms` | `property.bedrooms` / `property.bathrooms` |
| `furniture[]` | **drop** — cleaning has no furniture inventory. The new spec captures scope via `clean_type` + `add_ons` + `condition`. |
| `specialNotes` | `notes` |
| `sourceFileName` | keep client-only (not stored server-side; `intake_source` says which path produced it) |
| — (new to add to the Review form) | `property.type`, `property.levels`, `frequency`, `condition.*`, `add_ons.*`, `access.*`, `schedule.*` — these are the fields the "confirm" gate should show. |

### `CompanyCall` — a `calls` row joined with its `quotes`/`quote_items`
| Frontend field | Backend source |
|---|---|
| `companyId` / `companyName` / `phone` | `companies.id` / `.name` / `.phone` |
| `status` (`waiting/calling/completed/declined/failed`) | `calls.status` → map **`waiting`→`queued`, `completed`→`done`**; `calling`/`declined` match; `failed` has no backend equivalent (keep client-side) |
| `price` | `quotes.final_total` |
| `travelFee` (`included/extra`) | not a field — derive from a trip/travel line in `quote_items`, or simplify away |
| `extraCharges[]` | the `quote_items` labels (itemized lines) |
| `callOutcome` | `quotes.outcome` (**`quote/callback/declined`** — the locked vocab) + `quotes.notes` |
| `redFlag` | `quotes.red_flags.length > 0` |
| `startedAt` / `completedAt` | `calls.created_at` / `calls.updated_at` |

### `QuoteReport` — `GET /report/{spec_id}`
`jobId`→`spec_id`; `bestQuote`→the recommended deal (lowest **non-flagged** `final_total`); `warnings[]`→aggregated `red_flags`. Otherwise as-is.

## Live now, for the call board
The DB (`the-negotiator` Supabase project) already has **Realtime** on `calls`, `quotes`, `quote_items`, and read-only anon access. The frontend can subscribe with `supabase-js` (anon/publishable key) filtered by `spec_id` instead of polling — the socket stub at the bottom of `api.ts` is where that plugs in. (v4 plan is fine with plain polling too; either works.)

## Team decisions to close
1. **Transcript shape** — backend stores a `transcript_url`. Does the report render from that URL, or should the backend also return `lines[]` per call? (Frontend wants `lines[]`.)
2. **travelFee / extraCharges** — keep the frontend's summarized shape and have the backend compute it, or have the frontend render raw `quote_items`?
3. **Progress transport** — Supabase Realtime (live now) vs `GET /calls?spec_id` polling (Umra to build).

Nothing here changes a component — it's all `lib/types.ts` + `lib/api.ts`.
