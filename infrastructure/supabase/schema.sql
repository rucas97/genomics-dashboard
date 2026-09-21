create extension if not exists "uuid-ossp";

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text, full_name text,
  role text default 'viewer' check (role in ('admin','analyst','viewer')),
  org_id uuid, created_at timestamptz default now()
);

create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email) values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

create table if not exists public.projects (
  id uuid primary key default uuid_generate_v4(),
  name text not null, description text, org_id uuid,
  created_by uuid references auth.users(id),
  created_at timestamptz default now()
);

create table if not exists public.samples (
  id uuid primary key default uuid_generate_v4(),
  project_id uuid references public.projects(id) on delete cascade,
  name text not null, species text default 'Homo sapiens',
  reference_genome text default 'GRCh38',
  file_path text, file_type text, file_size_bytes bigint,
  status text default 'uploaded' check (status in ('uploaded','processing','ready','failed')),
  metadata jsonb default '{}',
  created_by uuid references auth.users(id),
  created_at timestamptz default now()
);
create index if not exists idx_samples_project on public.samples(project_id);
create index if not exists idx_samples_status on public.samples(status);

create table if not exists public.qc_metrics (
  id uuid primary key default uuid_generate_v4(),
  sample_id uuid references public.samples(id) on delete cascade,
  total_reads bigint, mapped_reads bigint, mean_coverage numeric,
  duplication_rate numeric, contamination_rate numeric, q30_rate numeric,
  gc_content numeric, variant_count integer, snp_count integer, indel_count integer,
  computed_at timestamptz default now()
);
create index if not exists idx_qc_sample on public.qc_metrics(sample_id);

create table if not exists public.variants (
  id uuid primary key default uuid_generate_v4(),
  sample_id uuid references public.samples(id) on delete cascade,
  chrom text not null, pos bigint not null, ref text, alt text,
  qual numeric, filter text, genotype text, depth integer,
  gene text, consequence text, impact text,
  clinvar_significance text, gnomad_af numeric, rsid text,
  created_at timestamptz default now()
);
create index if not exists idx_var_sample on public.variants(sample_id);
create index if not exists idx_var_pos on public.variants(chrom, pos);
create index if not exists idx_var_gene on public.variants(gene);
create index if not exists idx_var_clinvar on public.variants(clinvar_significance);

create table if not exists public.cohorts (
  id uuid primary key default uuid_generate_v4(),
  project_id uuid references public.projects(id) on delete cascade,
  name text not null, description text, sample_ids uuid[] default '{}',
  created_by uuid references auth.users(id),
  created_at timestamptz default now()
);

create table if not exists public.pipeline_runs (
  id uuid primary key default uuid_generate_v4(),
  sample_id uuid references public.samples(id) on delete cascade,
  pipeline_name text not null,
  status text default 'queued' check (status in ('queued','running','completed','failed')),
  logs text, started_at timestamptz, finished_at timestamptz,
  created_by uuid references auth.users(id),
  created_at timestamptz default now()
);
create index if not exists idx_runs_sample on public.pipeline_runs(sample_id);
create index if not exists idx_runs_status on public.pipeline_runs(status);

create table if not exists public.reports (
  id uuid primary key default uuid_generate_v4(),
  project_id uuid references public.projects(id) on delete cascade,
  sample_id uuid references public.samples(id),
  title text not null,
  type text default 'sample' check (type in ('sample','cohort','qc')),
  file_path text, created_by uuid references auth.users(id),
  created_at timestamptz default now()
);

create table if not exists public.audit_log (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id),
  action text not null, resource_type text, resource_id uuid,
  details jsonb default '{}', ip_address text,
  created_at timestamptz default now()
);
create index if not exists idx_audit_user on public.audit_log(user_id);
create index if not exists idx_audit_created on public.audit_log(created_at desc);

alter table public.profiles enable row level security;
alter table public.projects enable row level security;
alter table public.samples enable row level security;
alter table public.qc_metrics enable row level security;
alter table public.variants enable row level security;
alter table public.cohorts enable row level security;
alter table public.pipeline_runs enable row level security;
alter table public.reports enable row level security;
alter table public.audit_log enable row level security;

drop policy if exists "own profile" on public.profiles;
create policy "own profile" on public.profiles for all using (auth.uid() = id);
drop policy if exists "auth read samples" on public.samples;
create policy "auth read samples" on public.samples for select using (auth.role() = 'authenticated');
drop policy if exists "auth write samples" on public.samples;
create policy "auth write samples" on public.samples for insert with check (auth.role() = 'authenticated');
drop policy if exists "auth read qc" on public.qc_metrics;
create policy "auth read qc" on public.qc_metrics for select using (auth.role() = 'authenticated');
drop policy if exists "auth write qc" on public.qc_metrics;
create policy "auth write qc" on public.qc_metrics for insert with check (auth.role() = 'authenticated');
drop policy if exists "auth read variants" on public.variants;
create policy "auth read variants" on public.variants for select using (auth.role() = 'authenticated');
drop policy if exists "auth write variants" on public.variants;
create policy "auth write variants" on public.variants for insert with check (auth.role() = 'authenticated');
drop policy if exists "auth all cohorts" on public.cohorts;
create policy "auth all cohorts" on public.cohorts for all using (auth.role() = 'authenticated');
drop policy if exists "auth all runs" on public.pipeline_runs;
create policy "auth all runs" on public.pipeline_runs for all using (auth.role() = 'authenticated');
drop policy if exists "auth all reports" on public.reports;
create policy "auth all reports" on public.reports for all using (auth.role() = 'authenticated');
drop policy if exists "auth read audit" on public.audit_log;
create policy "auth read audit" on public.audit_log for select using (auth.role() = 'authenticated');
drop policy if exists "auth insert audit" on public.audit_log;
create policy "auth insert audit" on public.audit_log for insert with check (auth.role() = 'authenticated');

insert into storage.buckets (id, name, public)
values ('genomic-files', 'genomic-files', false)
on conflict (id) do nothing;

drop policy if exists "auth upload genomic" on storage.objects;
create policy "auth upload genomic" on storage.objects for insert
  with check (bucket_id = 'genomic-files' and auth.role() = 'authenticated');
drop policy if exists "auth read genomic" on storage.objects;
create policy "auth read genomic" on storage.objects for select
  using (bucket_id = 'genomic-files' and auth.role() = 'authenticated');
