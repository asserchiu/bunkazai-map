# Decisions

This file records data analysis findings and key decisions made for the project.

## Data Analysis (2026-03-08)

### Source

Bulk CSV export from 国指定文化財等データベース:
`https://kunishitei.bunka.go.jp/utile/csv-list`

Combined file: `download.csv` — 19 categories, 37,081 total records as of analysis date.

Columns: `台帳ID`, `管理対象ID`, `名称`, `棟名`, `文化財種類`, `種別1`, `種別2`, `国`, `時代`,
`重文指定年月日`, `国宝指定年月日`, `都道府県・地域`, `所在地`, `保管施設の名称`, `所有者名`,
`管理団体又は責任者`, `緯度`, `経度`

### Coordinate Coverage by Category

| Category (文化財種類) | Total | With Coords | Coverage |
|---|---:|---:|---:|
| 登録有形文化財(建造物) | 14,759 | 14,544 | 98.5% |
| 国宝・重要文化財（美術工芸品） | 11,513 | 4,289 | 37.3% |
| 国宝・重要文化財（建造物） | 5,523 | 5,522 | 100.0% |
| 史跡名勝天然記念物 | 3,262 | 3,106 | 95.2% |
| 記録作成等の措置を講ずべき無形の民俗文化財 | 661 | 19 | 2.9% |
| 重要無形民俗文化財 | 337 | 166 | 49.3% |
| 重要有形民俗文化財 | 228 | 217 | 95.2% |
| 登録記念物 | 140 | 121 | 86.4% |
| 記録作成等の措置を講ずべき無形文化財 | 132 | 0 | 0.0% |
| 重要伝統的建造物群保存地区 | 126 | 126 | 100.0% |
| 重要無形文化財 | 101 | 0 | 0.0% |
| 選定保存技術 | 83 | 0 | 0.0% |
| 重要文化的景観 | 71 | 55 | 77.5% |
| 登録有形民俗文化財 | 52 | 49 | 94.2% |
| 登録美術品 | 40 | 30 | 75.0% |
| 世界遺産 | 21 | 21 | 100.0% |
| 登録有形文化財（美術工芸品） | 18 | 16 | 88.9% |
| 登録無形文化財 | 7 | 0 | 0.0% |
| 登録無形民俗文化財 | 7 | 7 | 100.0% |
| **Total** | **37,081** | **~28,288** | **76.3%** |

Categories with 0 coordinate coverage (重要無形文化財, 選定保存技術, 登録無形文化財,
記録作成等の措置を講ずべき無形文化財) are intangible properties — no fixed location by nature.

### Coordinate Outlier Filter

Raw data contains outliers (e.g. minimum longitude 39.541° — likely lat/lon swap errors).
Applied bounds filter:

- Latitude: 20.0 – 47.0 (Okinawa to Hokkaido)
- Longitude: 120.0 – 155.0 (Ryukyu to Minami Torishima)

## Key Decisions

### ID Fields and Detail URL

- `台帳ID` = category code (e.g. `102` for 国宝・重要文化財（建造物）). Stored as string.
- `管理対象ID` = per-item ID within the category. Stored as **string** to preserve leading zeros.
- Detail URL: `https://kunishitei.bunka.go.jp/heritage/detail/{台帳ID}/{管理対象ID}`

### Architecture: Fully Static Site

**Decision:** HTML + pre-built GeoJSON, hosted on any static file host.

**Rationale:**
- Zero running cost, no server required
- Compatible with any static file host (GitHub Pages, Cloudflare Pages, Netlify, etc.)
- Update flow: re-download `download.csv` → run `build.py` → commit `data/features.geojson` → deploy
- Data changes infrequently (government designations are slow to change)
- 28K features compress to ~1–2 MB over the wire (static hosts typically serve gzip automatically)

### Map Library: Leaflet + MarkerCluster

**Decision:** Leaflet v1.9 with Leaflet.markercluster, replacing the originally planned MapLibre GL JS.

**Why MapLibre was dropped:** MapLibre requires an async vector tile style to load before the
`map.on('load')` event fires. With a ~9 MB GeoJSON, the tile style consistently loaded first,
causing `map.on('load')` to fire before the listener was registered — resulting in layers never
being added (only 3 OSM POI points were visible). Leaflet has no such async style-load step;
layers are added synchronously after `fetch()` resolves.

**Rationale for Leaflet:**
- No async timing issues between data load and map ready state
- `L.markerClusterGroup` with `addLayers()` / `removeLayers()` handles category filtering cleanly
- `disableClusteringAtZoom: 16` ensures individual overlapping markers are always reachable
- Simpler stack, no WebGL dependency

### Category Filtering Strategy

Each category's markers are stored in `markersByCategory[name]`. Toggling a category calls
`clusterGroup.addLayers()` or `removeLayers()` for that category's marker array, then
`applyFilters()` reconciles with any active search conditions.

### Tile Provider Switcher

7 tile providers are offered via a sidebar dropdown (no API key required for any):
CartoDB Voyager, CartoDB Light, GSI 淡色地図, GSI 標準地図, GSI 航空写真, Esri World Topo,
Esri Satellite. Switching updates both the map layer and the sidebar attribution text.

### Category Display

All 19 categories are listed in the sidebar filter. Categories with 0 mappable records are shown
greyed out and disabled. Counts show the number of features present in the GeoJSON (i.e. records
with valid coordinates within Japan bounds).

### GeoJSON Field Selection

`address`（所在地）was removed from the exported GeoJSON to reduce file size (~10.3 MB →
~8.9 MB uncompressed). The detail URL links to the source database page where the full address
is available. Retained fields: `ledger_id`, `item_id`, `name`, `building`, `category`,
`type1`, `type2`, `era`, `prefecture`.

### Multi-Condition Search

Users can add multiple field+keyword condition rows; results must match all conditions (AND
logic). Searchable fields: `name`, `building`, `type1`, `era`, `prefecture`. Filter is applied
via `applyFilters()` which reconciles active categories and search conditions together, using
`clusterGroup.clearLayers()` + `addLayers()` to update the map.

### Data Scope

All records with valid coordinates within Japan bounds are included. No further filtering by
category importance or designation level.

### Show Labels

**Decision:** Permanent Leaflet tooltips (`.name-label`) bound to each named marker, hidden by
default via CSS (`display: none !important`). A "Show labels" checkbox toggles the `show-labels`
class on the map container; labels are only rendered at zoom ≥ 12 to avoid clutter.

Hovering a marker calls `bringToFront()` (SVG re-append) and also re-appends the tooltip DOM
element to the end of the tooltip pane, making both the dot and label float above overlapping
neighbours. CSS z-index and `tooltipopen`-based approaches were attempted but unreliable —
covered labels can't be hovered directly, so the action must be triggered from the marker dot.

### Mobile Support

**Decision:** Overlay drawer pattern — map fills full screen on mobile; a floating ≡ button
(top-left) opens the sidebar as a fixed left-side overlay with a dismissible backdrop.

**Breakpoint:** `max-width: 768px`

**Details:**
- `#sidebar-backdrop` hidden by default (`display: none`); becomes a flex child otherwise and
  breaks the desktop layout — fixed by scoping the hide rule outside the media query
- Zoom control moved to `topright` to avoid overlap with the ≡ button
- Larger tap targets for category items and buttons on mobile
- `env(safe-area-inset-bottom)` padding on footer for iPhone home indicator
- Popup `maxWidth` capped to `Math.min(280, window.innerWidth - 32)` to avoid overflow on
  narrow screens
- Result list click closes the sidebar on mobile so the map is visible

### Legal / Attribution

- Data source: 文化庁 国指定文化財等データベース (Agency for Cultural Affairs, Japan)
- Usage consistent with 政府標準利用規約 (Government Standard Terms of Use, v2.0),
  which permits redistribution with attribution
- **Action required before public release:** Confirm current terms at
  `https://kunishitei.bunka.go.jp/bsys/about`
