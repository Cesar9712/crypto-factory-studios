export class MapGraphService {
  constructor({ store, bus }) { this.store = store; this.bus = bus; }

  registerGraph(graph) {
    if (!graph?.id || !Array.isArray(graph.nodes)) throw new Error('Map graph requires id and nodes');
    const nodeIds = new Set(graph.nodes.map(node => node.id));
    for (const edge of graph.edges ?? []) {
      if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to)) throw new Error(`Invalid edge ${edge.from} -> ${edge.to}`);
    }
    this.store.update(state => {
      state.world ??= { graphs: {}, currentGraphId: null, currentNodeId: null, unlockedNodes: {} };
      state.world.graphs[graph.id] = structuredClone(graph);
      state.world.currentGraphId ??= graph.id;
      const start = graph.startNodeId ?? graph.nodes[0]?.id ?? null;
      state.world.currentNodeId ??= start;
      if (start) state.world.unlockedNodes[`${graph.id}:${start}`] = true;
    }, { source: 'map:register', graphId: graph.id });
  }

  canTravel(graphId, targetNodeId) {
    const state = this.store.getState();
    const world = state.world ?? {};
    const graph = world.graphs?.[graphId];
    if (!graph) return false;
    if (!world.unlockedNodes?.[`${graphId}:${targetNodeId}`]) return false;
    const current = world.currentNodeId;
    if (!current) return targetNodeId === (graph.startNodeId ?? graph.nodes[0]?.id);
    return (graph.edges ?? []).some(edge =>
      (edge.from === current && edge.to === targetNodeId) ||
      (!edge.directed && edge.to === current && edge.from === targetNodeId)
    );
  }

  travel(graphId, targetNodeId) {
    if (!this.canTravel(graphId, targetNodeId)) throw new Error(`Travel blocked: ${targetNodeId}`);
    this.store.update(state => {
      state.world.currentGraphId = graphId;
      state.world.currentNodeId = targetNodeId;
    }, { source: 'map:travel', graphId, targetNodeId });
    this.bus?.emit('map:travelled', { graphId, targetNodeId });
  }

  unlock(graphId, nodeId) {
    this.store.update(state => {
      state.world ??= { graphs: {}, currentGraphId: null, currentNodeId: null, unlockedNodes: {} };
      state.world.unlockedNodes[`${graphId}:${nodeId}`] = true;
    }, { source: 'map:unlock', graphId, nodeId });
    this.bus?.emit('map:node-unlocked', { graphId, nodeId });
  }
}
