# Experiment: Leaflet Marker Rendering Performance

## Background

When icon shape support was added (switching from `L.circleMarker` to `L.marker` + `L.divIcon`),
map panning became noticeably less smooth. This experiment quantifies the performance difference
between the three Leaflet marker rendering strategies to inform the implementation decision.

## Hypothesis

Canvas circleMarker renders faster than SVG circleMarker, which renders significantly faster
than DOM-based divIcon — especially at high marker density.

## Test Setup

- **Dataset**: `data/features.geojson` (~28,000 markers, all categories)
- **Clustering**: None (plain `L.layerGroup`) — maximises rendering stress
- **Initial view**: Tokyo (35.72, 139.78), zoom 13 — densest area (1,439 markers in 0.1°×0.1°)
- **Benchmark page**: `benchmarks/leaflet-marker-rendering.html`

## Approaches Compared

| Mode | Leaflet API | Renderer | Notes |
|------|-------------|----------|-------|
| Canvas | `L.circleMarker` | `preferCanvas: true` | All paths on one `<canvas>` |
| SVG | `L.circleMarker` | SVG (default) | All paths in one `<svg>` |
| divIcon | `L.marker` + inline SVG `L.divIcon` | DOM | One `<div>` per marker |

## Metrics

| Metric | Method |
|--------|--------|
| Load time | `performance.now()` around `layer.addLayer()` loop |
| Drag latency | `mousedown` → first `map.on('move')` → double `requestAnimationFrame` (waits for frame commit) |
| FPS | `requestAnimationFrame` 10-frame rolling average, displayed live |

### Drag Latency — Safari Caveat

Safari's GPU compositing runs in a separate process. The double-rAF callback fires on the JS side
before pixels actually reach the screen, so measured drag latency on Safari is systematically
lower than subjective latency. Chrome and Firefox are accurate; **on Safari, treat the number as
a lower bound and rely on subjective feel.**

## How to Run

```sh
python3 -m http.server 8080
# open http://localhost:8080/benchmarks/leaflet-marker-rendering.html
```

Select a mode → click **Reload with this mode** → pan and zoom around Tokyo.

## Conclusion

Canvas circleMarker chosen for `map.html` — retains `L.circleMarker` API and adds
`preferCanvas: true` to `L.map` options. Shape differentiation per category group was
abandoned; all markers render as circles. Group membership is shown via sidebar headings only.
