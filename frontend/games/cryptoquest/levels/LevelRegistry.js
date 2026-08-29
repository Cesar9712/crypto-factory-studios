export class LevelRegistry {
  #levels = new Map();
  register(definition) {
    if (!definition?.id) throw new Error('Level id required');
    this.#levels.set(definition.id, structuredClone(definition));
    return definition.id;
  }
  get(id) { const level = this.#levels.get(id); return level ? structuredClone(level) : null; }
  has(id) { return this.#levels.has(id); }
  list() { return [...this.#levels.values()].map(level => structuredClone(level)); }
  clear() { this.#levels.clear(); }
}
