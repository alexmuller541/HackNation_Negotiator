-- The Negotiator — live Supabase schema (cleaning vertical).
-- This is the schema currently used by backend/database.py. It uses a JSONB
-- job spec so both document and voice intake share one canonical payload.
create extension if not exists pgcrypto;

create table if not exists public.specs (
  id uuid primary key default gen_random_uuid(),
  spec jsonb not null,
  clean_type text,
  intake_source text,
  confirmed_by_user boolean not null default false,
  missing_fields text[] not null default '{}',
  created_at timestamptz not null default now()
);
create table if not exists public.companies (
  id uuid primary key default gen_random_uuid(), name text not null,
  persona text, phone text, created_at timestamptz not null default now()
);
create table if not exists public.calls (
  id uuid primary key default gen_random_uuid(), spec_id uuid not null references public.specs(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade, round integer not null default 1,
  status text not null default 'queued', transcript_url text, recording_url text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.quotes (
  id uuid primary key default gen_random_uuid(), call_id uuid not null references public.calls(id) on delete cascade,
  spec_id uuid references public.specs(id) on delete cascade, company_id uuid references public.companies(id),
  outcome text not null, initial_total numeric, final_total numeric, pricing_model text, binding boolean,
  conditions text[] not null default '{}', callback_contact text, callback_window text,
  red_flags text[] not null default '{}', notes text, created_at timestamptz not null default now()
);
create table if not exists public.quote_items (
  id uuid primary key default gen_random_uuid(), call_id uuid not null references public.calls(id) on delete cascade,
  label text not null, amount numeric not null, disclosed_voluntarily boolean, negotiable boolean,
  created_at timestamptz not null default now()
);
create index if not exists calls_spec_id_idx on public.calls(spec_id);
create index if not exists quotes_spec_id_idx on public.quotes(spec_id);
create index if not exists quote_items_call_id_idx on public.quote_items(call_id);
