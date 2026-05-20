-- Fase 2G de endurecimiento RLS: public.case_ranking.
-- Objetivo:
-- - Activar RLS en case_ranking.
-- - Bloquear acceso directo de anon a select/insert/update/delete.
-- - Mantener consolidacion explicita desde panel admin mediante RPC.
-- - No reintroducir triggers automaticos desde teacher_reviews.
--
-- Validacion minima:
-- - public.cases.id = p_case_id existe.
-- - public.profiles.id = p_user_id existe cuando aplica.
-- - La consolidacion usa solo teacher_reviews.review_status = 'validada'.
--
-- Esta fase no toca exportacion ni cierre formal.

alter table public.case_ranking enable row level security;

drop policy if exists "Anon can read case ranking directly" on public.case_ranking;
drop policy if exists "Anon can insert case ranking directly" on public.case_ranking;
drop policy if exists "Anon can update case ranking directly" on public.case_ranking;
drop policy if exists "Anon can delete case ranking directly" on public.case_ranking;

create unique index if not exists idx_case_ranking_case_user_unique
    on public.case_ranking(case_id, user_id);

-- La RPC antigua queda sin permiso anon para evitar depender de ella desde la app.
revoke execute on function public.refresh_case_ranking_for_case(uuid) from anon;
revoke execute on function public.refresh_case_ranking_for_case(uuid) from authenticated;

create or replace function public.get_case_ranking_for_student_secure(
    p_case_id uuid,
    p_user_id uuid
)
returns table (
    case_id uuid,
    user_id uuid,
    role_id uuid,
    total_score numeric,
    position integer,
    updated_at timestamptz
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
        raise exception 'Caso no valido para consultar ranking.';
    end if;

    if not exists (
        select 1
        from public.profiles p
        where p.id = p_user_id
    ) then
        raise exception 'Perfil no valido para consultar ranking.';
    end if;

    return query
    select
        cr.case_id,
        cr.user_id,
        cr.role_id,
        cr.total_score::numeric,
        cr.position,
        cr.updated_at
    from public.case_ranking cr
    where cr.case_id = p_case_id
      and cr.user_id = p_user_id
    limit 1;
end;
$$;

create or replace function public.get_case_ranking_for_case_secure(
    p_case_id uuid
)
returns table (
    case_id uuid,
    user_id uuid,
    role_id uuid,
    total_score numeric,
    position integer,
    updated_at timestamptz,
    student_name text,
    role_name text
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
        raise exception 'Caso no valido para consultar ranking.';
    end if;

    return query
    select
        cr.case_id,
        cr.user_id,
        cr.role_id,
        cr.total_score::numeric,
        cr.position,
        cr.updated_at,
        coalesce(
            to_jsonb(p)->>'full_name',
            to_jsonb(p)->>'name',
            to_jsonb(p)->>'display_name',
            to_jsonb(p)->>'email',
            'Estudiante'
        )::text as student_name,
        coalesce(
            to_jsonb(r)->>'name',
            to_jsonb(r)->>'title',
            to_jsonb(r)->>'role_name',
            'Rol asignado'
        )::text as role_name
    from public.case_ranking cr
    left join public.profiles p on p.id = cr.user_id
    left join public.roles r on r.id = cr.role_id
    where cr.case_id = p_case_id
    order by cr.position nulls last, cr.total_score desc;
end;
$$;

create or replace function public.refresh_case_ranking_for_case_secure(
    p_case_id uuid
)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
    refreshed_rows integer := 0;
begin
    if not exists (
        select 1
        from public.cases c
        where c.id = p_case_id
    ) then
        raise exception 'Caso no valido para consolidar ranking.';
    end if;

    with grouped_scores as (
        select
            i.case_id,
            i.author_id as user_id,
            (array_agg(i.role_id order by i.created_at desc))[1] as role_id,
            round(avg(tr.final_score)::numeric, 2) as total_score
        from public.teacher_reviews tr
        join public.interventions i
            on i.id = tr.intervention_id
        where
            i.case_id = p_case_id
            and tr.review_status = 'validada'
            and tr.final_score is not null
        group by
            i.case_id,
            i.author_id
    ),
    ranked_scores as (
        select
            case_id,
            user_id,
            role_id,
            total_score,
            dense_rank() over (
                partition by case_id
                order by total_score desc
            )::integer as position
        from grouped_scores
    ),
    upserted as (
        insert into public.case_ranking (
            case_id,
            user_id,
            role_id,
            total_score,
            position,
            updated_at
        )
        select
            case_id,
            user_id,
            role_id,
            total_score,
            position,
            now()
        from ranked_scores
        on conflict (case_id, user_id)
        do update set
            role_id = excluded.role_id,
            total_score = excluded.total_score,
            position = excluded.position,
            updated_at = now()
        returning 1
    )
    select count(*) into refreshed_rows
    from upserted;

    return refreshed_rows;
end;
$$;

revoke all on function public.get_case_ranking_for_student_secure(uuid, uuid) from public;
revoke all on function public.get_case_ranking_for_case_secure(uuid) from public;
revoke all on function public.refresh_case_ranking_for_case_secure(uuid) from public;

grant execute on function public.get_case_ranking_for_student_secure(uuid, uuid) to anon;
grant execute on function public.get_case_ranking_for_case_secure(uuid) to anon;
grant execute on function public.refresh_case_ranking_for_case_secure(uuid) to anon;
