from pathlib import Path

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MAPS_DIR = PROJECT_ROOT / "maps"
TABLES_DIR = PROJECT_ROOT / "tables"


MIN_DISTANCE_TO_EXISTING = 500  # meters
TOP_LOCATIONS = 10


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

    print("Exploding uncovered polygons...")

    uncovered = uncovered.explode(index_parts=False)

    uncovered["area_m2"] = uncovered.area
    uncovered["area_km2"] = uncovered["area_m2"] / 1_000_000

    uncovered = uncovered.sort_values(
        by="area_m2",
        ascending=False
    ).reset_index(drop=True)

    print(f"Number of individual uncovered polygons: {len(uncovered)}")

    candidates = []

    print("Generating candidate locations...")

    for idx, row in uncovered.iterrows():

        centroid = row.geometry.centroid

        distances = pharmacies.distance(centroid)

        nearest_distance = distances.min()

        if nearest_distance >= MIN_DISTANCE_TO_EXISTING:

            candidates.append(
                {
                    "candidate_id": len(candidates) + 1,
                    "area_km2": round(row["area_km2"], 3),
                    "nearest_pharmacy_m": round(nearest_distance, 1),
                    "geometry": centroid
                }
            )

        if len(candidates) >= TOP_LOCATIONS:
            break

    candidates_gdf = gpd.GeoDataFrame(
        candidates,
        geometry="geometry",
        crs=pharmacies.crs
    )

    print(f"Selected candidate locations: {len(candidates_gdf)}")

    print("Saving results...")

    output_geojson = (
        PROCESSED_DIR /
        "optimal_pharmacy_locations_2180.geojson"
    )

    candidates_gdf.to_file(
        output_geojson,
        driver="GeoJSON"
    )

    print(f"Saved: {output_geojson}")

    output_csv = (
        TABLES_DIR /
        "optimal_pharmacy_locations.csv"
    )

    candidates_gdf.drop(
        columns="geometry"
    ).to_csv(
        output_csv,
        index=False
    )

    print(f"Saved: {output_csv}")

    create_map(
        boundary,
        pharmacies,
        candidates_gdf
    )

    print("\n--- OPTIMISATION SUMMARY ---")

    if len(candidates_gdf) > 0:

        for _, row in candidates_gdf.iterrows():

            print(
                f"Location {row['candidate_id']} | "
                f"Area: {row['area_km2']} km² | "
                f"Nearest pharmacy: "
                f"{row['nearest_pharmacy_m']} m"
            )

    print("--------------------------------")
    print("Optimization completed successfully.")


def create_map(
    boundary,
    pharmacies,
    candidates
):
    print("Creating optimisation map...")

    fig, ax = plt.subplots(
        figsize=(12, 12)
    )

    boundary.plot(
        ax=ax,
        facecolor="white",
        edgecolor="black"
    )

    pharmacies.plot(
        ax=ax,
        markersize=12,
        label="Existing pharmacies"
    )

    candidates.plot(
        ax=ax,
        markersize=80,
        marker="*",
        label="Suggested locations"
    )

    for _, row in candidates.iterrows():

        ax.annotate(
            text=str(row["candidate_id"]),
            xy=(row.geometry.x, row.geometry.y),
            fontsize=8
        )

    ax.set_title(
        "Suggested new pharmacy locations"
    )

    ax.legend()

    plt.tight_layout()

    output_png = (
        MAPS_DIR /
        "optimal_pharmacy_locations.png"
    )

    plt.savefig(
        output_png,
        dpi=300
    )

    plt.close()

    print(f"Saved: {output_png}")


if __name__ == "__main__":
    main()