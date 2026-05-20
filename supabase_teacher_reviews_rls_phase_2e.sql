-- Fase 2E de endurecimiento RLS: public.teacher_reviews.
-- Objetivo:
-- - Activar RLS en teacher_reviews.
-- - Bloquear acceso directo de anon a select/insert/update/delete.
-- - Exponer RPC security definer para lectura por intervencion, lectura por
--   estudiante/caso y upsert seguro desde panel admin.
--
-- Validacion minima:
-- - public.interventions.id = p_intervention_id existe y pertenece a un caso real.
-- - public.profiles.id = p_reviewed_by existe.
-- - Para escritura, reviewed_by debe corresponder a allowed_users.is_admin = true.
--
-- Esta fase no toca ai_reviews, case_ranking, exportacion ni cierre formal.
-- No crea triggers hacia case_ranking.

alter table public.teacher_reviews enable row level security;

drop policy if exists "Anon can read teacher reviews directly" on public.teacher_reviews;
drop policy if exists "Anon can insert teacher reviews directly" on public.teacher_reviews;
drop policy if exists "Anon can update teacher reviews directly" on public.teacher_reviews;
drop policy if exists "Anon can delete teacher reviews directly" on public.teacher_reviews;

create or replace function public.get_teacher_review_for_intervention_secure(
    p_intervention_id uuid
)
returns table (
    intervention_id uuid,
    reviewed_by uuid,
    review_status text,
    intervention_rating text,
    intervention_rating_score numeric,
    role_coherence_rating text,
    role_coherence_score numeric,
    argument_quality_rating text,
    argument_quality_score numeric,
    evidence_use_rating text,
    evidence_use_score numeric,
    discussion_result text,
    discussion_result_score numeric,
    final_score numeric,
    teacher_comment text,
    reviewed_at timestamptz
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
        raise exception 'Intervencion no valida para consultar revision docente.';
    end if;

    return query
    select
        tr.intervention_id,
        tr.reviewed_by,
        tr.review_status,
        tr.intervention_rating,
        tr.intervention_rating_score::numeric,
        tr.role_coherence_rating,
        tr.role_coherence_score::numeric,
        tr.argument_quality_rating,
        tr.argument_quality_score::numeric,
        tr.evidence_use_rating,
        tr.evidence_use_score::numeric,
        tr.discussion_result,
        tr.discussion_result_score::numeric,
        tr.final_score::numeric,
        tr.teacher_comment,
        tr.reviewed_at
    from public.teacher_reviews tr
    where tr.intervention_id = p_intervention_id
    limit 1;
end;
$$;

create or replace function public.get_teacher_reviews_for_student_secure(
    p_case_id uuid,
    p_profile_id uuid
)
returns table (
    intervention_id uuid,
    reviewed_by uuid,
    review_status text,
    intervention_rating text,
    intervention_rating_score numeric,
    role_coherence_rating text,
    role_coherence_score numeric,
    argument_quality_rating text,
    argument_quality_score numeric,
    evidence_use_rating text,
    evidence_use_score numeric,
    discussion_result text,
    discussion_result_score numeric,
    final_score numeric,
    teacher_comment text,
    reviewed_at timestamptz
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
        raise exception 'Caso no valido para consultar revisiones docentes.';
    end if;

    if not exists (
        select 1
        from public.profiles p
        where p.id = p_profile_id
    ) then
        raise exception 'Perfil no valido para consultar revisiones docentes.';
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
        tr.intervention_id,
        tr.reviewed_by,
        tr.review_status,
        tr.intervention_rating,
        tr.intervention_rating_score::numeric,
        tr.role_coherence_rating,
        tr.role_coherence_score::numeric,
        tr.argument_quality_rating,
        tr.argument_quality_score::numeric,
        tr.evidence_use_rating,
        tr.evidence_use_score::numeric,
        tr.discussion_result,
        tr.discussion_result_score::numeric,
        tr.final_score::numeric,
        tr.teacher_comment,
        tr.reviewed_at
    from public.teacher_reviews tr
    join public.interventions i on i.id = tr.intervention_id
    where i.case_id = p_case_id
      and i.author_id = p_profile_id
    order by tr.reviewed_at desc;
end;
$$;

create or replace function public.upsert_teacher_review_secure(
    p_intervention_id uuid,
    p_reviewed_by uuid,
    p_review_status text,
    p_intervention_rating text,
    p_intervention_rating_score numeric,
    p_role_coherence_rating text,
    p_role_coherence_score numeric,
    p_argument_quality_rating text,
    p_argument_quality_score numeric,
    p_evidence_use_rating text,
    p_evidence_use_score numeric,
    p_discussion_result text,
    p_discussion_result_score numeric,
    p_final_score numeric,
    p_teacher_comment text,
    p_reviewed_at timestamptz
)
returns table (
    intervention_id uuid,
    reviewed_by uuid,
    review_status text,
    intervention_rating text,
    intervention_rating_score numeric,
    role_coherence_rating text,
    role_coherence_score numeric,
    argument_quality_rating text,
    argument_quality_score numeric,
    evidence_use_rating text,
    evidence_use_score numeric,
    discussion_result text,
    discussion_result_score numeric,
    final_score numeric,
    teacher_comment text,
    reviewed_at timestamptz
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
        raise exception 'Intervencion no valida para guardar revision docente.';
    end if;

    if not exists (
        select 1
        from public.profiles p
        where p.id = p_reviewed_by
    ) then
        raise exception 'Perfil docente no valido para guardar revision.';
    end if;

    if not exists (
        select 1
        from public.profiles p
        join public.allowed_users au on lower(au.email) = lower(p.email)
        where p.id = p_reviewed_by
          and coalesce(au.is_active, true) = true
          and au.is_admin = true
    ) then
        raise exception 'El perfil revisor no tiene autorizacion administrativa.';
    end if;

    return query
    with saved as (
        insert into public.teacher_reviews (
            intervention_id,
            reviewed_by,
            review_status,
            intervention_rating,
            intervention_rating_score,
            role_coherence_rating,
            role_coherence_score,
            argument_quality_rating,
            argument_quality_score,
            evidence_use_rating,
            evidence_use_score,
            discussion_result,
            discussion_result_score,
            final_score,
            teacher_comment,
            reviewed_at
        )
        values (
            p_intervention_id,
            p_reviewed_by,
            p_review_status,
            p_intervention_rating,
            p_intervention_rating_score,
            p_role_coherence_rating,
            p_role_coherence_score,
            p_argument_quality_rating,
            p_argument_quality_score,
            p_evidence_use_rating,
            p_evidence_use_score,
            p_discussion_result,
            p_discussion_result_score,
            p_final_score,
            trim(coalesce(p_teacher_comment, '')),
            coalesce(p_reviewed_at, now())
        )
        on conflict (intervention_id)
        do update set
            reviewed_by = excluded.reviewed_by,
            review_status = excluded.review_status,
            intervention_rating = excluded.intervention_rating,
            intervention_rating_score = excluded.intervention_rating_score,
            role_coherence_rating = excluded.role_coherence_rating,
            role_coherence_score = excluded.role_coherence_score,
            argument_quality_rating = excluded.argument_quality_rating,
            argument_quality_score = excluded.argument_quality_score,
            evidence_use_rating = excluded.evidence_use_rating,
            evidence_use_score = excluded.evidence_use_score,
            discussion_result = excluded.discussion_result,
            discussion_result_score = excluded.discussion_result_score,
            final_score = excluded.final_score,
            teacher_comment = excluded.teacher_comment,
            reviewed_at = excluded.reviewed_at
        returning *
    )
    select
        saved.intervention_id,
        saved.reviewed_by,
        saved.review_status,
        saved.intervention_rating,
        saved.intervention_rating_score::numeric,
        saved.role_coherence_rating,
        saved.role_coherence_score::numeric,
        saved.argument_quality_rating,
        saved.argument_quality_score::numeric,
        saved.evidence_use_rating,
        saved.evidence_use_score::numeric,
        saved.discussion_result,
        saved.discussion_result_score::numeric,
        saved.final_score::numeric,
        saved.teacher_comment,
        saved.reviewed_at
    from saved;
end;
$$;

revoke all on function public.get_teacher_review_for_intervention_secure(uuid) from public;
revoke all on function public.get_teacher_reviews_for_student_secure(uuid, uuid) from public;
revoke all on function public.upsert_teacher_review_secure(
    uuid,
    uuid,
    text,
    text,
    numeric,
    text,
    numeric,
    text,
    numeric,
    text,
    numeric,
    text,
    numeric,
    numeric,
    text,
    timestamptz
) from public;

grant execute on function public.get_teacher_review_for_intervention_secure(uuid) to anon;
grant execute on function public.get_teacher_reviews_for_student_secure(uuid, uuid) to anon;
grant execute on function public.upsert_teacher_review_secure(
    uuid,
    uuid,
    text,
    text,
    numeric,
    text,
    numeric,
    text,
    numeric,
    text,
    numeric,
    text,
    numeric,
    numeric,
    text,
    timestamptz
) to anon;
