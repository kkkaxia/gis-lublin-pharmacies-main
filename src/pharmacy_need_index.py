from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLES_DIR = PROJECT_ROOT / "tables"
MAPS_DIR = PROJECT_ROOT / "maps"


def main():

    print("Starting Pharmacy Need Index analysis...")

    coverage = gpd.read_file(
        PROCESSED_DIR /
        "district_buffer_coverage_stats_2180.geojson"
    )

    pharmacies = gpd.read_file(
        PROCESSED_DIR /
        "district_pharmacy_stats_2180.geojson"
    )

    print(f"Coverage rows: {len(coverage)}")
    print(f"Pharmacy rows: {len(pharmacies)}")

    print("\nCOVERAGE COLUMNS:")
    print(coverage.columns.tolist())

    print("\nPHARMACY COLUMNS:")
    print(pharmacies.columns.tolist())

    districts = coverage.merge(
        pharmacies[
            [
                "district_name",
                "pharmacies_count"
            ]
        ],
        on="district_name",
        how="left"
    )

    districts["pharmacies_count"] = (
        districts["pharmacies_count"]
        .fillna(0)
    )

    districts["pharmacy_count_safe"] = (
        districts["pharmacies_count"]
        .replace(0, 0.5)
    )

    districts["PNI"] = (
        districts["uncovered_500m_percent"]
        / districts["pharmacy_count_safe"]
    )

    districts["PNI_rank"] = (
        districts["PNI"]
        .rank(
            ascending=False,
            method="dense"
        )
        .astype(int)
    )

    districts = districts.sort_values(
        "PNI",
        ascending=False
    )

    save_outputs(districts)

    print("\nTOP 10 DISTRICTS BY PNI\n")

    print(
        districts[
            [
                "district_name",
                "pharmacies_count",
                "uncovered_500m_percent",
                "PNI"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nAnalysis completed.")


def save_outputs(gdf):

    csv_path = (
        TABLES_DIR /
        "pharmacy_need_index.csv"
    )

    gdf.drop(
        columns="geometry"
    ).to_csv(
        csv_path,
        index=False
    )

    print(f"Saved: {csv_path}")

    geojson_path = (
        PROCESSED_DIR /
        "pharmacy_need_index_2180.geojson"
    )

    gdf.to_file(
        geojson_path,
        driver="GeoJSON"
    )

    print(f"Saved: {geojson_path}")

    create_map(gdf)

    create_chart(gdf)


def create_map(gdf):

    print("Creating PNI map...")

    fig, ax = plt.subplots(
        figsize=(12, 10)
    )

    gdf.plot(
        column="PNI",
        legend=True,
        ax=ax
    )

    ax.set_title(
        "Pharmacy Need Index by district"
    )

    ax.axis("off")

    plt.tight_layout()

    output = (
        MAPS_DIR /
        "pharmacy_need_index_map.png"
    )

    plt.savefig(
        output,
        dpi=300
    )

    plt.close()

    print(f"Saved: {output}")


def create_chart(gdf):

    print("Creating ranking chart...")

    top = gdf.sort_values(
        "PNI",
        ascending=False
    )

    fig, ax = plt.subplots(
        figsize=(12, 8)
    )

    ax.barh(
        top["district_name"],
        top["PNI"]
    )

    ax.set_title(
        "Pharmacy Need Index ranking"
    )

    ax.invert_yaxis()

    plt.tight_layout()

    output = (
        MAPS_DIR /
        "pharmacy_need_index_ranking.png"
    )

    plt.savefig(
        output,
        dpi=300
    )

    plt.close()

    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
