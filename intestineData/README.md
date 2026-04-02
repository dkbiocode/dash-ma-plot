Using a database mariaDB (original), postgres (migration) for the source data.

## Docker and supabase

Using Docker containers, each supabase instance hosts an isolated database.

## Migration to postgres

Install pgloader (brew) to convert schema from mariaDB to postgres.

```
supabase init
supabase start # (gives local DB url to use below):
pgloader mysql://worm:@129.82.XXX.XXX:3307/NishimuraLab postgresql://postgres:postgres@127.0.0.1:54322/postgres
pgloader mysql://worm:@129.82.XXX.XXX:3307/williams2023 postgresql://postgres:postgres@127.0.0.1:54322/postgres
```
