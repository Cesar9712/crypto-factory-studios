export class Scheduler {
  #raf = new Map();
  #timers = new Map();

  frame(key, callback) {
    if (this.#raf.has(key)) return;
    const id = requestAnimationFrame((time) => {
      this.#raf.delete(key);
      callback(time);
    });
    this.#raf.set(key, id);
  }

  debounce(key, callback, delay = 0) {
    if (this.#timers.has(key)) clearTimeout(this.#timers.get(key));
    const id = setTimeout(() => {
      this.#timers.delete(key);
      callback();
    }, delay);
    this.#timers.set(key, id);
  }

  cancel(key) {
    if (this.#raf.has(key)) cancelAnimationFrame(this.#raf.get(key));
    if (this.#timers.has(key)) clearTimeout(this.#timers.get(key));
    this.#raf.delete(key);
    this.#timers.delete(key);
  }

  dispose() {
    for (const id of this.#raf.values()) cancelAnimationFrame(id);
    for (const id of this.#timers.values()) clearTimeout(id);
    this.#raf.clear();
    this.#timers.clear();
  }
}
