-- The Negotiator — cleaning vertical — backend schema
-- Applied live to Supabase project: the-negotiator (ref: bhwtkatjwaduxbicdaur)
-- URL: https://bhwtkatjwaduxbicdaur.supabase.co  (region eu-west-1)
--
-- This file documents exactly what exists in the DB so it's reproducible and
-- reviewable. Writes go through the backend service-role key (bypasses RLS);
-- the frontend reads with the anon/publishable key (read-only policies below).

-- ── Core tables ────────────────────────────────────────────────────────────
-- 1. specs — confirmed job specs; both intake paths write here via /specs
create table if not exists public.specs (
  id                uuid primary key default gen_random_uuid(),
  spec              jsonb not null,
  clean_type        text,
  intake_source     text,               -- document | voice_interview | both
  confirmed_by_user boolean not null default false,
  missing_fields    text[] not null default '{}',
  created_at        timestamptz not null default now()
);

-- 2. companies — the three role-play cleaning companies (seeded below)
create table if not exists public.companies (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  persona    text,                       -- premium | lowballer | upseller
  phone      text,
  created_at timestamptz not null default now()
);

-- 3. calls — one call session per company per round (state machine)
create table if not exists public.calls (
  id             uuid primary key default gen_random_uuid(),
  spec_id        uuid not null references public.specs(id) on delete cascade,
  company_id     uuid not null references public.companies(id) on delete cascade,
  round          int not null default 1,          -- 1 = Caller, 2 = Closer
  status         text not null default 'queued',  -- queued | calling | done | declined
  transcript_url text,
  recording_url  text,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

-- 4. quotes — one structured outcome per call (log_outcome)
create table if not exists public.quotes (
  id               uuid primary key default gen_random_uuid(),
  call_id          uuid not null references public.calls(id) on delete cascade,
  spec_id          uuid references public.specs(id) on delete cascade,
  company_id       uuid references public.companies(id) on delete cascade,
  outcome          text not null,                 -- quote | callback | declined
  initial_total    numeric,
  final_total      numeric,
  pricing_model    text,                          -- flat | hourly | per_cleaner
  binding          boolean,
  conditions       text[] not null default '{}',
  callback_contact text,
  callback_window  text,
  red_flags        text[] not null default '{}',
  notes            text,
  created_at       timestamptz not null default now()
);

-- 5. quote_items — itemized lines (log_quote_item), streamed live during a call
create table if not exists public.quote_items (
  id                    uuid primary key default gen_random_uuid(),
  call_id               uuid not null references public.calls(id) on delete cascade,
  label                 text not null,
  amount                numeric not null,
  disclosed_voluntarily boolean,
  negotiable            boolean,
  created_at            timestamptz not null default now()
);

create index if not exists calls_spec_id_idx       on public.calls (spec_id);
create index if not exists quotes_spec_id_idx      on public.quotes (spec_id);
create index if not exists quotes_call_id_idx      on public.quotes (call_id);
create index if not exists quote_items_call_id_idx on public.quote_items (call_id);

-- ── RLS: read-only for anon (frontend); backend service-role bypasses RLS ────
alter table public.specs       enable row level security;
alter table public.companies   enable row level security;
alter table public.calls       enable row level security;
alter table public.quotes      enable row level security;
alter table public.quote_items enable row level security;

create policy "read specs"       on public.specs       for select using (true);
create policy "read companies"   on public.companies   for select using (true);
create policy "read calls"       on public.calls       for select using (true);
create policy "read quotes"      on public.quotes      for select using (true);
create policy "read quote_items" on public.quote_items for select using (true);

-- ── Realtime (live call board) ───────────────────────────────────────────────
alter publication supabase_realtime add table public.calls;
alter publication supabase_realtime add table public.quotes;
alter publication supabase_realtime add table public.quote_items;

-- ── Seed: the three role-play companies ──────────────────────────────────────
insert into public.companies (name, persona) values
  ('White Glove Home Cleaning', 'premium'),
  ('QuickBudget Cleaners', 'lowballer'),
  ('Fresh Start Cleaning Co', 'upseller')
on conflict do nothing;
