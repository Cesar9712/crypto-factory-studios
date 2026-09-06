begin;

-- Client gameplay only needs row-level DML governed by RLS or server-side Edge RPCs.
-- TRUNCATE is not governed by row policies; TRIGGER and REFERENCES are also not
-- required by any browser gameplay path. Remove those privileges everywhere.
revoke truncate, trigger, references on all tables in schema public from public, anon, authenticated;
alter default privileges in schema public revoke truncate, trigger, references on tables from public, anon, authenticated;

commit;
