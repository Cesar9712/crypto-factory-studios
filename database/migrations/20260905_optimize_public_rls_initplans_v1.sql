drop policy if exists profession_talent_progress_read_own on public.profession_talent_progress;
create policy profession_talent_progress_read_own
on public.profession_talent_progress
for select
to authenticated
using (exists (
  select 1 from public.characters c
  where c.id = profession_talent_progress.character_id
    and c.user_id = (select auth.uid())
));

drop policy if exists hunt_assignments_read_own on public.hunt_assignments;
create policy hunt_assignments_read_own
on public.hunt_assignments
for select
to authenticated
using (exists (
  select 1 from public.characters c
  where c.id = hunt_assignments.character_id
    and c.user_id = (select auth.uid())
));
