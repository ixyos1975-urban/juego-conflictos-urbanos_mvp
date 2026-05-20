-- Bloque 14G: cambio obligatorio de contraseña en primer ingreso.
-- Ejecutar en Supabase SQL editor antes de activar la prueba funcional.

begin;

alter table public.allowed_users
add column if not exists must_change_password boolean not null default false;

alter table public.allowed_users
add column if not exists password_changed_at timestamptz;

create or replace function public.mark_password_changed_secure(
    p_email text
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
    v_authenticated_email text;
    v_requested_email text := lower(trim(p_email));
begin
    if v_requested_email is null or v_requested_email = '' then
        raise exception 'Correo no valido para actualizar cambio de contraseña.';
    end if;

    select lower(p.email)
    into v_authenticated_email
    from public.profiles p
    where p.id = auth.uid();

    if v_authenticated_email is null then
        v_authenticated_email := lower(auth.jwt() ->> 'email');
    end if;

    if v_authenticated_email is null
       or v_authenticated_email <> v_requested_email then
        raise exception 'No fue posible registrar el cambio de contraseña para este usuario.';
    end if;

    update public.allowed_users au
    set
        must_change_password = false,
        password_changed_at = now()
    where lower(au.email) = v_authenticated_email
      and coalesce(au.is_active, true) = true;

    if not found then
        raise exception 'No fue posible registrar el cambio de contraseña para este usuario.';
    end if;
end;
$$;

revoke all on function public.mark_password_changed_secure(text) from public;
grant execute on function public.mark_password_changed_secure(text) to authenticated;

update public.allowed_users au
set
    must_change_password = true,
    password_changed_at = null
where au.group_name = 'POT-Grupo_3'
  and coalesce(au.is_active, true) = true
  and coalesce(au.is_admin, false) = false;

notify pgrst, 'reload schema';

commit;
