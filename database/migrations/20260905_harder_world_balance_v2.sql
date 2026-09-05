-- Harder world balance v2. Applied to Supabase production on 2026-09-05 UTC.
-- Existing character progress is preserved.

update public.enemy_definitions
set
  hp = greatest(1, ceil(hp * case when is_boss then 1.35 else 1.20 end)::int),
  atk = greatest(1, ceil(atk * case when is_boss then 1.22 else 1.15 end)::int),
  def = greatest(0, ceil(def * case when is_boss then 1.18 else 1.12 end)::int),
  reward_gold = greatest(1, floor(reward_gold * 0.92)::int),
  reward_xp = greatest(1, floor(reward_xp * 0.88)::int);

update public.quests
set target = greatest(1, ceil(target * 1.25)::int);

update public.expedition_definitions
set
  difficulty = difficulty + 1,
  energy_cost = greatest(1, ceil(energy_cost * 1.20)::int);

update public.crafting_recipes
set
  gold_cost = greatest(1, ceil(gold_cost * 1.15)::int),
  energy_cost = energy_cost + 1,
  cost = (
    select jsonb_object_agg(k, to_jsonb(greatest(1, ceil((v::text)::numeric * 1.10)::int)))
    from jsonb_each(cost) as e(k,v)
  ),
  metadata = coalesce(metadata,'{}'::jsonb) || jsonb_build_object('balance','harder_v2');
