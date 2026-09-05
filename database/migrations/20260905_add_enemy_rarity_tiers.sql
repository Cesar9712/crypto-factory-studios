update public.enemy_definitions
set metadata = coalesce(metadata, '{}'::jsonb) || jsonb_build_object(
  'rarity',
  case
    when is_boss and level >= 17 then 'MYTHIC'
    when is_boss and level >= 12 then 'LEGENDARY'
    when is_boss and level >= 7 then 'EPIC'
    when is_boss then 'RARE'
    when level >= 16 then 'LEGENDARY'
    when level >= 11 then 'EPIC'
    when level >= 7 then 'RARE'
    when level >= 4 then 'UNCOMMON'
    else 'COMMON'
  end,
  'rarity_rank',
  case
    when is_boss and level >= 17 then 6
    when is_boss and level >= 12 then 5
    when is_boss and level >= 7 then 4
    when is_boss then 3
    when level >= 16 then 5
    when level >= 11 then 4
    when level >= 7 then 3
    when level >= 4 then 2
    else 1
  end
);