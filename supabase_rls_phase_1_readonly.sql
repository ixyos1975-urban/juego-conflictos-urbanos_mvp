-- Fase 1 de endurecimiento RLS: catalogos de lectura de bajo riesgo.
-- Contexto actual:
-- - La app usa cliente Supabase con rol anon.
-- - La identidad de estudiante/admin vive en Streamlit session_state.
-- - Por eso esta fase solo habilita lectura anon en tablas no sensibles.
--
-- Tablas incluidas:
-- - public.cases
-- - public.roles
-- - public.discussion_threads
--
-- Tablas sensibles expresamente fuera de esta fase:
-- - public.allowed_users
-- - public.profiles
-- - public.role_assignments
-- - public.actor_profiles
-- - public.student_progress
-- - public.interventions
-- - public.evidences
-- - public.teacher_reviews
-- - public.ai_reviews
-- - public.case_ranking

alter table public.cases enable row level security;
alter table public.roles enable row level security;
alter table public.discussion_threads enable row level security;

drop policy if exists "Anon can read cases" on public.cases;
create policy "Anon can read cases"
on public.cases
for select
to anon
using (true);

drop policy if exists "Anon can read roles" on public.roles;
create policy "Anon can read roles"
on public.roles
for select
to anon
using (true);

drop policy if exists "Anon can read discussion threads" on public.discussion_threads;
create policy "Anon can read discussion threads"
on public.discussion_threads
for select
to anon
using (true);

-- No se crean politicas de insert, update ni delete para anon.
-- Con RLS habilitado, la ausencia de politicas de escritura bloquea esas operaciones.
