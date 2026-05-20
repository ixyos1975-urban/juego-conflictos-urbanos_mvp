-- Fase 2F de endurecimiento RLS: public.ai_reviews.
-- Objetivo:
-- - Activar RLS en ai_reviews.
-- - Bloquear acceso directo de anon a select/insert/update/delete.
-- - Exponer RPC security definer para lectura por intervencion, lectura por
--   caso y upsert seguro.
--
-- Alcance:
-- - Esta fase es solo seguridad/acceso.
-- - No implementa integracion con DeepSeek ni con ningun proveedor AI.
-- - Campos como prompt_version y ai_comment quedan disponibles para una
--   generacion futura desde DeepSeek API u otro motor externo.
--
-- Validacion minima:
-- - public.interventions.id = p_intervention_id existe.
-- - La intervencion pertenece a un caso real.
-- - Para lectura por caso, public.cases.id = p_case_id existe.
--
-- Esta fase no toca case_ranking, exportacion ni cierre formal.

alter table public.ai_reviews enable row level security;

drop policy if exists "Anon can read ai reviews directly" on public.ai_reviews;
drop policy if exists "Anon can insert ai reviews directly" on public.ai_reviews;
drop policy if exists "Anon can update ai reviews directly" on public.ai_reviews;
drop policy if exists "Anon can delete ai reviews directly" on public.ai_reviews;

create or replace function public.get_ai_review_for_intervention_secure(
    p_intervention_id uuid
)
returns table (
    intervention_id uuid,
    moderation_status text,
    role_coherence text,
    argument_strength text,
    argument_type text,
    evidence_detected boolean,
    preliminary_score numeric,
    teacher_review_recommended boolean,
    ai_comment text,
    prompt_version text,
    created_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1
        from public.interventions i
        join public.cases c on c.id = i.case_id
        where i.id = p_intervention_id
    ) then
        raise exception 'Intervencion no valida para consultar lectura preliminar.';
    end if;

    return query
    select
        ar.intervention_id,
        ar.moderation_status,
        ar.role_coherence,
        ar.argument_strength,
        ar.argument_type,
        ar.evidence_detected,
        ar.preliminary_score::numeric,
        ar.teacher_review_recommended,
        ar.ai_comment,
        ar.prompt_version,
        ar.created_at
    from public.ai_reviews ar
    where ar.intervention_id = p_intervention_id
    limit 1;
end;
$$;

create or replace function public.get_ai_reviews_for_case_secure(
    p_case_id uuid
)
returns table (
    intervention_id uuid,
    moderation_status text,
    role_coherence text,
    argument_strength text,
    argument_type text,
    evidence_detected boolean,
    preliminary_score numeric,
    teacher_review_recommended boolean,
    ai_comment text,
    prompt_version text,
    created_at timestamptz
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
        raise exception 'Caso no valido para consultar lecturas preliminares.';
    end if;

    return query
    select
        ar.intervention_id,
        ar.moderation_status,
        ar.role_coherence,
        ar.argument_strength,
        ar.argument_type,
        ar.evidence_detected,
        ar.preliminary_score::numeric,
        ar.teacher_review_recommended,
        ar.ai_comment,
        ar.prompt_version,
        ar.created_at
    from public.ai_reviews ar
    join public.interventions i on i.id = ar.intervention_id
    where i.case_id = p_case_id
    order by ar.created_at desc;
end;
$$;

create or replace function public.upsert_ai_review_secure(
    p_intervention_id uuid,
    p_moderation_status text,
    p_role_coherence text,
    p_argument_strength text,
    p_argument_type text,
    p_evidence_detected boolean,
    p_preliminary_score numeric,
    p_teacher_review_recommended boolean,
    p_ai_comment text,
    p_prompt_version text
)
returns table (
    intervention_id uuid,
    moderation_status text,
    role_coherence text,
    argument_strength text,
    argument_type text,
    evidence_detected boolean,
    preliminary_score numeric,
    teacher_review_recommended boolean,
    ai_comment text,
    prompt_version text,
    created_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1
        from public.interventions i
        join public.cases c on c.id = i.case_id
        where i.id = p_intervention_id
    ) then
        raise exception 'Intervencion no valida para guardar lectura preliminar.';
    end if;

    return query
    with saved as (
        insert into public.ai_reviews (
            intervention_id,
            moderation_status,
            role_coherence,
            argument_strength,
            argument_type,
            evidence_detected,
            preliminary_score,
            teacher_review_recommended,
            ai_comment,
            prompt_version
        )
        values (
            p_intervention_id,
            p_moderation_status,
            p_role_coherence,
            p_argument_strength,
            p_argument_type,
            coalesce(p_evidence_detected, false),
            p_preliminary_score,
            coalesce(p_teacher_review_recommended, false),
            nullif(trim(coalesce(p_ai_comment, '')), ''),
            coalesce(nullif(trim(coalesce(p_prompt_version, '')), ''), 'manual_assisted_v1')
        )
        on conflict (intervention_id)
        do update set
            moderation_status = excluded.moderation_status,
            role_coherence = excluded.role_coherence,
            argument_strength = excluded.argument_strength,
            argument_type = excluded.argument_type,
            evidence_detected = excluded.evidence_detected,
            preliminary_score = excluded.preliminary_score,
            teacher_review_recommended = excluded.teacher_review_recommended,
            ai_comment = excluded.ai_comment,
            prompt_version = excluded.prompt_version
        returning *
    )
    select
        saved.intervention_id,
        saved.moderation_status,
        saved.role_coherence,
        saved.argument_strength,
        saved.argument_type,
        saved.evidence_detected,
        saved.preliminary_score::numeric,
        saved.teacher_review_recommended,
        saved.ai_comment,
        saved.prompt_version,
        saved.created_at
    from saved;
end;
$$;

revoke all on function public.get_ai_review_for_intervention_secure(uuid) from public;
revoke all on function public.get_ai_reviews_for_case_secure(uuid) from public;
revoke all on function public.upsert_ai_review_secure(
    uuid,
    text,
    text,
    text,
    text,
    boolean,
    numeric,
    boolean,
    text,
    text
) from public;

grant execute on function public.get_ai_review_for_intervention_secure(uuid) to anon;
grant execute on function public.get_ai_reviews_for_case_secure(uuid) to anon;
grant execute on function public.upsert_ai_review_secure(
    uuid,
    text,
    text,
    text,
    text,
    boolean,
    numeric,
    boolean,
    text,
    text
) to anon;
