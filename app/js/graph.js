/**
 * Ski routing graph with Dijkstra's algorithm.
 *
 * The graph models the La Plagne ski area as a directed graph:
 * - Nodes = physical locations (lift stations, slope endpoints, villages)
 * - Edges = lifts (directed uphill) and slopes (directed downhill)
 *
 * Dijkstra's algorithm finds the shortest path (by estimated travel time)
 * while respecting slope color filters.
 */

class MinPriorityQueue {
    constructor() {
        this.heap = [];
    }

    insert(key, priority) {
        this.heap.push({ key, priority });
        this._bubbleUp(this.heap.length - 1);
    }

    extractMin() {
        if (this.heap.length === 0) return null;
        const min = this.heap[0];
        const last = this.heap.pop();
        if (this.heap.length > 0) {
            this.heap[0] = last;
            this._sinkDown(0);
        }
        return min.key;
    }

    isEmpty() {
        return this.heap.length === 0;
    }

    _bubbleUp(i) {
        while (i > 0) {
            const parent = Math.floor((i - 1) / 2);
            if (this.heap[parent].priority <= this.heap[i].priority) break;
            [this.heap[parent], this.heap[i]] = [this.heap[i], this.heap[parent]];
            i = parent;
        }
    }

    _sinkDown(i) {
        const n = this.heap.length;
        while (true) {
            let smallest = i;
            const left = 2 * i + 1;
            const right = 2 * i + 2;
            if (left < n && this.heap[left].priority < this.heap[smallest].priority) smallest = left;
            if (right < n && this.heap[right].priority < this.heap[smallest].priority) smallest = right;
            if (smallest === i) break;
            [this.heap[smallest], this.heap[i]] = [this.heap[i], this.heap[smallest]];
            i = smallest;
        }
    }
}


class SkiGraph {
    constructor(graphData) {
        this.nodes = graphData.nodes;
        this.edges = graphData.edges;
        this.metadata = graphData.metadata;

        // Build edge lookup by ID
        this.edgesById = {};
        for (const edge of this.edges) {
            this.edgesById[edge.id] = edge;
        }

        // Build adjacency list
        this.adjacency = {};
        for (const nodeId in this.nodes) {
            this.adjacency[nodeId] = [];
        }
        for (const edge of this.edges) {
            if (this.adjacency[edge.source]) {
                this.adjacency[edge.source].push({
                    target: edge.target,
                    edgeId: edge.id,
                });
            }
        }
    }

    /**
     * Calculate edge weight (estimated travel time in minutes).
     */
    calculateWeight(edge, excludedColors) {
        // If this slope color is excluded, make it impassable
        if (edge.type === 'slope' && excludedColors.has(edge.difficulty)) {
            return Infinity;
        }

        if (edge.type === 'slope') {
            // Speed in meters per minute by difficulty
            const speeds = { green: 200, blue: 250, red: 300, black: 200 };
            const speed = speeds[edge.difficulty] || 200;
            return edge.distance / speed;
        }

        if (edge.type === 'lift') {
            // Lift speed in meters per minute by type
            const speeds = {
                drag_lift: 100,
                chair_lift: 150,
                gondola: 200,
                cable_car: 250,
                magic_carpet: 50,
            };
            const speed = speeds[edge.liftType] || 150;
            const travelTime = edge.distance / speed;
            const queueTime = 3; // 3 minute average queue
            return travelTime + queueTime;
        }

        return edge.distance / 150; // fallback
    }

    /**
     * Find the shortest route between two nodes.
     *
     * @param {string} startNodeId - Starting node ID
     * @param {string} endNodeId - Ending node ID
     * @param {Set<string>} excludedColors - Set of slope colors to avoid
     * @returns {Object|null} Route object or null if no path found
     */
    findRoute(startNodeId, endNodeId, excludedColors) {
        if (startNodeId === endNodeId) {
            return { error: 'same_location' };
        }

        const dist = {};
        const prev = {};
        const prevEdge = {};
        const visited = new Set();
        const pq = new MinPriorityQueue();

        // Initialize
        for (const nodeId in this.nodes) {
            dist[nodeId] = Infinity;
        }
        dist[startNodeId] = 0;
        pq.insert(startNodeId, 0);

        // Dijkstra's main loop
        while (!pq.isEmpty()) {
            const u = pq.extractMin();

            if (u === endNodeId) break;
            if (visited.has(u)) continue;
            visited.add(u);

            for (const neighbor of this.adjacency[u] || []) {
                const edge = this.edgesById[neighbor.edgeId];
                const w = this.calculateWeight(edge, excludedColors);
                if (w === Infinity) continue;

                const alt = dist[u] + w;
                if (alt < dist[neighbor.target]) {
                    dist[neighbor.target] = alt;
                    prev[neighbor.target] = u;
                    prevEdge[neighbor.target] = neighbor.edgeId;
                    pq.insert(neighbor.target, alt);
                }
            }
        }

        // No path found
        if (dist[endNodeId] === Infinity) {
            return { error: 'no_route' };
        }

        // Reconstruct path
        const path = [];
        const edgePath = [];
        let current = endNodeId;

        while (current !== startNodeId) {
            path.unshift(current);
            edgePath.unshift(prevEdge[current]);
            current = prev[current];
        }
        path.unshift(startNodeId);

        // Build route details
        const steps = edgePath.map(edgeId => {
            const edge = this.edgesById[edgeId];
            const weight = this.calculateWeight(edge, excludedColors);
            return {
                edgeId: edge.id,
                name: edge.name || 'Unnamed',
                type: edge.type,
                difficulty: edge.difficulty || null,
                liftType: edge.liftType || null,
                distance: edge.distance,
                elevationDelta: edge.elevationDelta,
                estimatedMinutes: Math.round(weight * 10) / 10,
                geometry: edge.geometry,
                sourceNode: edge.source,
                targetNode: edge.target,
            };
        });

        // Calculate totals
        let totalDistance = 0;
        let totalTime = 0;
        let totalUp = 0;
        let totalDown = 0;

        for (const step of steps) {
            totalDistance += step.distance;
            totalTime += step.estimatedMinutes;
            if (step.elevationDelta > 0) {
                totalUp += step.elevationDelta;
            } else {
                totalDown += Math.abs(step.elevationDelta);
            }
        }

        // Build elevation profile data points
        const elevationProfile = this._buildElevationProfile(path, steps);

        return {
            path,
            steps,
            elevationProfile,
            summary: {
                totalDistance: Math.round(totalDistance),
                totalTime: Math.round(totalTime),
                totalUp: Math.round(totalUp),
                totalDown: Math.round(totalDown),
                stepCount: steps.length,
            },
        };
    }

    /**
     * Build elevation profile data for the route.
     */
    _buildElevationProfile(path, steps) {
        const points = [];
        let cumulativeDistance = 0;

        // First node
        const firstNode = this.nodes[path[0]];
        points.push({
            distance: 0,
            elevation: firstNode.ele,
            nodeId: path[0],
            isNode: true,
            type: null,
            difficulty: null,
        });

        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];
            const targetNode = this.nodes[step.targetNode];

            // Add intermediate geometry points for smoother profile
            if (step.geometry && step.geometry.length > 2) {
                const sourceEle = this.nodes[step.sourceNode].ele;
                const targetEle = targetNode.ele;
                const geomLen = step.geometry.length;

                for (let g = 1; g < geomLen - 1; g++) {
                    const frac = g / (geomLen - 1);
                    const segDist = step.distance * frac;
                    const interpEle = sourceEle + (targetEle - sourceEle) * frac;

                    points.push({
                        distance: cumulativeDistance + segDist,
                        elevation: Math.round(interpEle),
                        isNode: false,
                        type: step.type,
                        difficulty: step.difficulty,
                    });
                }
            }

            cumulativeDistance += step.distance;

            points.push({
                distance: cumulativeDistance,
                elevation: targetNode.ele,
                nodeId: step.targetNode,
                isNode: true,
                type: step.type,
                difficulty: step.difficulty,
            });
        }

        return points;
    }

    /**
     * Get all selectable locations grouped by category.
     */
    getSelectableLocations() {
        const stations = [];
        const slopeBottoms = [];
        const slopeTops = [];
        const liftBottoms = [];
        const liftTops = [];

        // Stations
        for (const [nodeId, node] of Object.entries(this.nodes)) {
            if (node.station) {
                stations.push({
                    nodeId,
                    label: `${node.station} (${node.ele}m)`,
                    name: node.station,
                    ele: node.ele,
                });
            }
        }
        stations.sort((a, b) => a.name.localeCompare(b.name));

        // Slopes and Lifts
        const seenSlopeTops = new Set();
        const seenSlopeBottoms = new Set();
        const seenLiftTops = new Set();
        const seenLiftBottoms = new Set();

        for (const edge of this.edges) {
            const sourceNode = this.nodes[edge.source];
            const targetNode = this.nodes[edge.target];

            if (edge.type === 'slope') {
                const topKey = edge.source;
                const bottomKey = edge.target;

                if (!seenSlopeTops.has(topKey) && edge.name) {
                    seenSlopeTops.add(topKey);
                    slopeTops.push({
                        nodeId: topKey,
                        label: `${edge.name} - top (${sourceNode.ele}m)`,
                        name: edge.name,
                        ele: sourceNode.ele,
                    });
                }

                if (!seenSlopeBottoms.has(bottomKey) && edge.name) {
                    seenSlopeBottoms.add(bottomKey);
                    slopeBottoms.push({
                        nodeId: bottomKey,
                        label: `${edge.name} - bottom (${targetNode.ele}m)`,
                        name: edge.name,
                        ele: targetNode.ele,
                    });
                }
            }

            if (edge.type === 'lift') {
                const bottomKey = edge.source;
                const topKey = edge.target;

                if (!seenLiftBottoms.has(bottomKey) && edge.name) {
                    seenLiftBottoms.add(bottomKey);
                    liftBottoms.push({
                        nodeId: bottomKey,
                        label: `${edge.name} - bottom (${sourceNode.ele}m)`,
                        name: edge.name,
                        ele: sourceNode.ele,
                    });
                }

                if (!seenLiftTops.has(topKey) && edge.name) {
                    seenLiftTops.add(topKey);
                    liftTops.push({
                        nodeId: topKey,
                        label: `${edge.name} - top (${targetNode.ele}m)`,
                        name: edge.name,
                        ele: targetNode.ele,
                    });
                }
            }
        }

        // Sort by name
        const byName = (a, b) => a.name.localeCompare(b.name);
        slopeTops.sort(byName);
        slopeBottoms.sort(byName);
        liftTops.sort(byName);
        liftBottoms.sort(byName);

        return { stations, slopeTops, slopeBottoms, liftTops, liftBottoms };
    }
}
