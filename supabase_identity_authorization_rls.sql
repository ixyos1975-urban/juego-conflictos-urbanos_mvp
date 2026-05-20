-- Hardening de nucleo de identidad/autorizacion.
-- Tablas:
-- - public.allowed_users
-- - public.profiles
-- - public.role_assignments
--
-- Contexto:
-- - La app usa cliente Supabase anon.
-- - La identidad vive en Streamlit/session_state, no en auth.uid().
-- - Por eso se bloquea acceso directo anon y se expone una capa RPC
--   security definer para lecturas puntuales de identidad/autorizacion.

alter table public.allowed_users enable row level security;
alter table public.profiles enable row level security;
alter table public.role_assignments enable row level security;

drop policy if exists "Anon can read allowed users directly" on public.allowed_users;
drop policy if exists "Anon can insert allowed users directly" on public.allowed_users;
drop policy if exists "Anon can update allowed users directly" on public.allowed_users;
drop policy if exists "Anon can delete allowed users directly" on public.allowed_users;

drop policy if exists "Anon can read profiles directly" on public.profiles;
drop policy if exists "Anon can insert profiles directly" on public.profiles;
drop policy if exists "Anon can update profiles directly" on public.profiles;
drop policy if exists "Anon can delete profiles directly" on public.profiles;

drop policy if exists "Anon can read role assignments directly" on public.role_assignments;
drop policy if exists "Anon can insert role assignments directly" on public.role_assignments;
drop policy if exists "Anon can update role assignments directly" on public.role_assignments;
drop policy if exists "Anon can delete role assignments directly" on public.role_assignments;

create or replace function public.get_allowed_user_by_email_secure(
    p_email text
)
returns setof public.allowed_users
language sql
security definer
set search_path = public
as $$
    select au.*
    from public.allowed_users au
    where lower(au.email) = lower(trim(p_email))
    limit 1;
$$;

create or replace function public.is_active_admin_by_email_secure(
    p_email text
)
returns boolean
language sql
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.allowed_users au
        where lower(au.email) = lower(trim(p_email))
          and coalesce(au.is_active, true) = true
          and au.is_admin = true
    );
$$;

create or replace function public.get_profile_by_email_secure(
    p_email text
)
returns setof public.profiles
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1
        from public.allowed_users au
        where lower(au.email) = lower(trim(p_email))
          and coalesce(au.is_active, true) = true
    ) then
        raise exception 'Usuario no autorizado para consultar perfil.';
    end if;

    return query
    select p.*
    from public.profiles p
    where lower(p.email) = lower(trim(p_email))
    limit 1;
end;
$$;

create or replace function public.get_role_assignment_for_user_case_secure(
    p_profile_id uuid,
    p_case_id uuid
)
returns setof public.role_assignments
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1
        from public.profiles p
        where p.id = p_profile_id
    ) then
        raise exception 'Perfil no valido para consultar asignacion.';
    end if;

    if not exists (
        select 1
        from public.cases c
        where c.id = p_case_id
    ) then
        raise exception 'Caso no valido para consultar asignacion.';
    end if;

    return query
    select ra.*
    from public.role_assignments ra
    where ra.user_id = p_profile_id
      and ra.case_id = p_case_id
    limit 1;
end;
$$;

create or replace function public.get_students_with_roles_for_case_secure(
    p_case_id uuid
)
returns table (
    profile_id uuid,
    role_id uuid,
    assignment_id uuid,
    name text,
    email text,
    role text
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1
        from public.cases c
        where c.id = p_case_id
    ) then
        raise exception 'Caso no valido para consultar estudiantes.';
    end if;

    return query
    select
        ra.user_id as profile_id,
        ra.role_id,
        ra.id as assignment_id,
        coalesce(
            to_jsonb(p)->>'full_name',
            to_jsonb(p)->>'name',
            to_jsonb(p)->>'display_name',
            to_jsonb(p)->>'email',
            'Estudiante sin nombre'
        )::text as name,
        coalesce(to_jsonb(p)->>'email', '')::text as email,
        coalesce(
            to_jsonb(r)->>'name',
            to_jsonb(r)->>'title',
            to_jsonb(r)->>'role_name',
            'Rol asignado'
        )::text as role
    from public.role_assignments ra
    left join public.profiles p on p.id = ra.user_id
    left join public.roles r on r.id = ra.role_id
    where ra.case_id = p_case_id
    order by name;
end;
$$;

create or replace function public.get_interventions_for_teacher_review_secure(
    p_case_id uuid,
    p_student_profile_id uuid default null
)
returns table (
    id uuid,
    case_id uuid,
    thread_id uuid,
    author_id uuid,
    role_id uuid,
    parent_intervention_id uuid,
    intervention_type text,
    title text,
    content text,
    phase text,
    is_visible boolean,
    review_status text,
    created_at timestamptz,
    updated_at timestamptz,
    author_name text,
    role_name text,
    thread_title text
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1
        from public.cases c
        where c.id = p_case_id
    ) then
        raise exception 'Caso no valido para consultar intervenciones.';
    end if;

    if p_student_profile_id is not null
       and not exists (
           select 1
           from public.profiles p
           where p.id = p_student_profile_id
       ) then
        raise exception 'Perfil no valido para filtrar intervenciones.';
    end if;

    return query
    select
        i.id,
        i.case_id,
        i.thread_id,
        i.author_id,
        i.role_id,
        i.parent_intervention_id,
        i.intervention_type,
        i.title,
        i.content,
        i.phase,
        i.is_visible,
        i.review_status,
        i.created_at,
        i.updated_at,
        coalesce(
            to_jsonb(p)->>'full_name',
            to_jsonb(p)->>'name',
            to_jsonb(p)->>'display_name',
            to_jsonb(p)->>'email',
            'Estudiante'
        )::text as author_name,
        coalesce(
            to_jsonb(r)->>'name',
            to_jsonb(r)->>'title',
            to_jsonb(r)->>'role_name',
            'Rol asignado'
        )::text as role_name,
        coalesce(dt.title, 'Hilo sin titulo')::text as thread_title
    from public.interventions i
    left join public.profiles p on p.id = i.author_id
    left join public.roles r on r.id = i.role_id
    left join public.discussion_threads dt on dt.id = i.thread_id
    where i.case_id = p_case_id
      and i.is_visible = true
      and (
          p_student_profile_id is null
          or i.author_id = p_student_profile_id
      )
    order by i.created_at desc;
end;
$$;

revoke all on function public.get_allowed_user_by_email_secure(text) from public;
revoke all on function public.is_active_admin_by_email_secure(text) from public;
revoke all on function public.get_profile_by_email_secure(text) from public;
revoke all on function public.get_role_assignment_for_user_case_secure(uuid, uuid) from public;
revoke all on function public.get_students_with_roles_for_case_secure(uuid) from public;
revoke all on function public.get_interventions_for_teacher_review_secure(uuid, uuid) from public;

grant execute on function public.get_allowed_user_by_email_secure(text) to anon;
grant execute on function public.is_active_admin_by_email_secure(text) to anon;
grant execute on function public.get_profile_by_email_secure(text) to anon;
grant execute on function public.get_role_assignment_for_user_case_secure(uuid, uuid) to anon;
grant execute on function public.get_students_with_roles_for_case_secure(uuid) to anon;
grant execute on function public.get_interventions_for_teacher_review_secure(uuid, uuid) to anon;
