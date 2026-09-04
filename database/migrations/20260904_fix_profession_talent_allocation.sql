-- Fix PL/pgSQL ambiguity that prevented profession talent points from being spent.
create or replace function public.allocate_profession_talent(p_character uuid, p_talent text)
returns table(talent_id text, new_rank integer, available_points integer)
language plpgsql
security definer
set search_path=public
as $$
declare
  c_level integer;
  p_level integer;
  earned integer;
  spent integer;
  cur_rank integer;
  defrow public.profession_talent_definitions%rowtype;
  prereq_rank integer;
begin
  select c.level into c_level from public.characters c where c.id=p_character for update;
  if c_level is null then raise exception 'Character not found'; end if;

  select d.* into defrow from public.profession_talent_definitions d where d.id=p_talent;
  if not found then raise exception 'Unknown talent'; end if;

  select pp.level into p_level
  from public.profession_progress pp
  where pp.character_id=p_character and pp.profession_key=defrow.profession_key;
  p_level:=coalesce(p_level,1);
  if p_level<defrow.required_profession_level then
    raise exception 'Profession level % required',defrow.required_profession_level;
  end if;

  if defrow.prerequisite_id is not null then
    select ptp.rank into prereq_rank
    from public.profession_talent_progress ptp
    where ptp.character_id=p_character and ptp.talent_id=defrow.prerequisite_id;
    if coalesce(prereq_rank,0)<1 then raise exception 'Prerequisite talent required'; end if;
  end if;

  select ptp.rank into cur_rank
  from public.profession_talent_progress ptp
  where ptp.character_id=p_character and ptp.talent_id=p_talent;
  cur_rank:=coalesce(cur_rank,0);
  if cur_rank>=defrow.max_rank then raise exception 'Talent maxed'; end if;

  earned:=greatest(0,(c_level-1)*2);
  select coalesce(sum(ptp.rank),0)::integer into spent
  from public.profession_talent_progress ptp
  where ptp.character_id=p_character;
  if spent>=earned then raise exception 'No profession talent points available'; end if;

  insert into public.profession_talent_progress as ptp(character_id,talent_id,rank,updated_at)
  values(p_character,p_talent,1,now())
  on conflict on constraint profession_talent_progress_pkey
  do update set rank=ptp.rank+1,updated_at=now();

  cur_rank:=cur_rank+1;
  available_points:=earned-(spent+1);
  talent_id:=p_talent;
  new_rank:=cur_rank;
  return next;
end;
$$;