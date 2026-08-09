---
id: BLK-145
type: tech-debt
title: "GraphML and DEXPI serializers use edges.index(edge) — O(n²) edge ID generation"
priority: low
status: backlog
phase: 4
owner: backend
created: 2026-08-08T14:45:00+05:30
estimate: S
tags: [backend, performance, graph-tools, tech-debt]
---

## Problem

`_serialize_graphml` and `_serialize_dexpi` in
`src/tools/graph/serialization.py` use `edges.index(edge)` to generate
edge IDs when the edge doesn't have an explicit `id` field. This is
O(n) per edge, making the overall serialization O(n²) in the number
of edges.

## Evidence

`src/tools/graph/serialization.py:82`:
```python
edge_id = edge.get("id", f"e{edges.index(edge)}")
```

`src/tools/graph/serialization.py:132`:
```python
edge_id = edge.get("id", f"p{edges.index(edge)}")
```

`list.index()` performs a linear scan using `==` comparison. For a
graph with N edges, this is O(N) per edge, resulting in O(N²) total.

## Impact

For large P&ID diagrams with hundreds or thousands of connections,
serialization will be noticeably slow. The issue is masked in testing
because test graphs are small. In production with real engineering
diagrams, this could cause multi-second delays.

## Reproduction or reasoning

1. Create a graph with 1000 edges, none having explicit `id` fields.
2. Call `serialize_graph(graph, format="graphml")`.
3. Time the serialization — O(n²) will be evident.

## Proposed resolution

Use `enumerate()` instead of `edges.index(edge)`:

```python
for i, edge in enumerate(edges):
    edge_id = edge.get("id", f"e{i}")
```

## Acceptance criteria

- [ ] No `edges.index(edge)` calls in serialization code
- [ ] Edge IDs are generated with `enumerate()` — O(n) total
- [ ] Existing tests pass with the same edge ID format

## Validation plan

- Run existing graph tool tests
- Benchmark with a large graph (1000+ edges) to verify O(n) behavior

## Related issues

BLK-110 (graph extraction tools)
