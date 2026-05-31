from pathlib import Path

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MAPS_DIR = PROJECT_ROOT / "maps"
TABLES_DIR = PROJECT_ROOT / "tables"


def main():
    print("Starting pharmacy location optimization...")

    uncovered = gpd.read_file(
        PROCESSED_DIR / "pharmacy_uncovered_area_500m_2180.geojson"
    )

    pharmacies = gpd.read_file(
        PROCESSED_DIR / "pharmacies_lublin_points_2180.geojson"
    )

    boundary = gpd.read_file(
        PROCESSED_DIR / "lublin_boundary_2180.geojson"
    )

    print(f"Uncovered polygons: {len(uncovered)}")
    print(f"Pharmacies: {len(pharmacies)}")
    print(f"Boundary rows: {len(boundary)}")


if __name__ == "__main__":
    main()