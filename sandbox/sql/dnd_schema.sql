-- Run in Supabase SQL Editor (Postgres)
-- Note: Supabase uses Postgres, not MySQL.

create extension if not exists pgcrypto;

create table if not exists public.campaigns (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  join_code text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists public.characters (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  player_name text not null,
  name text not null,
  archetype text not null,
  max_hp int not null,
  hp int not null,
  strength int not null,
  agility int not null,
  arcana int not null,
  notes text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.map_assets (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  uploaded_by text not null,
  filename text not null,
  mime_type text not null,
  storage_path text not null,
  public_url text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.turns (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  character_id uuid not null references public.characters(id) on delete cascade,
  action text not null,
  dice_roll int not null check (dice_roll between 1 and 20),
  total_roll int not null,
  effect_hp_delta int not null default 0,
  narration text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.story_ideas (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  submitted_by text not null,
  title text not null,
  idea_text text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.session_briefs (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  prepared_by text not null,
  brief_text text not null,
  created_at timestamptz not null default now()
);

alter table public.characters add column if not exists max_hp int;
alter table public.turns add column if not exists total_roll int;
alter table public.turns add column if not exists effect_hp_delta int not null default 0;
alter table public.map_assets add column if not exists storage_path text;
alter table public.map_assets add column if not exists public_url text;
update public.characters set max_hp = hp where max_hp is null;
alter table public.characters alter column max_hp set not null;
update public.turns set total_roll = dice_roll where total_roll is null;
alter table public.turns alter column total_roll set not null;

create index if not exists idx_characters_campaign_id on public.characters(campaign_id);
create index if not exists idx_maps_campaign_id on public.map_assets(campaign_id);
create index if not exists idx_turns_campaign_id on public.turns(campaign_id);
create index if not exists idx_turns_character_id on public.turns(character_id);
create index if not exists idx_story_ideas_campaign_id on public.story_ideas(campaign_id);
create index if not exists idx_session_briefs_campaign_id on public.session_briefs(campaign_id);

alter table public.campaigns enable row level security;
alter table public.characters enable row level security;
alter table public.map_assets enable row level security;
alter table public.turns enable row level security;
alter table public.story_ideas enable row level security;
alter table public.session_briefs enable row level security;

-- Development-open policies for rapid prototyping.
-- Tighten these before production by adding auth-based ownership rules.
drop policy if exists "campaigns_read_all" on public.campaigns;
create policy "campaigns_read_all" on public.campaigns for select using (true);
drop policy if exists "campaigns_write_all" on public.campaigns;
create policy "campaigns_write_all" on public.campaigns for insert with check (true);

drop policy if exists "characters_read_all" on public.characters;
create policy "characters_read_all" on public.characters for select using (true);
drop policy if exists "characters_write_all" on public.characters;
create policy "characters_write_all" on public.characters for insert with check (true);

drop policy if exists "maps_read_all" on public.map_assets;
create policy "maps_read_all" on public.map_assets for select using (true);
drop policy if exists "maps_write_all" on public.map_assets;
create policy "maps_write_all" on public.map_assets for insert with check (true);

drop policy if exists "turns_read_all" on public.turns;
create policy "turns_read_all" on public.turns for select using (true);
drop policy if exists "turns_write_all" on public.turns;
create policy "turns_write_all" on public.turns for insert with check (true);

drop policy if exists "story_ideas_read_all" on public.story_ideas;
create policy "story_ideas_read_all" on public.story_ideas for select using (true);
drop policy if exists "story_ideas_write_all" on public.story_ideas;
create policy "story_ideas_write_all" on public.story_ideas for insert with check (true);

drop policy if exists "session_briefs_read_all" on public.session_briefs;
create policy "session_briefs_read_all" on public.session_briefs for select using (true);
drop policy if exists "session_briefs_write_all" on public.session_briefs;
create policy "session_briefs_write_all" on public.session_briefs for insert with check (true);

-- One-time bucket setup for map uploads.
-- Run once if bucket doesn't exist:
insert into storage.buckets (id, name, public)
values ('dnd-maps', 'dnd-maps', true)
on conflict (id) do nothing;
