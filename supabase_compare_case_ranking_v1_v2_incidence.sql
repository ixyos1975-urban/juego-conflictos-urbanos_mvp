with target_case as (
    select c.id, c.slug
    from public.cases c
    where c.slug = 'caso-borde-barrial'
    limit 1
),
student_base as (
    select
        ra.case_id,
        p.id as user_id,
        p.email,
        p.full_name,
        ra.role_id,
        coalesce(
            to_jsonb(r)->>'name',
            to_jsonb(r)->>'title',
            to_jsonb(r)->>'role_name',
            'Rol no registrado'
        ) as role_name
    from public.role_assignments ra
    join target_case tc on tc.id = ra.case_id
    join public.profiles p on p.id = ra.user_id
    join public.allowed_users au on lower(au.email) = lower(p.email)
    left join public.roles r on r.id = ra.role_id
    where au.is_active = true
      and coalesce(au.is_admin, false) = false
      and au.user_type = 'student'
      and p.user_role = 'estudiante'
      and coalesce(ra.participation_status, 'active') = 'active'
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
    join target_case tc on tc.id = i.case_id
    where coalesce(i.is_visible, true) = true
),
evidence_by_intervention as (
    select
        e.intervention_id,
        count(e.id)::integer as evidence_count
    from public.evidences e
    join visible_interventions i on i.id = e.intervention_id
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
    join visible_interventions i on i.id = tr.intervention_id
    left join evidence_by_intervention ebi on ebi.intervention_id = i.id
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
v1_scores as (
    select
        sb.case_id,
        sb.user_id,
        case
            when coalesce(sa.total_interventions, 0) = 0 then 0.0
            when sa.total_interventions = 1 then 1.5
            when sa.total_interventions = 2 then 2.5
            when sa.total_interventions = 3 then 3.5
            when sa.total_interventions = 4 then 4.2
            when sa.total_interventions = 5 then 4.6
            else 5.0
        end::numeric as participation_score_v1,
        case
            when coalesce(sa.reply_count, 0) = 0 then 0.0
            when sa.reply_count = 1 then 3.5
            when sa.reply_count = 2 then 4.5
            else 5.0
        end::numeric as interaction_score_v1,
        case
            when coalesce(sa.evidence_count, 0) = 0 then 0.0
            when sa.evidence_count = 1 then 3.5
            when sa.evidence_count = 2 then 4.5
            else 5.0
        end::numeric as evidence_score_v1
    from student_base sb
    left join student_activity sa
        on sa.case_id = sb.case_id
       and sa.user_id = sb.user_id
),
v2_inputs as (
    select
        sb.case_id,
        sb.user_id,
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
        round(
            (
                vi.participation_quantity_score * 0.40
                + coalesce(rs.quality_score, 0) * 0.40
                + vi.validated_coverage_score * 0.20
            )::numeric,
            2
        ) as participation_incidence_score_v2,
        round(
            (
                vi.reply_quantity_score * 0.25
                + coalesce(rrs.avg_reply_discussion_score, 0) * 0.25
                + coalesce(rrs.avg_reply_argument_quality_score, 0) * 0.20
                + coalesce(das.dialogic_attention_score, 3.5) * 0.30
            )::numeric,
            2
        ) as interaction_pertinence_score_v2,
        round(
            (
                vi.evidence_quantity_score * 0.30
                + coalesce(ers.avg_evidence_argument_score, rs.avg_evidence_use_score, 0) * 0.50
                + vi.evidence_coverage_score * 0.20
            )::numeric,
            2
        ) as evidence_argument_score_v2
    from student_base sb
    join v2_inputs vi
        on vi.case_id = sb.case_id
       and vi.user_id = sb.user_id
    left join review_summary rs
        on rs.case_id = sb.case_id
       and rs.user_id = sb.user_id
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
comparison as (
    select
        sb.email,
        sb.full_name,
        sb.role_name,
        coalesce(sa.total_interventions, 0) as total_interventions,
        coalesce(sa.reply_count, 0) as reply_count,
        coalesce(rms.replies_made, 0) as replies_made,
        coalesce(das.replies_received, 0) as replies_received,
        coalesce(das.replies_received_attended, 0) as replies_received_attended,
        coalesce(das.replies_received_unattended, 0) as replies_received_unattended,
        das.dialogic_attention_ratio,
        das.dialogic_attention_score,
        coalesce(sa.evidence_count, 0) as evidence_count,
        coalesce(rs.validated_reviews_count, 0) as validated_reviews_count,
        rs.quality_score,
        v1.participation_score_v1,
        v1.interaction_score_v1,
        v1.evidence_score_v1,
        round(
            (
                coalesce(rs.quality_score, 0) * 0.70
                + v1.participation_score_v1 * 0.15
                + v1.interaction_score_v1 * 0.10
                + v1.evidence_score_v1 * 0.05
            )::numeric,
            2
        ) as total_score_v1,
        v2.participation_incidence_score_v2,
        v2.interaction_pertinence_score_v2,
        v2.evidence_argument_score_v2,
        round(
            (
                coalesce(rs.quality_score, 0) * 0.65
                + v2.participation_incidence_score_v2 * 0.15
                + v2.interaction_pertinence_score_v2 * 0.12
                + v2.evidence_argument_score_v2 * 0.08
            )::numeric,
            2
        ) as total_score_v2
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
    left join dialogic_attention_score das
        on das.case_id = sb.case_id
       and das.user_id = sb.user_id
    left join v1_scores v1
        on v1.case_id = sb.case_id
       and v1.user_id = sb.user_id
    left join v2_scores v2
        on v2.case_id = sb.case_id
       and v2.user_id = sb.user_id
)
select
    dense_rank() over (
        order by total_score_v1 desc nulls last
    )::integer as estimated_position_v1,
    dense_rank() over (
        order by total_score_v2 desc nulls last
    )::integer as estimated_position_v2,
    email,
    full_name,
    role_name,
    total_interventions,
    reply_count,
    replies_made,
    replies_received,
    replies_received_attended,
    replies_received_unattended,
    dialogic_attention_ratio,
    dialogic_attention_score,
    evidence_count,
    validated_reviews_count,
    quality_score,
    participation_score_v1,
    interaction_score_v1,
    evidence_score_v1,
    total_score_v1,
    participation_incidence_score_v2,
    interaction_pertinence_score_v2,
    evidence_argument_score_v2,
    total_score_v2,
    round((total_score_v2 - total_score_v1)::numeric, 2) as score_difference_v2_minus_v1
from comparison
order by estimated_position_v2, total_score_v2 desc, full_name;
