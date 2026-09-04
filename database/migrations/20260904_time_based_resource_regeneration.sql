-- HP, mana and energy recovery is server-authoritative and time-based.
-- No button press, victory or level-up grants instant regeneration.

alter table public.characters
  add column if not exists mana integer not null default 60,
  add column if not exists max_mana integer not null default 60,
  add column if not exists regen_boost_until timestamptz;

update public.characters
set max_mana = case class
  when 'mage' then 150
  when 'archer' then 80
  when 'assassin' then 70
  else 40
end,
mana = least(
  case class
    when 'mage' then 150
    when 'archer' then 80
    when 'assassin' then 70
    else 40
  end,
  greatest(0, mana)
);

alter table public.characters
  drop constraint if exists characters_mana_bounds,
  add constraint characters_mana_bounds
    check (mana >= 0 and max_mana > 0 and mana <= max_mana);

comment on column public.characters.last_tick is
  'Server-authoritative timestamp consumed in whole-minute ticks for HP, mana and energy regeneration.';
comment on column public.characters.regen_boost_until is
  'Optional timed regeneration boost; never grants resources instantly.';
