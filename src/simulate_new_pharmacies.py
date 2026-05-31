from pathlib import Path

import geopandas as gpd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def main():

    print("Starting simulation...")

    pharmacies = gpd.read_file(
        PROCESSED_DIR /
        "pharmacies_lublin_points_2180.geojson"
    )

    recommended = gpd.read_file(
        PROCESSED_DIR /
        "recommended_pharmacy_locations.geojson"
    )

    boundary = gpd.read_file(
        PROCESSED_DIR /
        "lublin_boundary_2180.geojson"
    )

    print(f"Current pharmacies: {len(pharmacies)}")
    print(f"Recommended locations: {len(recommended)}")

    top5 = recommended.head(5).copy()

    current_buffer = pharmacies.buffer(500)

    current_area = (
        current_buffer.union_all().area
        / 1_000_000
    )

    simulated = gpd.GeoDataFrame(
        geometry=list(pharmacies.geometry)
        + list(top5.geometry),
        crs=pharmacies.crs
    )

    simulated_buffer = simulated.buffer(500)

    simulated_area = (
        simulated_buffer.union_all().area
        / 1_000_000
    )

    city_area = (
        boundary.geometry.union_all().area
        / 1_000_000
    )

    current_percent = (
        current_area /
        city_area * 100
    )

    simulated_percent = (
        simulated_area /
        city_area * 100
    )

    improvement = (
        simulated_percent
        - current_percent
    )

    print("\nRESULTS\n")

    print(
        f"Current coverage: "
        f"{current_percent:.2f}%"
    )

    print(
        f"Coverage after simulation: "
        f"{simulated_percent:.2f}%"
    )

    print(
        f"Improvement: "
        f"{improvement:.2f} percentage points"
    )


if __name__ == "__main__":
    main()