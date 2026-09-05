create index if not exists phase2_arena_matches_season_idx on public.phase2_arena_matches(season_id);
create index if not exists phase2_arena_matches_winner_idx on public.phase2_arena_matches(winner_id);
create index if not exists phase2_reward_events_character_idx on public.phase2_reward_events(character_id);
create index if not exists phase2_rift_runs_reward_item_idx on public.phase2_rift_runs(reward_item_id) where reward_item_id is not null;
