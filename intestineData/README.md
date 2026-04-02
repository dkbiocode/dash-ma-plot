# decided to use supabase, therefore, downloaded pgloader (brew) and did the following:
supabase init
supabase start (gives local DB url to use below):
pgloader mysql://worm:@129.82.125.11:3307/NishimuraLab postgresql://postgres:postgres@127.0.0.1:54322/postgres
pgloader mysql://worm:@129.82.125.11:3307/williams2023 postgresql://postgres:postgres@127.0.0.1:54322/postgres
