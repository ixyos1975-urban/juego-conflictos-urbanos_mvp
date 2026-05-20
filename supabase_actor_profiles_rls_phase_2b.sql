-- Fase 2B de endurecimiento RLS: public.actor_profiles.
-- Objetivo:
-- - Activar RLS en actor_profiles.
-- - No crear politicas de select/insert/update directo para anon.
-- - Exponer solo RPC security definer con validacion minima de identidad tecnica.
--
-- Validacion minima aplicada en RPC:
-- - public.allowed_users.email = p_user_email and is_active = true existe.
-- - public.cases.slug = p_case_slug existe.
-- - public.profiles.email = p_user_email existe.
-- - public.role_assignments.user_id = profiles.id y case_id = cases.id existe.
--
-- Importante:
-- - La app sigue usando cliente Supabase anon.
-- - La identidad real sigue viviendo en Streamlit/session_state.
-- - Esta fase no toca interventions, evidences, teacher_reviews, ai_reviews
--   ni case_ranking.

alter table public.actor_profiles enable row level security;

drop policy if exists "Anon can read actor profiles directly" on public.actor_profiles;
drop policy if exists "Anon can insert actor profiles directly" on public.actor_profiles;
drop policy if exists "Anon can update actor profiles directly" on public.actor_profiles;
drop policy if exists "Anon can delete actor profiles directly" on public.actor_profiles;

create or replace function public.get_actor_profile_secure(
    p_user_email text,
    p_case_slug text
)
returns table (
    id uuid,
    user_email text,
    case_slug text,
    allowed_user_id uuid,
    case_id uuid,
    role_id uuid,
    display_name text,
    avatar_url text,
    public_presentation text,
    initial_position text,
    main_interest text,
    non_negotiable_point text,
    action_line text,
    created_at timestamptz,
    updated_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_user_email text := lower(trim(p_user_email));
    v_case_slug text := trim(p_case_slug);
    v_profile_id uuid;
    v_case_id uuid;
begin
    if not exists (
        select 1
        from public.allowed_users au
        where lower(au.email) = v_user_email
          and coalesce(au.is_active, true) = true
    ) then
        raise exception 'Usuario no autorizado para consultar perfil publico.';
    end if;

    select p.id
    into v_profile_id
    from public.profiles p
    where lower(p.email) = v_user_email
    limit 1;

    if v_profile_id is null then
        raise exception 'Perfil tecnico no encontrado para consultar perfil publico.';
    end if;

    select c.id
    into v_case_id
    from public.cases c
    where c.slug = v_case_slug
    limit 1;

    if v_case_id is null then
        raise exception 'Caso no encontrado para consultar perfil publico.';
    end if;

    if not exists (
        select 1
        from public.role_assignments ra
        where ra.user_id = v_profile_id
          and ra.case_id = v_case_id
    ) then
        raise exception 'El perfil no tiene asignacion activa para este caso.';
    end if;

    return query
    select
        ap.id,
        ap.user_email,
        ap.case_slug,
        ap.allowed_user_id,
        ap.case_id,
        ap.role_id,
        ap.display_name,
        ap.avatar_url,
        ap.public_presentation,
        ap.initial_position,
        ap.main_interest,
        ap.non_negotiable_point,
        ap.action_line,
        ap.created_at,
        ap.updated_at
    from public.actor_profiles ap
    where lower(ap.user_email) = v_user_email
      and ap.case_slug = v_case_slug
    limit 1;
end;
$$;

create or replace function public.upsert_actor_profile_secure(
    p_user_email text,
    p_case_slug text,
    p_display_name text,
    p_avatar_url text,
    p_public_presentation text,
    p_initial_position text,
    p_main_interest text,
    p_non_negotiable_point text,
    p_action_line text
)
returns table (
    id uuid,
    user_email text,
    case_slug text,
    allowed_user_id uuid,
    case_id uuid,
    role_id uuid,
    display_name text,
    avatar_url text,
    public_presentation text,
    initial_position text,
    main_interest text,
    non_negotiable_point text,
    action_line text,
    created_at timestamptz,
    updated_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_user_email text := lower(trim(p_user_email));
    v_case_slug text := trim(p_case_slug);
    v_allowed_user_id uuid;
    v_profile_id uuid;
    v_case_id uuid;
    v_role_id uuid;
begin
    select au.id
    into v_allowed_user_id
    from public.allowed_users au
    where lower(au.email) = v_user_email
      and coalesce(au.is_active, true) = true
    limit 1;

    if v_allowed_user_id is null then
        raise exception 'Usuario no autorizado para guardar perfil publico.';
    end if;

    select p.id
    into v_profile_id
    from public.profiles p
    where lower(p.email) = v_user_email
    limit 1;

    if v_profile_id is null then
        raise exception 'Perfil tecnico no encontrado para guardar perfil publico.';
    end if;

    select c.id
    into v_case_id
    from public.cases c
    where c.slug = v_case_slug
    limit 1;

    if v_case_id is null then
        raise exception 'Caso no encontrado para guardar perfil publico.';
    end if;

    select ra.role_id
    into v_role_id
    from public.role_assignments ra
    where ra.user_id = v_profile_id
      and ra.case_id = v_case_id
    limit 1;

    if v_role_id is null then
        raise exception 'El perfil no tiene asignacion activa para este caso.';
    end if;

    return query
    with saved as (
        insert into public.actor_profiles (
            user_email,
            case_slug,
            allowed_user_id,
            case_id,
            role_id,
            display_name,
            avatar_url,
            public_presentation,
            initial_position,
            main_interest,
            non_negotiable_point,
            action_line,
            updated_at
        )
        values (
            v_user_email,
            v_case_slug,
            v_allowed_user_id,
            v_case_id,
            v_role_id,
            coalesce(trim(p_display_name), ''),
            nullif(trim(coalesce(p_avatar_url, '')), ''),
            coalesce(trim(p_public_presentation), ''),
            coalesce(trim(p_initial_position), ''),
            coalesce(trim(p_main_interest), ''),
            coalesce(trim(p_non_negotiable_point), ''),
            coalesce(trim(p_action_line), ''),
            now()
        )
        on conflict (user_email, case_slug)
        do update set
            allowed_user_id = excluded.allowed_user_id,
            case_id = excluded.case_id,
            role_id = excluded.role_id,
            display_name = excluded.display_name,
            avatar_url = excluded.avatar_url,
            public_presentation = excluded.public_presentation,
            initial_position = excluded.initial_position,
            main_interest = excluded.main_interest,
            non_negotiable_point = excluded.non_negotiable_point,
            action_line = excluded.action_line,
            updated_at = now()
        returning *
    )
    select
        saved.id,
        saved.user_email,
        saved.case_slug,
        saved.allowed_user_id,
        saved.case_id,
        saved.role_id,
        saved.display_name,
        saved.avatar_url,
        saved.public_presentation,
        saved.initial_position,
        saved.main_interest,
        saved.non_negotiable_point,
        saved.action_line,
        saved.created_at,
        saved.updated_at
    from saved;
end;
$$;

revoke all on function public.get_actor_profile_secure(text, text) from public;
revoke all on function public.upsert_actor_profile_secure(
    text,
    text,
    text,
    text,
    text,
    text,
    text,
    text,
    text
) from public;

grant execute on function public.get_actor_profile_secure(text, text) to anon;
grant execute on function public.upsert_actor_profile_secure(
    text,
    text,
    text,
    text,
    text,
    text,
    text,
    text,
    text
) to anon;
