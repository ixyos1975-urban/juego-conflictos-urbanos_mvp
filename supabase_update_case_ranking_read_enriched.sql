begin;

drop function if exists public.get_case_ranking_for_case_secure(uuid);

create function public.get_case_ranking_for_case_secure(
    p_case_id uuid
)
returns table (
    case_id uuid,
    user_id uuid,
    role_id uuid,
    total_score numeric,
    "position" integer,
    updated_at timestamptz,
    full_name text,
    email text,
    student_name text,
    role_name text,
    quality_score numeric,
    participation_score numeric,
    interaction_score numeric,
    evidence_score numeric,
    total_interventions integer,
    reply_count integer,
    evidence_count integer,
    validated_reviews_count integer,
    pending_reviews_count integer,
    in_process_reviews_count integer,
    is_provisional boolean,
    ranking_formula_version text
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
        cr.position as "position",
        cr.updated_at,
        coalesce(p.full_name, '')::text as full_name,
        coalesce(p.email, '')::text as email,
        coalesce(p.full_name, p.email, 'Estudiante')::text as student_name,
        coalesce(
            to_jsonb(r)->>'name',
            to_jsonb(r)->>'title',
            to_jsonb(r)->>'role_name',
            'Rol no registrado'
        )::text as role_name,
        cr.quality_score::numeric,
        cr.participation_score::numeric,
        cr.interaction_score::numeric,
        cr.evidence_score::numeric,
        coalesce(cr.total_interventions, 0)::integer,
        coalesce(cr.reply_count, 0)::integer,
        coalesce(cr.evidence_count, 0)::integer,
        coalesce(cr.validated_reviews_count, 0)::integer,
        coalesce(cr.pending_reviews_count, 0)::integer,
        coalesce(cr.in_process_reviews_count, 0)::integer,
        coalesce(cr.is_provisional, true)::boolean,
        coalesce(cr.ranking_formula_version, 'No registrada')::text
    from public.case_ranking cr
    join public.profiles p
        on p.id = cr.user_id
    join public.allowed_users au
        on lower(au.email) = lower(p.email)
    left join public.roles r
        on r.id = cr.role_id
    left join public.role_assignments ra
        on ra.case_id = cr.case_id
       and ra.user_id = cr.user_id
    where cr.case_id = p_case_id
      and au.is_active = true
      and coalesce(au.is_admin, false) = false
      and au.user_type = 'student'
      and p.user_role = 'estudiante'
      and coalesce(ra.participation_status, 'active') = 'active'
    order by cr.position nulls last, cr.total_score desc;
end;
$$;

revoke all on function public.get_case_ranking_for_case_secure(uuid) from public;
grant execute on function public.get_case_ranking_for_case_secure(uuid) to anon;
grant execute on function public.get_case_ranking_for_case_secure(uuid) to authenticated;

notify pgrst, 'reload schema';

commit;
