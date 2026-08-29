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

  #commit(nextState, meta = {}) {
    const previous = this.#state;
    this.#state = nextState;
    this.#version += 1;
    this.#bus?.emit('state:changed', { previous, next: this.#state, version: this.#version, meta });
  }

  replace(nextState, meta = {}) { this.#commit(structuredClone(nextState), meta); }

  update(recipe, meta = {}) {
    const draft = structuredClone(this.#state);
    const result = recipe(draft);
    this.#commit(result === undefined ? draft : structuredClone(result), meta);
  }
}
