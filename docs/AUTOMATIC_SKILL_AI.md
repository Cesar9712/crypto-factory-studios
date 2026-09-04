# Automatic Skill AI

Nexus Realms resolves combat server-side. Players choose a combat tactic, while the combat engine automatically selects class skills based on combat state.

## Decision inputs

The automatic skill selector evaluates:

- current player HP ratio;
- current enemy HP ratio;
- available mana;
- skill mana cost;
- skill cooldown in turns;
- whether the enemy is a boss;
- combat tactic: Smart, Balanced, Aggressive, Defensive;
- skill role: damage, guard, execute;
- execution thresholds and armor-piercing/critical modifiers.

## Tactics

- **Smart:** adapts to HP, mana, enemy state and boss encounters. It reserves mana when appropriate and prioritizes defensive skills when HP is low.
- **Balanced:** alternates basic attacks and affordable abilities.
- **Aggressive:** prioritizes the strongest available damage skill.
- **Defensive:** conserves mana and favors guard/survival behavior.

## Skill roles

- **Damage:** used when the tactic and mana budget allow it.
- **Guard:** prioritized by defensive logic and by Smart mode when HP falls low.
- **Execute:** held until the enemy reaches its execution threshold.

Skills are unlocked by character level and remain server-authoritative. The client only displays the current skill set and AI behavior; it does not decide combat outcomes.
