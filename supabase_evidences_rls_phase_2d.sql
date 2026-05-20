-- Fase 2D de endurecimiento RLS: public.evidences.
-- Objetivo:
-- - Activar RLS en evidences.
-- - Bloquear acceso directo de escritura para anon.
-- - Exponer RPC security definer para lectura propia, creacion segura y
--   resumen agregado por caso usado por el panel admin.
--
-- Validacion minima aplicada al crear:
-- - public.profiles.id = p_uploaded_by existe.
-- - public.interventions.id = p_intervention_id existe.
-- - La intervencion pertenece a p_uploaded_by.
-- - Existe role_assignments para author/case/role de la intervencion.
--
-- Esta fase no toca teacher_reviews, ai_reviews ni case_ranking.

alter table public.evidences enable row level security;

drop policy if exists "Anon can read evidences directly" on public.evidences;
drop policy if exists "Anon can insert evidences directly" on public.evidences;
drop policy if exists "Anon can update evidences directly" on public.evidences;
drop policy if exists "Anon can delete evidences directly" on public.evidences;

create or replace function public.get_evidences_for_user_secure(
    p_uploaded_by uuid
)
returns table (
    id uuid,
    intervention_id uuid,
    uploaded_by uuid,
    evidence_type text,
    title text,
    description text,
    reference_text text,
    external_url text,
    file_url text,
    created_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1
        from public.profiles p
        where p.id = p_uploaded_by
    ) then
        raise exception 'Perfil no valido para consultar evidencias.';
    end if;

    return query
    select
        e.id,
        e.intervention_id,
        e.uploaded_by,
        e.evidence_type,
        e.title,
        e.description,
        e.reference_text,
        e.external_url,
        e.file_url,
        e.created_at
    from public.evidences e
    where e.uploaded_by = p_uploaded_by
    order by e.created_at desc;
end;
$$;

create or replace function public.create_evidence_secure(
    p_intervention_id uuid,
    p_uploaded_by uuid,
    p_evidence_type text,
    p_title text,
    p_description text,
    p_reference_text text,
    p_external_url text,
    p_file_url text
)
returns table (
    id uuid,
    intervention_id uuid,
    uploaded_by uuid,
    evidence_type text,
    title text,
    description text,
    reference_text text,
    external_url text,
    file_url text,
    created_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_case_id uuid;
    v_role_id uuid;
    v_author_id uuid;
begin
    if not exists (
        select 1
        from public.profiles p
        where p.id = p_uploaded_by
    ) then
        raise exception 'Perfil no valido para guardar evidencia.';
    end if;

    select i.case_id, i.role_id, i.author_id
    into v_case_id, v_role_id, v_author_id
    from public.interventions i
    where i.id = p_intervention_id
      and i.is_visible = true
    limit 1;

    if v_author_id is null then
        raise exception 'Intervencion no valida para asociar evidencia.';
    end if;

    if v_author_id <> p_uploaded_by then
        raise exception 'La evidencia solo puede asociarse a una intervencion propia.';
    end if;

    if not exists (
        select 1
        from public.role_assignments ra
        where ra.user_id = p_uploaded_by
          and ra.case_id = v_case_id
          and ra.role_id = v_role_id
    ) then
        raise exception 'El perfil no tiene asignacion valida para esta intervencion.';
    end if;

    if nullif(trim(coalesce(p_title, '')), '') is null then
        raise exception 'El titulo de la evidencia es obligatorio.';
    end if;

    return query
    with saved as (
        insert into public.evidences (
            intervention_id,
            uploaded_by,
            evidence_type,
            title,
            description,
            reference_text,
            external_url,
            file_url
        )
        values (
            p_intervention_id,
            p_uploaded_by,
            trim(coalesce(p_evidence_type, '')),
            trim(p_title),
            trim(coalesce(p_description, '')),
            trim(coalesce(p_reference_text, '')),
            trim(coalesce(p_external_url, '')),
            nullif(trim(coalesce(p_file_url, '')), '')
        )
        returning *
    )
    select
        saved.id,
        saved.intervention_id,
        saved.uploaded_by,
        saved.evidence_type,
        saved.title,
        saved.description,
        saved.reference_text,
        saved.external_url,
        saved.file_url,
        saved.created_at
    from saved;
end;
$$;

create or replace function public.get_evidence_counts_for_case_secure(
    p_case_id uuid
)
returns table (
    author_id uuid,
    evidence_count bigint
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
        raise exception 'Caso no valido para contar evidencias.';
    end if;

    return query
    select
        i.author_id,
        count(e.id)::bigint as evidence_count
    from public.evidences e
    join public.interventions i on i.id = e.intervention_id
    where i.case_id = p_case_id
      and i.is_visible = true
    group by i.author_id
    order by i.author_id;
end;
$$;

revoke all on function public.get_evidences_for_user_secure(uuid) from public;
revoke all on function public.create_evidence_secure(
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    text,
    text
) from public;
revoke all on function public.get_evidence_counts_for_case_secure(uuid) from public;

grant execute on function public.get_evidences_for_user_secure(uuid) to anon;
grant execute on function public.create_evidence_secure(
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    text,
    text
) to anon;
grant execute on function public.get_evidence_counts_for_case_secure(uuid) to anon;
