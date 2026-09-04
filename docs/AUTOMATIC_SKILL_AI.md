# Automatic Skill AI

Nexus Realms resolves combat server-side. Players choose a combat tactic, while the combat engine automatically selects class skills from the current combat state.

The selector evaluates player HP, enemy HP, mana, skill cost, cooldowns, boss status, selected tactic, skill role, execution thresholds, armor piercing, critical modifiers and damage reduction.

- **Smart:** adapts to HP, mana, enemy state and boss encounters; it preserves mana when useful and prioritizes defensive skills when HP is low.
- **Balanced:** alternates basic attacks and affordable skills.
- **Aggressive:** prioritizes the strongest available damage skill.
- **Defensive:** conserves mana and favors guard/survival behavior.

Skill roles are **Damage**, **Guard**, and **Execute**. Execute abilities are held until the enemy enters the configured execution threshold. Skills unlock by character level and remain server-authoritative; the client displays the decision rules but does not decide battle outcomes.
