-- Fase 2C de endurecimiento RLS: public.interventions.
-- Objetivo:
-- - Activar RLS en interventions.
-- - Bloquear insert/update/delete directo para anon.
-- - Exponer RPC security definer para lectura por hilo y creacion segura.
-- - Mantener select anon solo para intervenciones visibles, para no romper
--   modulos existentes que aun leen interventions directamente.
--
-- Validacion minima aplicada al crear:
-- - public.profiles.id = p_author_id existe.
-- - public.role_assignments.user_id = p_author_id, case_id = p_case_id
--   y role_id = p_role_id existe.
-- - public.discussion_threads.id = p_thread_id pertenece a p_case_id.
-- - parent_intervention_id, si viene, pertenece al mismo caso e hilo.
--
-- Esta fase no toca evidences, teacher_reviews, ai_reviews ni case_ranking.

alter table public.interventions enable row level security;

drop policy if exists "Anon can read visible interventions" on public.interventions;
drop policy if exists "Anon can insert interventions directly" on public.interventions;
drop policy if exists "Anon can update interventions directly" on public.interventions;
drop policy if exists "Anon can delete interventions directly" on public.interventions;

create policy "Anon can read visible interventions"
on public.interventions
for select
to anon
using (is_visible = true);

create or replace function public.get_interventions_for_thread_secure(
    p_thread_id uuid
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
    updated_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1
        from public.discussion_threads dt
        where dt.id = p_thread_id
          and coalesce(dt.is_active, true) = true
    ) then
        raise exception 'Hilo no valido para consultar intervenciones.';
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
        i.updated_at
    from public.interventions i
    where i.thread_id = p_thread_id
      and i.is_visible = true
    order by i.created_at;
end;
$$;

create or replace function public.create_intervention_secure(
    p_case_id uuid,
    p_thread_id uuid,
    p_author_id uuid,
    p_role_id uuid,
    p_parent_intervention_id uuid,
    p_intervention_type text,
    p_title text,
    p_content text,
    p_phase text
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
        where p.id = p_author_id
    ) then
        raise exception 'Autor no valido para publicar intervencion.';
    end if;

    if not exists (
        select 1
        from public.role_assignments ra
        where ra.user_id = p_author_id
          and ra.case_id = p_case_id
          and ra.role_id = p_role_id
    ) then
        raise exception 'El autor no tiene este rol asignado para el caso.';
    end if;

    if not exists (
        select 1
        from public.discussion_threads dt
        where dt.id = p_thread_id
          and dt.case_id = p_case_id
          and coalesce(dt.is_active, true) = true
    ) then
        raise exception 'El hilo no pertenece al caso indicado o no esta activo.';
    end if;

    if p_parent_intervention_id is not null
       and not exists (
           select 1
           from public.interventions parent
           where parent.id = p_parent_intervention_id
             and parent.case_id = p_case_id
             and parent.thread_id = p_thread_id
             and parent.is_visible = true
       ) then
        raise exception 'La intervencion padre no pertenece al mismo hilo y caso.';
    end if;

    if nullif(trim(coalesce(p_content, '')), '') is null then
        raise exception 'El contenido de la intervencion es obligatorio.';
    end if;

    return query
    with saved as (
        insert into public.interventions (
            case_id,
            thread_id,
            author_id,
            role_id,
            parent_intervention_id,
            intervention_type,
            title,
            content,
            phase,
            is_visible
        )
        values (
            p_case_id,
            p_thread_id,
            p_author_id,
            p_role_id,
            p_parent_intervention_id,
            trim(coalesce(p_intervention_type, 'intervencion')),
            nullif(trim(coalesce(p_title, '')), ''),
            trim(p_content),
            trim(coalesce(p_phase, 'apertura')),
            true
        )
        returning *
    )
    select
        saved.id,
        saved.case_id,
        saved.thread_id,
        saved.author_id,
        saved.role_id,
        saved.parent_intervention_id,
        saved.intervention_type,
        saved.title,
        saved.content,
        saved.phase,
        saved.is_visible,
        saved.review_status,
        saved.created_at,
        saved.updated_at
    from saved;
end;
$$;

revoke all on function public.get_interventions_for_thread_secure(uuid) from public;
revoke all on function public.create_intervention_secure(
    uuid,
    uuid,
    uuid,
    uuid,
    uuid,
    text,
    text,
    text,
    text
) from public;

grant execute on function public.get_interventions_for_thread_secure(uuid) to anon;
grant execute on function public.create_intervention_secure(
    uuid,
    uuid,
    uuid,
    uuid,
    uuid,
    text,
    text,
    text,
    text
) to anon;
