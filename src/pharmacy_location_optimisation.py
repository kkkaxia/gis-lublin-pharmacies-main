from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

from grid_utils import generate_points_in_polygon

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MAPS_DIR = PROJECT_ROOT / "maps"
TABLES_DIR = PROJECT_ROOT / "tables"


def main():

    print("Starting smart pharmacy location optimisation...")

    uncovered = gpd.read_file(
        PROCESSED_DIR /
        "pharmacy_uncovered_area_500m_2180.geojson"
    )

    pharmacies = gpd.read_file(
        PROCESSED_DIR /
        "pharmacies_lublin_points_2180.geojson"
    )

    pni = gpd.read_file(
        PROCESSED_DIR /
        "pharmacy_need_index_2180.geojson"
    )

    boundary = gpd.read_file(
        PROCESSED_DIR /
        "lublin_boundary_2180.geojson"
    )

    print("Generating candidate points...")

    candidate_points = []

    for geom in uncovered.geometry:

        if geom.geom_type == "MultiPolygon":

            for poly in geom.geoms:

                candidate_points.extend(
                    generate_points_in_polygon(
                        poly,
                        spacing=500
                    )
                )

        else:

            candidate_points.extend(
                generate_points_in_polygon(
                    geom,
                    spacing=500
                )
            )

    candidates = gpd.GeoDataFrame(
        geometry=candidate_points,
        crs=uncovered.crs
    )

    print(
        f"Generated candidates: "
        f"{len(candidates)}"
    )

    print("Calculating distance score...")

    nearest_distances = []

    for point in candidates.geometry:

        distances = pharmacies.distance(point)

        nearest_distances.append(
            distances.min()
        )

    candidates["nearest_pharmacy_m"] = (
        nearest_distances
    )

    print("Assigning PNI...")

    candidates = gpd.sjoin(
        candidates,
        pni[
            [
                "district_name",
                "PNI",
                "geometry"
            ]
        ],
        predicate="within"
    )

    max_distance = (
        candidates[
            "nearest_pharmacy_m"
        ].max()
    )

    candidates["distance_score"] = (
        candidates["nearest_pharmacy_m"]
        / max_distance
    )

    max_pni = candidates["PNI"].max()

    candidates["pni_score"] = (
        candidates["PNI"]
        / max_pni
    )

    candidates["score"] = (
        0.7 * candidates["distance_score"]
        +
        0.3 * candidates["pni_score"]
    )

    print("Selecting spatially distributed TOP 5...")

    MIN_DISTANCE = 1500

    candidates = candidates.sort_values(
        "score",
        ascending=False
    )

    selected_rows = []

    for _, candidate in candidates.iterrows():

        keep = True

        for selected in selected_rows:

            if (
                    candidate.geometry.distance(
                        selected.geometry
                    )
                    < MIN_DISTANCE
            ):
                keep = False
                break

        if keep:
            selected_rows.append(candidate)

        if len(selected_rows) == 5:
            break

    top5 = gpd.GeoDataFrame(
        selected_rows,
        crs=candidates.crs
    )

    top5["rank"] = range(
        1,
        len(top5) + 1
    )

    save_outputs(
        top5,
        boundary,
        pharmacies
    )

    print("\nTOP 5 LOCATIONS\n")

    print(
        top5[
            [
                "rank",
                "district_name",
                "nearest_pharmacy_m",
                "PNI",
                "score"
            ]
        ]
        .to_string(index=False)
    )

    print("\nDone.")


def save_outputs(
        top5,
        boundary,
        pharmacies
):

    csv_path = (
        TABLES_DIR /
        "recommended_pharmacy_locations.csv"
    )

    pd.DataFrame(
        top5.drop(
            columns="geometry"
        )
    ).to_csv(
        csv_path,
        index=False
    )

    print(f"Saved: {csv_path}")

    geojson_path = (
        PROCESSED_DIR /
        "recommended_pharmacy_locations.geojson"
    )

    top5.to_file(
        geojson_path,
        driver="GeoJSON"
    )

    print(f"Saved: {geojson_path}")

    create_map(
        boundary,
        pharmacies,
        top5
    )


def create_map(
        boundary,
        pharmacies,
        top5
):

    print("Creating optimisation map...")

    fig, ax = plt.subplots(
        figsize=(12, 10)
    )

    boundary.plot(
        ax=ax,
        facecolor="white",
        edgecolor="black"
    )

    pharmacies.plot(
        ax=ax,
        markersize=10
    )

    top5.plot(
        ax=ax,
        markersize=120,
        marker="*"
    )

    for _, row in top5.iterrows():

        ax.annotate(
            str(row["rank"]),
            (
                row.geometry.x,
                row.geometry.y
            )
        )

    ax.set_title(
        "TOP 5 recommended pharmacy locations"
    )

    ax.axis("off")

    plt.tight_layout()

    output = (
        MAPS_DIR /
        "top5_recommended_pharmacies.png"
    )

    plt.savefig(
        output,
        dpi=300
    )

    plt.close()

    print(f"Saved: {output}")


if __name__ == "__main__":
    main()