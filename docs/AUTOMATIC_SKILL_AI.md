# Automatic Skill AI

Nexus Realms resolves combat server-side. Players choose a combat tactic, while the combat engine automatically selects class skills based on the combat state.

## Decision inputs

The automatic selector evaluates player HP, enemy HP, mana, skill cost, cooldowns, boss status, selected tactic, skill role, execution thresholds, armor piercing, critical modifiers and damage reduction.

## Tactics

- **Smart:** adapts to HP, mana, enemy state and boss encounters; it preserves mana when useful and prioritizes defensive skills when HP is low.
- **Balanced:** alternates basic attacks and affordable skills.
- **Aggressive:** prioritizes the strongest available damage skill.
- **Defensive:** conserves mana and favors guard/survival behavior.

## Skill roles

- **Damage:** used when tactic, cooldown and mana allow it.
- **Guard:** prioritized by defensive logic and by Smart mode when HP falls low.
- **Execute:** held until the enemy reaches its execution threshold.

Skills unlock by character level and remain server-authoritative. The client displays the current skill set and AI behavior but does not decide combat outcomes.
