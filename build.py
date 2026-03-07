#!/usr/bin/env python3
"""Build script: converts target/download.csv to data/features.geojson for the map.

Run after downloading a fresh copy of target/download.csv:
    python3 build.py
"""

import csv
import json
from pathlib import Path

# Bounds covering all Japanese territory.
# Records outside these bounds are treated as data-entry errors and excluded.
LAT_BOUNDS = (20.0, 47.0)
LON_BOUNDS = (120.0, 155.0)


def main() -> None:
    src = Path("target/download.csv")
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "features.geojson"

    features: list[dict] = []
    n_no_coord = 0
    n_oob = 0

    with open(src, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        # The prefecture column has a long name with an inline note; match by prefix.
        pref_col = next((h for h in headers if h.startswith("都道府県")), "")

        for row in reader:
            # Skip rows without valid numeric coordinates.
            try:
                lat = float(row["緯度"])
                lon = float(row["経度"])
            except (ValueError, TypeError, KeyError):
                n_no_coord += 1
                continue

            # Filter out-of-bounds coordinates (likely data-entry errors).
            if not (LAT_BOUNDS[0] <= lat <= LAT_BOUNDS[1] and LON_BOUNDS[0] <= lon <= LON_BOUNDS[1]):
                n_oob += 1
                continue

            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    # 台帳ID is the category code (e.g. "102"); first segment of detail URL.
                    "ledger_id": row.get("台帳ID", "").strip(),
                    # 管理対象ID is the per-item ID; kept as string to preserve leading zeros.
                    "item_id": row.get("管理対象ID", "").strip(),
                    "name": row.get("名称", "").strip(),
                    "building": row.get("棟名", "").strip(),
                    "category": row.get("文化財種類", "").strip(),
                    "type1": row.get("種別1", "").strip(),
                    "type2": row.get("種別2", "").strip(),
                    "era": row.get("時代", "").strip(),
                    "prefecture": row.get(pref_col, "").strip() if pref_col else "",
                },
            })

    geojson = {"type": "FeatureCollection", "features": features}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Wrote {len(features):,} features to {out}")
    print(f"  Skipped - no/invalid coords : {n_no_coord:,}")
    print(f"  Skipped - out of bounds     : {n_oob:,}")


if __name__ == "__main__":
    main()
