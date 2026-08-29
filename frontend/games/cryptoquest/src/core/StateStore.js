export class StateStore {
  #state;
  #bus;
  #version = 0;

  constructor(initialState = {}, bus = null) {
    this.#state = structuredClone(initialState);
    this.#bus = bus;
  }

  get version() { return this.#version; }
  getState() { return structuredClone(this.#state); }
  select(selector) { return selector(this.#state); }

  replace(nextState, meta = {}) {
    const previous = this.#state;
    this.#state = structuredClone(nextState);
    this.#version += 1;
    this.#bus?.emit('state:changed', { previous, next: this.#state, version: this.#version, meta });
  }

  update(recipe, meta = {}) {
    const draft = structuredClone(this.#state);
    const result = recipe(draft);
    this.replace(result === undefined ? draft : result, meta);
  }
}
