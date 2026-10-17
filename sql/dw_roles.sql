-- Rol de solo lectura para el dashboard (mínimo privilegio). Se ejecuta como admin, una vez por base.
-- Uso: psql -v ON_ERROR_STOP=1 -v dash_pw=... -f dw_roles.sql
-- La contraseña no se versiona: se guarda en .env (DASHBOARD_PASSWORD).
\set ON_ERROR_STOP on

SELECT 'CREATE ROLE dashboard_user LOGIN'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dashboard_user') \gexec

SELECT format('ALTER ROLE dashboard_user PASSWORD %L', :'dash_pw') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO dashboard_user', current_database()) \gexec
GRANT USAGE ON SCHEMA public TO dashboard_user;
