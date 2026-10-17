#!/bin/bash
# Inicialización del PostgreSQL de datos. Se ejecuta solo cuando el volumen está vacío.
# - admin (POSTGRES_USER): dueño de las bases; prepara la fuente y el esquema del DW.
# - etl_user: el pipeline. Solo lectura en la fuente; DML en el DW.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v admin_user="$POSTGRES_USER" \
  -v etl_user="$ETL_DB_USER" \
  -v etl_pass="$ETL_DB_PASSWORD" \
  -v source_db="$SOURCE_DB_NAME" \
  -v dw_db="$DW_DB_NAME" <<'EOSQL'
CREATE ROLE :"etl_user" LOGIN PASSWORD :'etl_pass';

CREATE DATABASE :"source_db" OWNER :"admin_user";
CREATE DATABASE :"dw_db" OWNER :"admin_user";

REVOKE ALL ON DATABASE :"source_db" FROM PUBLIC;
REVOKE ALL ON DATABASE :"dw_db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"source_db" TO :"etl_user";
GRANT CONNECT ON DATABASE :"dw_db" TO :"etl_user";

-- Fuente: el pipeline solo lee
\connect :source_db
GRANT USAGE ON SCHEMA public TO :"etl_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"admin_user" IN SCHEMA public
  GRANT SELECT ON TABLES TO :"etl_user";

-- DW: el pipeline carga (el esquema lo crea admin con sql/dw_schema.sql)
\connect :dw_db
GRANT USAGE ON SCHEMA public TO :"etl_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"admin_user" IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO :"etl_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"admin_user" IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO :"etl_user";
EOSQL
