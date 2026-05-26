begin;

drop function if exists public.get_interventions_for_teacher_review_secure(uuid, uuid);

create function public.get_interventions_for_teacher_review_secure(
    p_case_id uuid,
    p_student_profile_id uuid default null
)
returns table (
    intervention_id uuid,
    case_id uuid,
    thread_id uuid,
    author_id uuid,
    role_id uuid,
    parent_intervention_id uuid,
    author_email text,
    author_name text,
    role_name text,
    thread_title text,
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
        i.id as intervention_id,
        i.case_id,
        i.thread_id,
        i.author_id,
        i.role_id,
        i.parent_intervention_id,
        coalesce(p.email, '')::text as author_email,
        coalesce(
            p.full_name,
            p.email,
            'Estudiante'
        )::text as author_name,
        coalesce(
            to_jsonb(r)->>'name',
            to_jsonb(r)->>'title',
            to_jsonb(r)->>'role_name',
            'Rol asignado'
        )::text as role_name,
        coalesce(dt.title, 'Hilo sin titulo')::text as thread_title,
        i.intervention_type,
        i.title,
        i.content,
        i.phase,
        i.is_visible,
        i.review_status,
        i.created_at,
        i.updated_at
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

revoke all on function public.get_interventions_for_teacher_review_secure(uuid, uuid) from public;
grant execute on function public.get_interventions_for_teacher_review_secure(uuid, uuid) to anon;
grant execute on function public.get_interventions_for_teacher_review_secure(uuid, uuid) to authenticated;

notify pgrst, 'reload schema';

commit;
