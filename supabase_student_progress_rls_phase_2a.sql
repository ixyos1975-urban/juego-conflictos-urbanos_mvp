-- Fase 2A de endurecimiento RLS: public.student_progress.
-- Objetivo:
-- - Activar RLS en student_progress.
-- - No crear politicas de insert/update directo para anon.
-- - Exponer solo RPC security definer con validacion minima de identidad tecnica.
--
-- Validacion minima aplicada en RPC:
-- - public.profiles.id = p_profile_id existe.
-- - public.role_assignments.user_id = p_profile_id y case_id = p_case_id existe.
--
-- Importante:
-- - La app sigue usando cliente Supabase anon.
-- - La identidad real sigue viviendo en Streamlit/session_state.
-- - Esta fase no toca actor_profiles, interventions, evidences, teacher_reviews,
--   ai_reviews ni case_ranking.

alter table public.student_progress enable row level security;

drop policy if exists "Anon can read student progress directly" on public.student_progress;
drop policy if exists "Anon can insert student progress directly" on public.student_progress;
drop policy if exists "Anon can update student progress directly" on public.student_progress;
drop policy if exists "Anon can delete student progress directly" on public.student_progress;

create or replace function public.get_student_progress_secure(
    p_profile_id uuid,
    p_case_id uuid
)
returns table (
    id uuid,
    profile_id uuid,
    case_id uuid,
    guide_completed boolean,
    case_context_completed boolean,
    role_preparation_completed boolean,
    public_actor_profile_completed boolean,
    updated_at timestamptz
)
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
        raise exception 'Perfil no valido para consultar progreso.';
    end if;

    if not exists (
        select 1
        from public.role_assignments ra
        where ra.user_id = p_profile_id
          and ra.case_id = p_case_id
    ) then
        raise exception 'El perfil no tiene asignacion activa para este caso.';
    end if;

    return query
    select
        sp.id,
        sp.profile_id,
        sp.case_id,
        sp.guide_completed,
        sp.case_context_completed,
        sp.role_preparation_completed,
        sp.public_actor_profile_completed,
        sp.updated_at
    from public.student_progress sp
    where sp.profile_id = p_profile_id
      and sp.case_id = p_case_id
    limit 1;
end;
$$;

create or replace function public.upsert_student_progress_secure(
    p_profile_id uuid,
    p_case_id uuid,
    p_guide_completed boolean,
    p_case_context_completed boolean,
    p_role_preparation_completed boolean,
    p_public_actor_profile_completed boolean
)
returns table (
    id uuid,
    profile_id uuid,
    case_id uuid,
    guide_completed boolean,
    case_context_completed boolean,
    role_preparation_completed boolean,
    public_actor_profile_completed boolean,
    updated_at timestamptz
)
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
        raise exception 'Perfil no valido para guardar progreso.';
    end if;

    if not exists (
        select 1
        from public.role_assignments ra
        where ra.user_id = p_profile_id
          and ra.case_id = p_case_id
    ) then
        raise exception 'El perfil no tiene asignacion activa para este caso.';
    end if;

    return query
    with saved as (
        insert into public.student_progress (
            profile_id,
            case_id,
            guide_completed,
            case_context_completed,
            role_preparation_completed,
            public_actor_profile_completed,
            updated_at
        )
        values (
            p_profile_id,
            p_case_id,
            coalesce(p_guide_completed, false),
            coalesce(p_case_context_completed, false),
            coalesce(p_role_preparation_completed, false),
            coalesce(p_public_actor_profile_completed, false),
            now()
        )
        on conflict (profile_id, case_id)
        do update set
            guide_completed = excluded.guide_completed,
            case_context_completed = excluded.case_context_completed,
            role_preparation_completed = excluded.role_preparation_completed,
            public_actor_profile_completed = excluded.public_actor_profile_completed,
            updated_at = now()
        returning *
    )
    select
        saved.id,
        saved.profile_id,
        saved.case_id,
        saved.guide_completed,
        saved.case_context_completed,
        saved.role_preparation_completed,
        saved.public_actor_profile_completed,
        saved.updated_at
    from saved;
end;
$$;

revoke all on function public.get_student_progress_secure(uuid, uuid) from public;
revoke all on function public.upsert_student_progress_secure(
    uuid,
    uuid,
    boolean,
    boolean,
    boolean,
    boolean
) from public;

grant execute on function public.get_student_progress_secure(uuid, uuid) to anon;
grant execute on function public.upsert_student_progress_secure(
    uuid,
    uuid,
    boolean,
    boolean,
    boolean,
    boolean
) to anon;
