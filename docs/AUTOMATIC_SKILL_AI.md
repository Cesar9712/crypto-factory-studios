# Automatic Skill AI

Nexus Realms resolves combat server-side. Players choose a combat tactic, while the combat engine automatically selects class skills based on combat state.

## Decision inputs

The automatic skill selector evaluates:

- current player HP ratio;
- current enemy HP ratio;
- available mana and skill mana cost;
- cooldowns measured in combat turns;
- whether the enemy is a boss;
- selected tactic: Smart, Balanced, Aggressive, or Defensive;
- skill role: damage, guard, or execute;
- execution thresholds, armor piercing, critical modifiers, and damage reduction.

## Tactics

- **Smart:** adapts to HP, mana, enemy state and boss encounters; it reserves mana when appropriate and prioritizes defensive skills when HP is low.
- **Balanced:** alternates basic attacks and affordable abilities.
- **Aggressive:** prioritizes the strongest available damage skill.
- **Defensive:** conserves mana and favors guard/survival behavior.

## Skill roles

- **Damage:** used when the tactic, cooldown and mana budget allow it.
- **Guard:** prioritized by defensive logic and by Smart mode when HP falls low.
- **Execute:** held until the enemy reaches its execution threshold.

Skills unlock by character level and remain server-authoritative. The client only displays the current skill set and AI behavior; it does not decide combat outcomes.
