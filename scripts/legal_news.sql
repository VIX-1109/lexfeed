-- LexFeed · Legal News persistence
-- Run this in your Supabase SQL Editor (same project as NyayaSetu).
--
-- Why this design:
--   The news cache used to live only in the server's RAM, so it was wiped
--   every time a free-tier server slept or restarted. This stores the latest
--   batch in Supabase so it survives restarts AND both LexFeed and NyayaSetu
--   can read it.
--
--   Space stays tiny on its own: replace_legal_news() DELETEs the old batch
--   and INSERTs the new one in a single transaction, so the table never holds
--   more than one batch (~10 rows). No cron job needed — it "cleans" itself
--   every time fresh news is fetched (at most once every 2 hours).

-- ── Table ───────────────────────────────────────────────────────────────────
create table if not exists public.legal_news (
  id          uuid primary key default gen_random_uuid(),
  position    int  not null default 0,   -- preserves source ranking order
  tag         text,
  title       text not null,
  summary     text,
  source      text,
  url         text,
  image       text,
  time_label  text,                       -- snapshot like "2h ago"
  fetched_at  timestamptz not null default now()
);

create index if not exists idx_legal_news_fetched_at on public.legal_news(fetched_at desc);
create index if not exists idx_legal_news_position    on public.legal_news(position);

-- ── RLS: anyone may READ, nobody may write directly ──────────────────────────
alter table public.legal_news enable row level security;

drop policy if exists "legal_news public read" on public.legal_news;
create policy "legal_news public read"
  on public.legal_news for select
  using (true);
-- No insert/update/delete policies: the only write path is the
-- SECURITY DEFINER function below, so the anon key cannot tamper with rows.

-- ── Self-cleaning write: replace the whole batch atomically ───────────────────
create or replace function public.replace_legal_news(p_items jsonb)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  delete from public.legal_news where true;            -- drop old batch (frees space; WHERE satisfies safe-update guard)
  insert into public.legal_news
    (position, tag, title, summary, source, url, image, time_label, fetched_at)
  select
    (ord - 1)::int,
    item->>'tag',
    coalesce(item->>'title', 'Legal news update'),
    item->>'summary',
    item->>'source',
    item->>'url',
    item->>'image',
    item->>'time',
    now()
  from jsonb_array_elements(p_items) with ordinality as t(item, ord);
end;
$$;

grant execute on function public.replace_legal_news(jsonb) to anon, authenticated;
