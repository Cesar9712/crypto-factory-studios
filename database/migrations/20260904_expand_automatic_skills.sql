-- Expanded automatic skill roster for all launch classes.
-- Skills remain server-authoritative and use internal game resources only.
insert into public.skill_definitions (id,class,name,metadata) values
('warrior-shield-bash','warrior','Shield Bash','{"kind":"guard","name_es":"Golpe de Escudo","mana_cost":5,"min_level":3,"multiplier":1.25,"cooldown_turns":2,"damage_reduction":0.72,"armor_pierce":0.10}'::jsonb),
('warrior-berserker-rage','warrior','Berserker Rage','{"kind":"damage","name_es":"Furia Berserker","mana_cost":20,"min_level":12,"multiplier":3.10,"cooldown_turns":5,"crit_bonus":0.08}'::jsonb),
('mage-chain-lightning','mage','Chain Lightning','{"kind":"damage","name_es":"Relámpago Encadenado","mana_cost":14,"min_level":3,"multiplier":1.95,"cooldown_turns":2,"crit_bonus":0.05}'::jsonb),
('mage-arcane-nova','mage','Arcane Nova','{"kind":"damage","name_es":"Nova Arcana","mana_cost":28,"min_level":12,"multiplier":3.00,"cooldown_turns":5,"armor_pierce":0.20}'::jsonb),
('archer-hunters-mark','archer','Hunter''s Mark','{"kind":"damage","name_es":"Marca del Cazador","mana_cost":8,"min_level":3,"multiplier":1.65,"cooldown_turns":2,"armor_pierce":0.22}'::jsonb),
('archer-rain-of-arrows','archer','Rain of Arrows','{"kind":"damage","name_es":"Lluvia de Flechas","mana_cost":24,"min_level":12,"multiplier":2.80,"cooldown_turns":5,"crit_bonus":0.06}'::jsonb),
('assassin-smoke-veil','assassin','Smoke Veil','{"kind":"guard","name_es":"Velo de Humo","mana_cost":9,"min_level":3,"multiplier":1.15,"cooldown_turns":3,"damage_reduction":0.50}'::jsonb),
('assassin-death-mark','assassin','Death Mark','{"kind":"execute","name_es":"Marca de Muerte","mana_cost":24,"min_level":12,"multiplier":3.20,"cooldown_turns":5,"execute_threshold":0.50,"crit_bonus":0.12}'::jsonb)
on conflict (id) do update set class=excluded.class,name=excluded.name,metadata=excluded.metadata;