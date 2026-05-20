-- Persistencia incremental del onboarding inicial del estudiante.
-- Ejecutar una sola vez en Supabase.

create table if not exists public.student_progress (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid not null references public.profiles(id) on delete cascade,
    case_id uuid not null references public.cases(id) on delete cascade,
    guide_completed boolean not null default false,
    case_context_completed boolean not null default false,
    role_preparation_completed boolean not null default false,
    public_actor_profile_completed boolean not null default false,
    updated_at timestamptz not null default now(),
    constraint student_progress_profile_case_unique unique (profile_id, case_id)
);

create index if not exists idx_student_progress_profile_id
    on public.student_progress(profile_id);

create index if not exists idx_student_progress_case_id
    on public.student_progress(case_id);

create or replace function public.set_student_progress_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists set_student_progress_updated_at on public.student_progress;

create trigger set_student_progress_updated_at
before update on public.student_progress
for each row
execute function public.set_student_progress_updated_at();
