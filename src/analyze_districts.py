from pathlib import Path

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
MAPS_DIR = BASE_DIR / "maps"
TABLES_DIR = BASE_DIR / "tables"

MAPS_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Input files
# ---------------------------------------------------------

INPUT_DISTRICTS = PROCESSED_DATA_DIR / "lublin_districts_2180.geojson"
INPUT_PHARMACIES = PROCESSED_DATA_DIR / "pharmacies_lublin_points_2180.geojson"


# ---------------------------------------------------------
# Output files
# ---------------------------------------------------------

OUTPUT_STATS_CSV = TABLES_DIR / "district_pharmacy_stats.csv"
OUTPUT_STATS_GEOJSON = PROCESSED_DATA_DIR / "district_pharmacy_stats_2180.geojson"
OUTPUT_PHARMACIES_WITH_DISTRICTS = PROCESSED_DATA_DIR / "pharmacies_with_districts_2180.geojson"
OUTPUT_PHARMACIES_WITH_DISTRICTS_CSV = TABLES_DIR / "pharmacies_with_districts.csv"

OUTPUT_COUNT_MAP = MAPS_DIR / "pharmacies_count_by_district.png"
OUTPUT_DENSITY_MAP = MAPS_DIR / "pharmacies_density_by_district.png"
OUTPUT_RANKING_CHART = MAPS_DIR / "pharmacy_ranking_by_district.png"
OUTPUT_DENSITY_CHART = MAPS_DIR / "pharmacy_density_ranking.png"
OUTPUT_POINTS_MAP = MAPS_DIR / "pharmacies_and_districts.png"


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

TARGET_CRS = "EPSG:2180"


# ---------------------------------------------------------
# Loading data
# ---------------------------------------------------------

def load_data() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Loads processed district and pharmacy datasets.
    """
    print("Loading processed data...")

    if not INPUT_DISTRICTS.exists():
        raise FileNotFoundError(f"Missing file: {INPUT_DISTRICTS}")

    if not INPUT_PHARMACIES.exists():
        raise FileNotFoundError(f"Missing file: {INPUT_PHARMACIES}")

    districts = gpd.read_file(INPUT_DISTRICTS)
    pharmacies = gpd.read_file(INPUT_PHARMACIES)

    print(f"Districts rows: {len(districts)}")
    print(f"Pharmacies rows: {len(pharmacies)}")
    print(f"Districts CRS: {districts.crs}")
    print(f"Pharmacies CRS: {pharmacies.crs}")

    return districts, pharmacies


def prepare_layers(
    districts: gpd.GeoDataFrame,
    pharmacies: gpd.GeoDataFrame
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Checks CRS, removes empty geometries and prepares layers for spatial analysis.
    """
    print("Preparing layers...")

    if districts.crs is None:
        districts = districts.set_crs(TARGET_CRS)

    if pharmacies.crs is None:
        pharmacies = pharmacies.set_crs(TARGET_CRS)

    districts = districts.to_crs(TARGET_CRS)
    pharmacies = pharmacies.to_crs(TARGET_CRS)

    districts = districts[districts.geometry.notnull()]
    districts = districts[~districts.geometry.is_empty]

    pharmacies = pharmacies[pharmacies.geometry.notnull()]
    pharmacies = pharmacies[~pharmacies.geometry.is_empty]

    districts["geometry"] = districts.geometry.make_valid()
    pharmacies["geometry"] = pharmacies.geometry.make_valid()

    if "district_id" not in districts.columns:
        districts = districts.reset_index(drop=True)
        districts["district_id"] = range(1, len(districts) + 1)

    if "district_name" not in districts.columns:
        raise ValueError("District layer must contain 'district_name' column.")

    if "pharmacy_id" not in pharmacies.columns:
        pharmacies = pharmacies.reset_index(drop=True)
        pharmacies["pharmacy_id"] = range(1, len(pharmacies) + 1)

    return districts, pharmacies


# ---------------------------------------------------------
# Spatial analysis
# ---------------------------------------------------------

def assign_pharmacies_to_districts(
    districts: gpd.GeoDataFrame,
    pharmacies: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Assigns each pharmacy to a district using spatial join.
    """
    print("Assigning pharmacies to districts...")

    district_columns = ["district_id", "district_name", "geometry"]

    pharmacies_with_districts = gpd.sjoin(
        pharmacies,
        districts[district_columns],
        how="left",
        predicate="within"
    )

    pharmacies_with_districts = pharmacies_with_districts.drop(columns=["index_right"], errors="ignore")

    unassigned_count = pharmacies_with_districts["district_name"].isna().sum()

    print(f"Assigned pharmacies: {len(pharmacies_with_districts) - unassigned_count}")
    print(f"Unassigned pharmacies: {unassigned_count}")

    # If a pharmacy is exactly on a boundary, 'within' may not assign it.
    # In that case, we assign it to the nearest district.
    if unassigned_count > 0:
        print("Some pharmacies were not assigned. Using nearest district for them...")

        assigned = pharmacies_with_districts[pharmacies_with_districts["district_name"].notna()].copy()
        unassigned = pharmacies_with_districts[pharmacies_with_districts["district_name"].isna()].copy()

        unassigned = unassigned.drop(columns=["district_id", "district_name"], errors="ignore")

        nearest = gpd.sjoin_nearest(
            unassigned,
            districts[district_columns],
            how="left",
            distance_col="distance_to_district_m"
        )

        nearest = nearest.drop(columns=["index_right"], errors="ignore")

        pharmacies_with_districts = pd.concat([assigned, nearest], ignore_index=True)
        pharmacies_with_districts = gpd.GeoDataFrame(
            pharmacies_with_districts,
            geometry="geometry",
            crs=TARGET_CRS
        )

        still_unassigned = pharmacies_with_districts["district_name"].isna().sum()
        print(f"Still unassigned after nearest join: {still_unassigned}")

    return pharmacies_with_districts


def calculate_district_statistics(
    districts: gpd.GeoDataFrame,
    pharmacies_with_districts: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Calculates number of pharmacies and pharmacy density for each district.
    """
    print("Calculating district statistics...")

    districts_stats = districts.copy()

    districts_stats["area_km2"] = districts_stats.geometry.area / 1_000_000

    pharmacy_counts = (
        pharmacies_with_districts
        .dropna(subset=["district_id"])
        .groupby(["district_id", "district_name"])
        .size()
        .reset_index(name="pharmacies_count")
    )

    districts_stats = districts_stats.merge(
        pharmacy_counts[["district_id", "pharmacies_count"]],
        on="district_id",
        how="left"
    )

    districts_stats["pharmacies_count"] = districts_stats["pharmacies_count"].fillna(0).astype(int)

    districts_stats["pharmacies_per_km2"] = (
        districts_stats["pharmacies_count"] / districts_stats["area_km2"]
    )

    districts_stats["pharmacies_per_km2"] = districts_stats["pharmacies_per_km2"].round(2)
    districts_stats["area_km2"] = districts_stats["area_km2"].round(2)

    districts_stats = districts_stats.sort_values(
        by="pharmacies_count",
        ascending=False
    ).reset_index(drop=True)

    districts_stats["rank_by_count"] = range(1, len(districts_stats) + 1)

    districts_stats = districts_stats.sort_values(
        by="pharmacies_per_km2",
        ascending=False
    ).reset_index(drop=True)

    districts_stats["rank_by_density"] = range(1, len(districts_stats) + 1)

    districts_stats = districts_stats.sort_values("district_name").reset_index(drop=True)

    return districts_stats


# ---------------------------------------------------------
# Saving results
# ---------------------------------------------------------

def save_results(
    districts_stats: gpd.GeoDataFrame,
    pharmacies_with_districts: gpd.GeoDataFrame
) -> None:
    """
    Saves analysis results to CSV and GeoJSON.
    """
    print("Saving analysis results...")

    districts_stats.to_file(OUTPUT_STATS_GEOJSON, driver="GeoJSON", encoding="utf-8")

    stats_table = districts_stats.drop(columns="geometry")
    stats_table.to_csv(OUTPUT_STATS_CSV, index=False, encoding="utf-8")

    pharmacies_with_districts.to_file(
        OUTPUT_PHARMACIES_WITH_DISTRICTS,
        driver="GeoJSON",
        encoding="utf-8"
    )

    pharmacies_table = pharmacies_with_districts.drop(columns="geometry")
    pharmacies_table.to_csv(
        OUTPUT_PHARMACIES_WITH_DISTRICTS_CSV,
        index=False,
        encoding="utf-8"
    )

    print(f"Saved: {OUTPUT_STATS_CSV}")
    print(f"Saved: {OUTPUT_STATS_GEOJSON}")
    print(f"Saved: {OUTPUT_PHARMACIES_WITH_DISTRICTS}")
    print(f"Saved: {OUTPUT_PHARMACIES_WITH_DISTRICTS_CSV}")


# ---------------------------------------------------------
# Visualization
# ---------------------------------------------------------

def create_count_map(districts_stats: gpd.GeoDataFrame) -> None:
    """
    Creates choropleth map showing number of pharmacies by district.
    """
    print("Creating pharmacy count map...")

    fig, ax = plt.subplots(figsize=(10, 10))

    districts_stats.plot(
        column="pharmacies_count",
        ax=ax,
        legend=True,
        edgecolor="black",
        linewidth=0.5,
        cmap="Blues"
    )

    districts_stats.boundary.plot(ax=ax, linewidth=0.5, color="black")

    ax.set_title("Number of pharmacies by district in Lublin")
    ax.set_axis_off()

    plt.tight_layout()
    plt.savefig(OUTPUT_COUNT_MAP, dpi=300)
    plt.close()

    print(f"Saved: {OUTPUT_COUNT_MAP}")


def create_density_map(districts_stats: gpd.GeoDataFrame) -> None:
    """
    Creates choropleth map showing pharmacy density by district.
    """
    print("Creating pharmacy density map...")

    fig, ax = plt.subplots(figsize=(10, 10))

    districts_stats.plot(
        column="pharmacies_per_km2",
        ax=ax,
        legend=True,
        edgecolor="black",
        linewidth=0.5,
        cmap="Oranges"
    )

    districts_stats.boundary.plot(ax=ax, linewidth=0.5, color="black")

    ax.set_title("Pharmacy density by district in Lublin pharmacies/km²")
    ax.set_axis_off()

    plt.tight_layout()
    plt.savefig(OUTPUT_DENSITY_MAP, dpi=300)
    plt.close()

    print(f"Saved: {OUTPUT_DENSITY_MAP}")


def create_points_map(
    districts_stats: gpd.GeoDataFrame,
    pharmacies_with_districts: gpd.GeoDataFrame
) -> None:
    """
    Creates map with district boundaries and pharmacy points.
    """
    print("Creating pharmacy points and districts map...")

    fig, ax = plt.subplots(figsize=(10, 10))

    districts_stats.boundary.plot(ax=ax, linewidth=0.7, color="black")
    pharmacies_with_districts.plot(ax=ax, markersize=8, color="red", alpha=0.8)

    ax.set_title("Pharmacies and district boundaries in Lublin")
    ax.set_axis_off()

    plt.tight_layout()
    plt.savefig(OUTPUT_POINTS_MAP, dpi=300)
    plt.close()

    print(f"Saved: {OUTPUT_POINTS_MAP}")


def create_ranking_chart(districts_stats: gpd.GeoDataFrame) -> None:
    """
    Creates horizontal bar chart with number of pharmacies by district.
    """
    print("Creating pharmacy count ranking chart...")

    stats = districts_stats.sort_values("pharmacies_count", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 9))

    ax.barh(stats["district_name"], stats["pharmacies_count"])

    ax.set_title("Number of pharmacies by district in Lublin")
    ax.set_xlabel("Number of pharmacies")
    ax.set_ylabel("District")

    for index, value in enumerate(stats["pharmacies_count"]):
        ax.text(value + 0.1, index, str(value), va="center", fontsize=8)

    plt.tight_layout()
    plt.savefig(OUTPUT_RANKING_CHART, dpi=300)
    plt.close()

    print(f"Saved: {OUTPUT_RANKING_CHART}")


def create_density_chart(districts_stats: gpd.GeoDataFrame) -> None:
    """
    Creates horizontal bar chart with pharmacy density by district.
    """
    print("Creating pharmacy density ranking chart...")

    stats = districts_stats.sort_values("pharmacies_per_km2", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 9))

    ax.barh(stats["district_name"], stats["pharmacies_per_km2"])

    ax.set_title("Pharmacy density by district in Lublin")
    ax.set_xlabel("Pharmacies per km²")
    ax.set_ylabel("District")

    for index, value in enumerate(stats["pharmacies_per_km2"]):
        ax.text(value + 0.02, index, str(value), va="center", fontsize=8)

    plt.tight_layout()
    plt.savefig(OUTPUT_DENSITY_CHART, dpi=300)
    plt.close()

    print(f"Saved: {OUTPUT_DENSITY_CHART}")


def create_visualizations(
    districts_stats: gpd.GeoDataFrame,
    pharmacies_with_districts: gpd.GeoDataFrame
) -> None:
    """
    Creates all maps and charts.
    """
    create_count_map(districts_stats)
    create_density_map(districts_stats)
    create_points_map(districts_stats, pharmacies_with_districts)
    create_ranking_chart(districts_stats)
    create_density_chart(districts_stats)


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

def print_summary(
    districts_stats: gpd.GeoDataFrame,
    pharmacies_with_districts: gpd.GeoDataFrame
) -> None:
    """
    Prints summary of the analysis.
    """
    total_pharmacies = len(pharmacies_with_districts)
    total_districts = len(districts_stats)

    top_by_count = districts_stats.sort_values("pharmacies_count", ascending=False).head(5)
    bottom_by_count = districts_stats.sort_values("pharmacies_count", ascending=True).head(5)

    top_by_density = districts_stats.sort_values("pharmacies_per_km2", ascending=False).head(5)
    bottom_by_density = districts_stats.sort_values("pharmacies_per_km2", ascending=True).head(5)

    print("\n--- ANALYSIS SUMMARY ---")
    print(f"Total pharmacies: {total_pharmacies}")
    print(f"Total districts: {total_districts}")

    print("\nTop 5 districts by number of pharmacies:")
    for _, row in top_by_count.iterrows():
        print(f"- {row['district_name']}: {row['pharmacies_count']} pharmacies")

    print("\nBottom 5 districts by number of pharmacies:")
    for _, row in bottom_by_count.iterrows():
        print(f"- {row['district_name']}: {row['pharmacies_count']} pharmacies")

    print("\nTop 5 districts by pharmacy density:")
    for _, row in top_by_density.iterrows():
        print(f"- {row['district_name']}: {row['pharmacies_per_km2']} pharmacies/km²")

    print("\nBottom 5 districts by pharmacy density:")
    for _, row in bottom_by_density.iterrows():
        print(f"- {row['district_name']}: {row['pharmacies_per_km2']} pharmacies/km²")

    print("------------------------\n")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main() -> None:
    print("Starting district-level pharmacy analysis...")

    districts, pharmacies = load_data()

    districts, pharmacies = prepare_layers(districts, pharmacies)

    pharmacies_with_districts = assign_pharmacies_to_districts(
        districts=districts,
        pharmacies=pharmacies
    )

    districts_stats = calculate_district_statistics(
        districts=districts,
        pharmacies_with_districts=pharmacies_with_districts
    )

    save_results(
        districts_stats=districts_stats,
        pharmacies_with_districts=pharmacies_with_districts
    )

    create_visualizations(
        districts_stats=districts_stats,
        pharmacies_with_districts=pharmacies_with_districts
    )

    print_summary(
        districts_stats=districts_stats,
        pharmacies_with_districts=pharmacies_with_districts
    )

    print("District-level pharmacy analysis completed successfully.")


if __name__ == "__main__":
    main()