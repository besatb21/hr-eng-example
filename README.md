
# Ask
Choose one of the two components (frontend, backend) and choose a task. 
You can create an implementation or a design description.
If you choose to use AI Agents or Copilot, please highlight your prompts and thought process.
Send your contribution before the in-person meeting. We will talk about your solution.
There is no right or wrong. We are curious about problem solving capabilities.

# Backend

## Task:
Choose 3-5

[X] Scheduler (nearest-idle): Implement assign_nearest_idle_robot(order) using shortest-path to the order’s source, tie-break by robot name; flip statuses (NEW→IN_PROGRESS, robot IDLE→EXECUTING) and store the planned route.

[X] Pathfinding: Add Dijkstra/A* over the provided graph (bidirectional edges, weight as cost). Return both distance and path.

[X] Tick simulation: POST /tick advances time by one “step”; robots move one edge per tick, update their node; when reaching target, mark order DONE, robot IDLE.

[X] State & validation: Validate nodes exist; keep state in memory; guard against duplicate order names; return helpful 4xx errors.

[X] OpenAPI polish: Ensure models/enums are documented; add tags and examples; verify with /docs.

[X] Deterministic tests: Unit tests for pathfinding, scheduling, and reservations; seed test graph/robots; use property tests for “path cost monotonicity”.


#### Nice-to-haves

[] Collision avoidance (edge reservations): Prevent two robots from occupying the same edge in the same tick; simple time-slot reservation is enough (defer one robot if conflict).

[] Batch scheduling: On each tick, try to assign all NEW orders (recompute as robots free up).

[] Preemption guardrails: Don’t reassign an order already IN_PROGRESS; allow manual cancellation path to set FAILED.

[] Audit log: Append events (order created/assigned/finished, robot moved) and expose GET /events?since=…&limit=….

#### Stretch goals

[] Charging logic: Add battery (0–100). Drain per tick; when <20%, send to nearest “charger” node; pause scheduling while charging; resume at >80%.

[] Priorities & SLAs: Orders get priority (int) and optional deadline. Scheduler prefers higher priority, then nearest distance; mark FAILED if deadline exceeded.

[] Zones/blocked edges: Support temporarily blocked edges (maintenance) and zone constraints (e.g., robots with capability: {zone: 'cold'} only).

[X] Persistence: Swap in SQLite or TinyDB; add /reset to re-seed for tests.

[] WebSocket/SSE: Push robot/ order updates instead of polling; keep /tick but notify subscribers.


## Acceptance:

- App loads graph and lists robots + orders.
- Adding an order triggers scheduling when an IDLE robot exists.
- Robots visibly move along paths over time; orders progress to DONE.
- No runtime errors; basic empty/error states handled.


# Probable Questions
- What challenges do you foresee and why?
