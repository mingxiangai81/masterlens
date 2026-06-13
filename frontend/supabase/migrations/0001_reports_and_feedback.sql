-- Ensure the `reports` table exists with the columns needed for report history
create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  ticker text not null,
  report_json jsonb,
  created_at timestamptz not null default now()
);

do $$
begin
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='reports' and column_name='user_id') then
    alter table public.reports add column user_id uuid references auth.users(id) on delete cascade;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='reports' and column_name='report_json') then
    alter table public.reports add column report_json jsonb;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='reports' and column_name='created_at') then
    alter table public.reports add column created_at timestamptz not null default now();
  end if;
end $$;

alter table public.reports enable row level security;

drop policy if exists "Users can view own reports" on public.reports;
create policy "Users can view own reports" on public.reports
  for select using (auth.uid() = user_id);

drop policy if exists "Users can insert own reports" on public.reports;
create policy "Users can insert own reports" on public.reports
  for insert with check (auth.uid() = user_id);

-- Feedback table for the /feedback page
create table if not exists public.feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  rating int not null,
  category text,
  message text not null,
  email text,
  language text,
  created_at timestamptz not null default now()
);

alter table public.feedback enable row level security;

drop policy if exists "Anyone can submit feedback" on public.feedback;
create policy "Anyone can submit feedback" on public.feedback
  for insert with check (true);

drop policy if exists "Users can view own feedback" on public.feedback;
create policy "Users can view own feedback" on public.feedback
  for select using (auth.uid() = user_id);
