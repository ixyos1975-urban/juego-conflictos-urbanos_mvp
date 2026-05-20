-- Persistencia minima para la sala de discusion.
-- Ejecutar en Supabase SQL editor antes de usar la sala persistente.

create table if not exists public.discussion_threads (
  id uuid primary key default gen_random_uuid(),
  case_slug text not null,
  case_id uuid,
  title text not null,
  thread_type text not null,
  description text,
  sort_order integer not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  constraint discussion_threads_case_title_unique unique (case_slug, title)
);

create table if not exists public.discussion_posts (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid not null references public.discussion_threads(id) on delete cascade,
  case_slug text not null,
  user_email text not null,
  author_display_name text not null,
  role_label text,
  role_id uuid,
  intervention_type text not null,
  content text not null,
  parent_id uuid references public.discussion_posts(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists discussion_threads_case_slug_idx
  on public.discussion_threads (case_slug);

create index if not exists discussion_posts_thread_id_idx
  on public.discussion_posts (thread_id);

create index if not exists discussion_posts_case_slug_idx
  on public.discussion_posts (case_slug);

create index if not exists discussion_posts_user_email_idx
  on public.discussion_posts (user_email);

insert into public.discussion_threads (
  case_slug,
  title,
  thread_type,
  description,
  sort_order
)
values
  (
    'caso-borde-barrial',
    'Cumplimiento normativo del proyecto',
    'normativo',
    'Discusion sobre alcance normativo, licencias, cargas y condiciones del proyecto.',
    1
  ),
  (
    'caso-borde-barrial',
    'Impactos sociales y permanencia barrial',
    'social',
    'Discusion sobre permanencia, tejido social, desplazamiento y afectaciones a la comunidad.',
    2
  ),
  (
    'caso-borde-barrial',
    'Viabilidad y negociacion entre actores',
    'negociacion',
    'Discusion sobre acuerdos, compensaciones, ajustes o rutas de negociacion posibles.',
    3
  )
on conflict (case_slug, title) do update
set
  thread_type = excluded.thread_type,
  description = excluded.description,
  sort_order = excluded.sort_order,
  is_active = true;
