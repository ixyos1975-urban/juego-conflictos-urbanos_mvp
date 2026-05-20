-- Tabla minima refinada para persistir el perfil publico del actor.
-- Clave operativa: un solo perfil por user_email + case_slug.
-- Las columnas *_id quedan preparadas para relaciones futuras y pueden ser null.
-- Ejecutar en Supabase SQL editor antes de usar la pantalla de perfil persistente.

create table if not exists public.actor_profiles (
  id uuid primary key default gen_random_uuid(),

  user_email text not null,
  case_slug text not null,

  allowed_user_id uuid,
  case_id uuid,
  role_id uuid,

  display_name text not null,
  avatar_url text,
  public_presentation text not null,
  initial_position text not null,
  main_interest text not null,
  non_negotiable_point text not null,
  action_line text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint actor_profiles_user_case_unique unique (user_email, case_slug)
);

alter table public.actor_profiles
  add column if not exists allowed_user_id uuid,
  add column if not exists case_id uuid,
  add column if not exists role_id uuid;

create index if not exists actor_profiles_user_email_idx
  on public.actor_profiles (user_email);

create index if not exists actor_profiles_case_slug_idx
  on public.actor_profiles (case_slug);

create or replace function public.set_actor_profiles_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_actor_profiles_updated_at
  on public.actor_profiles;

create trigger set_actor_profiles_updated_at
before update on public.actor_profiles
for each row
execute function public.set_actor_profiles_updated_at();

-- Politica de escritura esperada:
-- insert into public.actor_profiles (...)
-- values (...)
-- on conflict (user_email, case_slug) do update
-- set
--   allowed_user_id = excluded.allowed_user_id,
--   case_id = excluded.case_id,
--   role_id = excluded.role_id,
--   display_name = excluded.display_name,
--   avatar_url = excluded.avatar_url,
--   public_presentation = excluded.public_presentation,
--   initial_position = excluded.initial_position,
--   main_interest = excluded.main_interest,
--   non_negotiable_point = excluded.non_negotiable_point,
--   action_line = excluded.action_line;
-- El trigger actualiza updated_at = now() y created_at no se sobrescribe.
