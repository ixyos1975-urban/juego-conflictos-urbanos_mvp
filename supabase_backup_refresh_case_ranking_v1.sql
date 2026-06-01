-- Backup V1 de public.refresh_case_ranking_for_case_secure(uuid).
-- Recuperado desde supabase_case_ranking_rls_phase_2g.sql antes de preparar V2.
-- Formula V1: promedio simple de teacher_reviews.final_score validadas.

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

revoke all on function public.refresh_case_ranking_for_case_secure(uuid) from public;
grant execute on function public.refresh_case_ranking_for_case_secure(uuid) to anon;

