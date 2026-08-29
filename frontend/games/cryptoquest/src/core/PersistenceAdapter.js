export class PersistenceAdapter {
  constructor({ key = 'cryptoquest:state', storage = localStorage, schemaVersion = 1 } = {}) {
    this.key = key;
    this.storage = storage;
    this.schemaVersion = schemaVersion;
  }

  load(fallback = {}) {
    try {
      const raw = this.storage.getItem(this.key);
      if (!raw) return structuredClone(fallback);
      const envelope = JSON.parse(raw);
      if (!envelope || typeof envelope !== 'object') return structuredClone(fallback);
      return envelope.data ?? structuredClone(fallback);
    } catch {
      return structuredClone(fallback);
    }
  }

  save(state) {
    const envelope = {
      schemaVersion: this.schemaVersion,
      savedAt: Date.now(),
      data: state,
    };
    this.storage.setItem(this.key, JSON.stringify(envelope));
    return envelope;
  }

  remove() { this.storage.removeItem(this.key); }
}
