export { ApiClient } from '../src/core/ApiClient.js';

export class NetworkFacade {
  constructor({ api }) { this.api = api; }
  health() { return this.api.get('/health'); }
  ready() { return this.api.get('/ready'); }
}
