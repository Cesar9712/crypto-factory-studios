export class StateMachine {
  #state;
  #transitions;
  #bus;
  #context;

  constructor({ initial, transitions, context = {}, bus = null }) {
    if (!initial) throw new Error('StateMachine requires an initial state');
    this.#state = initial;
    this.#transitions = transitions ?? {};
    this.#context = context;
    this.#bus = bus;
  }

  get state() { return this.#state; }
  get context() { return this.#context; }
  can(event) { return Boolean(this.#transitions[this.#state]?.[event]); }

  send(event, payload) {
    const rule = this.#transitions[this.#state]?.[event];
    if (!rule) return false;
    const descriptor = typeof rule === 'string' ? { target: rule } : rule;
    if (descriptor.guard && !descriptor.guard(this.#context, payload)) return false;
    const previous = this.#state;
    descriptor.action?.(this.#context, payload);
    this.#state = descriptor.target ?? previous;
    this.#bus?.emit('fsm:transition', { machine: this, event, previous, next: this.#state, payload });
    return true;
  }
}
