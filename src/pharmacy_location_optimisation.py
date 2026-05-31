from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MAPS_DIR = PROJECT_ROOT / "maps"


def main():

    print("Starting pharmacy location optimization...")

    uncovered = gpd.read_file(
        PROCESSED_DIR /
        "pharmacy_uncovered_area_500m_2180.geojson"
    )

    pharmacies = gpd.read_file(
        PROCESSED_DIR /
        "pharmacies_lublin_points_2180.geojson"
    )

    boundary = gpd.read_file(
        PROCESSED_DIR /
        "lublin_boundary_2180.geojson"
    )

    print(f"Uncovered polygons: {len(uncovered)}")
    print(f"Pharmacies: {len(pharmacies)}")

    candidates = []

    for geom in uncovered.geometry:

        if geom.is_empty:
            continue

        if geom.geom_type == "Polygon":

            point = geom.representative_point()

            candidates.append(point)

        elif geom.geom_type == "MultiPolygon":

            for poly in geom.geoms:

                point = poly.representative_point()

                candidates.append(point)

    candidate_gdf = gpd.GeoDataFrame(
        geometry=candidates,
        crs=uncovered.crs
    )

    print(
        f"Candidate locations found: "
        f"{len(candidate_gdf)}"
    )

    output_geojson = (
        PROCESSED_DIR /
        "recommended_pharmacy_locations.geojson"
    )

    candidate_gdf.to_file(
        output_geojson,
        driver="GeoJSON"
    )

    print(f"Saved: {output_geojson}")

    create_map(
        boundary,
        pharmacies,
        uncovered,
        candidate_gdf
    )

    print("Optimization completed.")


def create_map(
        boundary,
        pharmacies,
        uncovered,
        candidates
):

    print("Creating optimization map...")

    fig, ax = plt.subplots(
        figsize=(12, 10)
    )

    boundary.plot(
        ax=ax,
        facecolor="white",
        edgecolor="black"
    )

    uncovered.plot(
        ax=ax,
        alpha=0.5
    )

    pharmacies.plot(
        ax=ax,
        markersize=10
    )

    candidates.plot(
        ax=ax,
        markersize=80,
        marker="*"
    )

    ax.set_title(
        "Recommended locations for new pharmacies"
    )

    ax.axis("off")

    plt.tight_layout()

    output = (
        MAPS_DIR /
        "recommended_pharmacy_locations.png"
    )

    plt.savefig(
        output,
        dpi=300
    )

    plt.close()

    print(f"Saved: {output}")


if __name__ == "__main__":
    main()