begin;

drop function if exists public.refresh_case_ranking_for_case_secure(uuid);

create function public.refresh_case_ranking_for_case_secure(
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

    with student_base as (
        select distinct on (ra.case_id, p.id)
            ra.case_id,
            p.id as user_id,
            p.email,
            p.full_name,
            ra.role_id
        from public.role_assignments ra
        join public.profiles p
            on p.id = ra.user_id
        join public.allowed_users au
            on lower(au.email) = lower(p.email)
        where ra.case_id = p_case_id
          and au.is_active = true
          and coalesce(au.is_admin, false) = false
          and au.user_type = 'student'
          and p.user_role = 'estudiante'
          and coalesce(ra.participation_status, 'active') = 'active'
          and lower(coalesce(p.email, '')) not in (
              'alumno1@unisalle.edu.co'
          )
        order by ra.case_id, p.id
    ),
    visible_interventions as (
        select
            i.id,
            i.case_id,
            i.thread_id,
            i.author_id as user_id,
            i.role_id,
            i.intervention_type,
            i.parent_intervention_id,
            i.created_at
        from public.interventions i
        join student_base sb
            on sb.case_id = i.case_id
           and sb.user_id = i.author_id
        where coalesce(i.is_visible, true) = true
    ),
    evidence_by_intervention as (
        select
            e.intervention_id,
            count(e.id)::integer as evidence_count
        from public.evidences e
        join visible_interventions i
            on i.id = e.intervention_id
        group by e.intervention_id
    ),
    student_activity as (
        select
            sb.case_id,
            sb.user_id,
            count(i.id)::integer as total_interventions,
            count(i.id) filter (
                where i.parent_intervention_id is not null
            )::integer as reply_count,
            coalesce(sum(ebi.evidence_count), 0)::integer as evidence_count,
            count(distinct i.id) filter (
                where coalesce(ebi.evidence_count, 0) > 0
            )::integer as interventions_with_evidence
        from student_base sb
        left join visible_interventions i
            on i.case_id = sb.case_id
           and i.user_id = sb.user_id
        left join evidence_by_intervention ebi
            on ebi.intervention_id = i.id
        group by sb.case_id, sb.user_id
    ),
    validated_reviews as (
        select
            i.case_id,
            i.user_id,
            tr.intervention_id,
            i.intervention_type,
            i.parent_intervention_id,
            tr.final_score::numeric as final_score,
            tr.argument_quality_score::numeric as argument_quality_score,
            tr.evidence_use_score::numeric as evidence_use_score,
            tr.discussion_result_score::numeric as discussion_result_score,
            coalesce(ebi.evidence_count, 0) as evidence_count
        from public.teacher_reviews tr
        join visible_interventions i
            on i.id = tr.intervention_id
        left join evidence_by_intervention ebi
            on ebi.intervention_id = i.id
        where tr.review_status = 'validada'
          and tr.final_score is not null
    ),
    review_summary as (
        select
            sb.case_id,
            sb.user_id,
            count(vr.intervention_id)::integer as validated_reviews_count,
            round(avg(vr.final_score)::numeric, 2) as quality_score,
            round(avg(vr.argument_quality_score)::numeric, 2) as avg_argument_quality_score,
            round(avg(vr.evidence_use_score)::numeric, 2) as avg_evidence_use_score
        from student_base sb
        left join validated_reviews vr
            on vr.case_id = sb.case_id
           and vr.user_id = sb.user_id
        group by sb.case_id, sb.user_id
    ),
    review_status_summary as (
        select
            sb.case_id,
            sb.user_id,
            count(distinct i.id) filter (
                where tr.intervention_id is null
                   or tr.review_status = 'pendiente'
            )::integer as pending_reviews_count,
            count(distinct i.id) filter (
                where tr.review_status is not null
                  and tr.review_status not in ('validada', 'pendiente')
            )::integer as in_process_reviews_count
        from student_base sb
        left join visible_interventions i
            on i.case_id = sb.case_id
           and i.user_id = sb.user_id
        left join public.teacher_reviews tr
            on tr.intervention_id = i.id
        group by sb.case_id, sb.user_id
    ),
    reply_review_summary as (
        select
            sb.case_id,
            sb.user_id,
            round(avg(vr.discussion_result_score)::numeric, 2) as avg_reply_discussion_score,
            round(avg(vr.argument_quality_score)::numeric, 2) as avg_reply_argument_quality_score
        from student_base sb
        left join validated_reviews vr
            on vr.case_id = sb.case_id
           and vr.user_id = sb.user_id
           and (
                vr.parent_intervention_id is not null
                or lower(coalesce(vr.intervention_type, '')) in (
                    'respuesta',
                    'contraargumento',
                    'negociacion'
                )
           )
        group by sb.case_id, sb.user_id
    ),
    reply_links as (
        select
            child.id as reply_id,
            child.case_id,
            child.thread_id,
            child.user_id as reply_author_id,
            parent.user_id as original_author_id,
            child.created_at as reply_created_at
        from visible_interventions child
        join visible_interventions parent
            on parent.id = child.parent_intervention_id
        where child.user_id <> parent.user_id
    ),
    replies_made_summary as (
        select
            sb.case_id,
            sb.user_id,
            count(rl.reply_id)::integer as replies_made
        from student_base sb
        left join reply_links rl
            on rl.case_id = sb.case_id
           and rl.reply_author_id = sb.user_id
        group by sb.case_id, sb.user_id
    ),
    dialogic_received_events as (
        select
            sb.case_id,
            sb.user_id,
            rl.reply_id as received_reply_id,
            attended.id as attended_intervention_id,
            tr.argument_quality_score::numeric as attended_argument_quality_score,
            tr.discussion_result_score::numeric as attended_discussion_result_score
        from student_base sb
        join reply_links rl
            on rl.case_id = sb.case_id
           and rl.original_author_id = sb.user_id
        left join lateral (
            select i.id
            from visible_interventions i
            where i.parent_intervention_id = rl.reply_id
              and i.user_id = sb.user_id
              and i.created_at > rl.reply_created_at
            order by i.created_at asc
            limit 1
        ) attended on true
        left join public.teacher_reviews tr
            on tr.intervention_id = attended.id
           and tr.review_status = 'validada'
    ),
    dialogic_attention_summary as (
        select
            sb.case_id,
            sb.user_id,
            count(dre.received_reply_id)::integer as replies_received,
            count(dre.received_reply_id) filter (
                where dre.attended_intervention_id is not null
            )::integer as replies_received_attended,
            count(dre.received_reply_id) filter (
                where dre.attended_intervention_id is null
            )::integer as replies_received_unattended,
            case
                when count(dre.received_reply_id) = 0 then null
                else round(
                    (
                        count(dre.received_reply_id) filter (
                            where dre.attended_intervention_id is not null
                        )::numeric
                        / count(dre.received_reply_id)::numeric
                    ),
                    2
                )
            end as dialogic_attention_ratio,
            round(
                (
                    avg(
                        (
                            dre.attended_argument_quality_score
                            + dre.attended_discussion_result_score
                        ) / 2.0
                    ) filter (
                        where dre.attended_intervention_id is not null
                          and dre.attended_argument_quality_score is not null
                          and dre.attended_discussion_result_score is not null
                    )
                )::numeric,
                2
            ) as avg_attended_response_score
        from student_base sb
        left join dialogic_received_events dre
            on dre.case_id = sb.case_id
           and dre.user_id = sb.user_id
        group by sb.case_id, sb.user_id
    ),
    dialogic_attention_score as (
        select
            das.case_id,
            das.user_id,
            das.replies_received,
            das.replies_received_attended,
            das.replies_received_unattended,
            das.dialogic_attention_ratio,
            round(
                case
                    when coalesce(das.replies_received, 0) = 0 then 3.5
                    when coalesce(das.replies_received_attended, 0) = 0 then 0.5
                    when das.avg_attended_response_score is null then least(
                        5.0,
                        coalesce(das.dialogic_attention_ratio, 0) * 3.25
                    )
                    else least(
                        5.0,
                        (
                            coalesce(das.dialogic_attention_ratio, 0) * 3.25
                            + das.avg_attended_response_score * 0.35
                        )
                    )
                end::numeric,
                2
            ) as dialogic_attention_score
        from dialogic_attention_summary das
    ),
    evidence_review_summary as (
        select
            sb.case_id,
            sb.user_id,
            round(avg(vr.evidence_use_score)::numeric, 2) as avg_evidence_argument_score
        from student_base sb
        left join validated_reviews vr
            on vr.case_id = sb.case_id
           and vr.user_id = sb.user_id
           and vr.evidence_count > 0
        group by sb.case_id, sb.user_id
    ),
    v2_inputs as (
        select
            sb.case_id,
            sb.user_id,
            sb.role_id,
            (
                coalesce(sa.total_interventions, 0) > 0
                or coalesce(rs.validated_reviews_count, 0) > 0
                or coalesce(sa.evidence_count, 0) > 0
            ) as has_real_activity,
            case
                when coalesce(sa.total_interventions, 0) = 0 then 0.0
                when sa.total_interventions = 1 then 1.5
                when sa.total_interventions = 2 then 2.4
                when sa.total_interventions = 3 then 3.1
                when sa.total_interventions = 4 then 3.7
                when sa.total_interventions = 5 then 4.1
                when sa.total_interventions = 6 then 4.4
                else 4.6
            end::numeric as participation_quantity_score,
            case
                when coalesce(sa.total_interventions, 0) = 0 then 0.0
                else least(
                    5.0,
                    round(
                        (
                            coalesce(rs.validated_reviews_count, 0)::numeric
                            / nullif(sa.total_interventions, 0)::numeric
                        ) * 5.0,
                        2
                    )
                )
            end::numeric as validated_coverage_score,
            case
                when coalesce(rms.replies_made, 0) = 0 then 0.0
                when rms.replies_made = 1 then 2.5
                when rms.replies_made = 2 then 3.4
                when rms.replies_made = 3 then 3.9
                when rms.replies_made = 4 then 4.2
                else 4.4
            end::numeric as reply_quantity_score,
            case
                when coalesce(sa.evidence_count, 0) = 0 then 0.0
                when sa.evidence_count = 1 then 2.5
                when sa.evidence_count = 2 then 3.4
                when sa.evidence_count = 3 then 3.9
                when sa.evidence_count = 4 then 4.2
                else 4.4
            end::numeric as evidence_quantity_score,
            case
                when coalesce(sa.total_interventions, 0) = 0 then 0.0
                else least(
                    5.0,
                    round(
                        (
                            coalesce(sa.interventions_with_evidence, 0)::numeric
                            / nullif(sa.total_interventions, 0)::numeric
                        ) * 5.0,
                        2
                    )
                )
            end::numeric as evidence_coverage_score
        from student_base sb
        left join student_activity sa
            on sa.case_id = sb.case_id
           and sa.user_id = sb.user_id
        left join review_summary rs
            on rs.case_id = sb.case_id
           and rs.user_id = sb.user_id
        left join replies_made_summary rms
            on rms.case_id = sb.case_id
           and rms.user_id = sb.user_id
    ),
    v2_scores as (
        select
            sb.case_id,
            sb.user_id,
            vi.role_id,
            coalesce(sa.total_interventions, 0)::integer as total_interventions,
            coalesce(sa.reply_count, 0)::integer as reply_count,
            coalesce(sa.evidence_count, 0)::integer as evidence_count,
            coalesce(rs.validated_reviews_count, 0)::integer as validated_reviews_count,
            coalesce(rss.pending_reviews_count, 0)::integer as pending_reviews_count,
            coalesce(rss.in_process_reviews_count, 0)::integer as in_process_reviews_count,
            coalesce(rs.quality_score, 0)::numeric as quality_score,
            case
                when vi.has_real_activity is not true then 0.0
                else round(
                    (
                        vi.participation_quantity_score * 0.40
                        + coalesce(rs.quality_score, 0) * 0.40
                        + vi.validated_coverage_score * 0.20
                    )::numeric,
                    2
                )
            end as participation_score,
            case
                when vi.has_real_activity is not true then 0.0
                else round(
                    (
                        vi.reply_quantity_score * 0.25
                        + coalesce(rrs.avg_reply_discussion_score, 0) * 0.25
                        + coalesce(rrs.avg_reply_argument_quality_score, 0) * 0.20
                        + coalesce(das.dialogic_attention_score, 3.5) * 0.30
                    )::numeric,
                    2
                )
            end as interaction_score,
            case
                when vi.has_real_activity is not true then 0.0
                else round(
                    (
                        vi.evidence_quantity_score * 0.30
                        + coalesce(ers.avg_evidence_argument_score, rs.avg_evidence_use_score, 0) * 0.50
                        + vi.evidence_coverage_score * 0.20
                    )::numeric,
                    2
                )
            end as evidence_score
        from student_base sb
        join v2_inputs vi
            on vi.case_id = sb.case_id
           and vi.user_id = sb.user_id
        left join student_activity sa
            on sa.case_id = sb.case_id
           and sa.user_id = sb.user_id
        left join review_summary rs
            on rs.case_id = sb.case_id
           and rs.user_id = sb.user_id
        left join review_status_summary rss
            on rss.case_id = sb.case_id
           and rss.user_id = sb.user_id
        left join reply_review_summary rrs
            on rrs.case_id = sb.case_id
           and rrs.user_id = sb.user_id
        left join dialogic_attention_score das
            on das.case_id = sb.case_id
           and das.user_id = sb.user_id
        left join evidence_review_summary ers
            on ers.case_id = sb.case_id
           and ers.user_id = sb.user_id
    ),
    final_scores as (
        select
            vs.*,
            case
                when (
                    vs.total_interventions = 0
                    and vs.validated_reviews_count = 0
                    and vs.evidence_count = 0
                ) then 0.0
                else round(
                    (
                        vs.quality_score * 0.65
                        + vs.participation_score * 0.15
                        + vs.interaction_score * 0.12
                        + vs.evidence_score * 0.08
                    )::numeric,
                    2
                )
            end as total_score,
            (
                coalesce(vs.pending_reviews_count, 0) > 0
                or coalesce(vs.in_process_reviews_count, 0) > 0
            ) as is_provisional
        from v2_scores vs
    ),
    ranked_scores as (
        select
            fs.*,
            dense_rank() over (
                partition by fs.case_id
                order by fs.total_score desc
            )::integer as position
        from final_scores fs
    ),
    removed_excluded_rows as (
        delete from public.case_ranking cr
        where cr.case_id = p_case_id
          and not exists (
              select 1
              from student_base sb
              where sb.case_id = cr.case_id
                and sb.user_id = cr.user_id
          )
        returning 1
    ),
    upserted as (
        insert into public.case_ranking (
            case_id,
            user_id,
            role_id,
            total_score,
            position,
            updated_at,
            quality_score,
            participation_score,
            interaction_score,
            evidence_score,
            total_interventions,
            reply_count,
            evidence_count,
            validated_reviews_count,
            pending_reviews_count,
            in_process_reviews_count,
            is_provisional,
            ranking_formula_version
        )
        select
            case_id,
            user_id,
            role_id,
            total_score,
            position,
            now(),
            quality_score,
            participation_score,
            interaction_score,
            evidence_score,
            total_interventions,
            reply_count,
            evidence_count,
            validated_reviews_count,
            pending_reviews_count,
            in_process_reviews_count,
            is_provisional,
            'quality_participation_v2_incidence'
        from ranked_scores
        on conflict (case_id, user_id)
        do update set
            role_id = excluded.role_id,
            total_score = excluded.total_score,
            position = excluded.position,
            updated_at = now(),
            quality_score = excluded.quality_score,
            participation_score = excluded.participation_score,
            interaction_score = excluded.interaction_score,
            evidence_score = excluded.evidence_score,
            total_interventions = excluded.total_interventions,
            reply_count = excluded.reply_count,
            evidence_count = excluded.evidence_count,
            validated_reviews_count = excluded.validated_reviews_count,
            pending_reviews_count = excluded.pending_reviews_count,
            in_process_reviews_count = excluded.in_process_reviews_count,
            is_provisional = excluded.is_provisional,
            ranking_formula_version = excluded.ranking_formula_version
        returning 1
    )
    select count(*) into refreshed_rows
    from upserted;

    return refreshed_rows;
end;
$$;

revoke all on function public.refresh_case_ranking_for_case_secure(uuid) from public;
grant execute on function public.refresh_case_ranking_for_case_secure(uuid) to anon;
grant execute on function public.refresh_case_ranking_for_case_secure(uuid) to authenticated;

notify pgrst, 'reload schema';

commit;
