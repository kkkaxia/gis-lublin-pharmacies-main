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

INPUT_CITY_BOUNDARY = PROCESSED_DATA_DIR / "lublin_boundary_2180.geojson"
INPUT_DISTRICTS = PROCESSED_DATA_DIR / "lublin_districts_2180.geojson"
INPUT_PHARMACIES = PROCESSED_DATA_DIR / "pharmacies_with_districts_2180.geojson"


# ---------------------------------------------------------
# Output files
# ---------------------------------------------------------

OUTPUT_BUFFERS_500 = PROCESSED_DATA_DIR / "pharmacy_buffers_500m_2180.geojson"
OUTPUT_BUFFERS_1000 = PROCESSED_DATA_DIR / "pharmacy_buffers_1000m_2180.geojson"

OUTPUT_SERVICE_AREA_500 = PROCESSED_DATA_DIR / "pharmacy_service_area_500m_2180.geojson"
OUTPUT_SERVICE_AREA_1000 = PROCESSED_DATA_DIR / "pharmacy_service_area_1000m_2180.geojson"

OUTPUT_UNCOVERED_AREA_500 = PROCESSED_DATA_DIR / "pharmacy_uncovered_area_500m_2180.geojson"
OUTPUT_UNCOVERED_AREA_1000 = PROCESSED_DATA_DIR / "pharmacy_uncovered_area_1000m_2180.geojson"

OUTPUT_DISTRICT_BUFFER_STATS = TABLES_DIR / "district_buffer_coverage_stats.csv"
OUTPUT_DISTRICT_BUFFER_STATS_GEOJSON = PROCESSED_DATA_DIR / "district_buffer_coverage_stats_2180.geojson"

OUTPUT_MAP_500 = MAPS_DIR / "pharmacy_buffer_500m_map.png"
OUTPUT_MAP_1000 = MAPS_DIR / "pharmacy_buffer_1000m_map.png"
OUTPUT_MAP_UNCOVERED_500 = MAPS_DIR / "pharmacy_uncovered_500m_map.png"
OUTPUT_MAP_DISTRICT_COVERAGE_500 = MAPS_DIR / "district_coverage_500m_map.png"
OUTPUT_MAP_DISTRICT_COVERAGE_1000 = MAPS_DIR / "district_coverage_1000m_map.png"
OUTPUT_COVERAGE_CHART = MAPS_DIR / "district_buffer_coverage_chart.png"


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

TARGET_CRS = "EPSG:2180"
BUFFER_DISTANCES = [500, 1000]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def union_geometries(gdf: gpd.GeoDataFrame):
    """
    Returns a single geometry created from all geometries in a GeoDataFrame.
    Works with both older and newer GeoPandas/Shapely versions.
    """
    if hasattr(gdf.geometry, "union_all"):
        return gdf.geometry.union_all()

    return gdf.geometry.unary_union


def save_geodataframe(gdf: gpd.GeoDataFrame, output_path: Path) -> None:
    """
    Saves GeoDataFrame to GeoJSON.
    """
    gdf.to_file(output_path, driver="GeoJSON", encoding="utf-8")
    print(f"Saved: {output_path}")


def load_data() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Loads city boundary, district boundaries and pharmacies.
    """
    print("Loading data for buffer analysis...")

    if not INPUT_CITY_BOUNDARY.exists():
        raise FileNotFoundError(f"Missing file: {INPUT_CITY_BOUNDARY}")

    if not INPUT_DISTRICTS.exists():
        raise FileNotFoundError(f"Missing file: {INPUT_DISTRICTS}")

    if not INPUT_PHARMACIES.exists():
        raise FileNotFoundError(f"Missing file: {INPUT_PHARMACIES}")

    city_boundary = gpd.read_file(INPUT_CITY_BOUNDARY)
    districts = gpd.read_file(INPUT_DISTRICTS)
    pharmacies = gpd.read_file(INPUT_PHARMACIES)

    print(f"City boundary rows: {len(city_boundary)}")
    print(f"Districts rows: {len(districts)}")
    print(f"Pharmacies rows: {len(pharmacies)}")

    print(f"City boundary CRS: {city_boundary.crs}")
    print(f"Districts CRS: {districts.crs}")
    print(f"Pharmacies CRS: {pharmacies.crs}")

    return city_boundary, districts, pharmacies


def prepare_layers(
    city_boundary: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    pharmacies: gpd.GeoDataFrame
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Prepares layers for buffer analysis.
    """
    print("Preparing layers...")

    if city_boundary.crs is None:
        city_boundary = city_boundary.set_crs(TARGET_CRS)

    if districts.crs is None:
        districts = districts.set_crs(TARGET_CRS)

    if pharmacies.crs is None:
        pharmacies = pharmacies.set_crs(TARGET_CRS)

    city_boundary = city_boundary.to_crs(TARGET_CRS)
    districts = districts.to_crs(TARGET_CRS)
    pharmacies = pharmacies.to_crs(TARGET_CRS)

    city_boundary = city_boundary[city_boundary.geometry.notnull()]
    city_boundary = city_boundary[~city_boundary.geometry.is_empty]

    districts = districts[districts.geometry.notnull()]
    districts = districts[~districts.geometry.is_empty]

    pharmacies = pharmacies[pharmacies.geometry.notnull()]
    pharmacies = pharmacies[~pharmacies.geometry.is_empty]

    city_boundary["geometry"] = city_boundary.geometry.make_valid()
    districts["geometry"] = districts.geometry.make_valid()
    pharmacies["geometry"] = pharmacies.geometry.make_valid()

    if "pharmacy_id" not in pharmacies.columns:
        pharmacies = pharmacies.reset_index(drop=True)
        pharmacies["pharmacy_id"] = range(1, len(pharmacies) + 1)

    if "district_name" not in districts.columns:
        raise ValueError("Districts file must contain 'district_name' column.")

    return city_boundary, districts, pharmacies


# ---------------------------------------------------------
# Buffer analysis
# ---------------------------------------------------------

def create_individual_buffers(
    pharmacies: gpd.GeoDataFrame,
    distance_m: int
) -> gpd.GeoDataFrame:
    """
    Creates individual buffers around each pharmacy.
    """
    print(f"Creating individual {distance_m} m buffers...")

    buffers = pharmacies.copy()

    buffers["buffer_distance_m"] = distance_m
    buffers["geometry"] = buffers.geometry.buffer(distance_m)

    useful_columns = [
        "pharmacy_id",
        "name",
        "district_name",
        "buffer_distance_m",
        "geometry",
    ]

    existing_columns = [column for column in useful_columns if column in buffers.columns]

    buffers = buffers[existing_columns]

    return buffers


def create_service_area(
    city_boundary: gpd.GeoDataFrame,
    buffers: gpd.GeoDataFrame,
    distance_m: int
) -> gpd.GeoDataFrame:
    """
    Creates dissolved service area from all pharmacy buffers and clips it to city boundary.
    """
    print(f"Creating dissolved service area for {distance_m} m buffers...")

    city_geometry = union_geometries(city_boundary)
    buffer_geometry = union_geometries(buffers)

    service_geometry = buffer_geometry.intersection(city_geometry)

    service_area = gpd.GeoDataFrame(
        {
            "buffer_distance_m": [distance_m],
            "area_km2": [service_geometry.area / 1_000_000],
            "geometry": [service_geometry],
        },
        geometry="geometry",
        crs=TARGET_CRS
    )

    service_area["area_km2"] = service_area["area_km2"].round(2)

    return service_area


def create_uncovered_area(
    city_boundary: gpd.GeoDataFrame,
    service_area: gpd.GeoDataFrame,
    distance_m: int
) -> gpd.GeoDataFrame:
    """
    Creates area outside the pharmacy service area.
    """
    print(f"Creating uncovered area for {distance_m} m buffers...")

    city_geometry = union_geometries(city_boundary)
    service_geometry = union_geometries(service_area)

    uncovered_geometry = city_geometry.difference(service_geometry)

    uncovered_area = gpd.GeoDataFrame(
        {
            "buffer_distance_m": [distance_m],
            "area_km2": [uncovered_geometry.area / 1_000_000],
            "geometry": [uncovered_geometry],
        },
        geometry="geometry",
        crs=TARGET_CRS
    )

    uncovered_area["area_km2"] = uncovered_area["area_km2"].round(2)

    return uncovered_area


def calculate_city_coverage(
    city_boundary: gpd.GeoDataFrame,
    service_area: gpd.GeoDataFrame,
    distance_m: int
) -> dict:
    """
    Calculates city-level coverage statistics.
    """
    city_geometry = union_geometries(city_boundary)
    service_geometry = union_geometries(service_area)

    city_area_km2 = city_geometry.area / 1_000_000
    covered_area_km2 = service_geometry.area / 1_000_000
    uncovered_area_km2 = city_area_km2 - covered_area_km2
    covered_percent = covered_area_km2 / city_area_km2 * 100

    return {
        "buffer_distance_m": distance_m,
        "city_area_km2": round(city_area_km2, 2),
        "covered_area_km2": round(covered_area_km2, 2),
        "uncovered_area_km2": round(uncovered_area_km2, 2),
        "covered_percent": round(covered_percent, 2),
        "uncovered_percent": round(100 - covered_percent, 2),
    }


def calculate_district_coverage(
    districts: gpd.GeoDataFrame,
    service_area_500: gpd.GeoDataFrame,
    service_area_1000: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Calculates how much of each district is covered by 500 m and 1000 m buffers.
    """
    print("Calculating district-level buffer coverage...")

    districts_stats = districts.copy()

    service_500_geometry = union_geometries(service_area_500)
    service_1000_geometry = union_geometries(service_area_1000)

    districts_stats["area_km2"] = districts_stats.geometry.area / 1_000_000

    districts_stats["covered_500m_km2"] = districts_stats.geometry.apply(
        lambda geom: geom.intersection(service_500_geometry).area / 1_000_000
    )

    districts_stats["covered_1000m_km2"] = districts_stats.geometry.apply(
        lambda geom: geom.intersection(service_1000_geometry).area / 1_000_000
    )

    districts_stats["covered_500m_percent"] = (
        districts_stats["covered_500m_km2"] / districts_stats["area_km2"] * 100
    )

    districts_stats["covered_1000m_percent"] = (
        districts_stats["covered_1000m_km2"] / districts_stats["area_km2"] * 100
    )

    districts_stats["uncovered_500m_percent"] = 100 - districts_stats["covered_500m_percent"]
    districts_stats["uncovered_1000m_percent"] = 100 - districts_stats["covered_1000m_percent"]

    numeric_columns = [
        "area_km2",
        "covered_500m_km2",
        "covered_1000m_km2",
        "covered_500m_percent",
        "covered_1000m_percent",
        "uncovered_500m_percent",
        "uncovered_1000m_percent",
    ]

    for column in numeric_columns:
        districts_stats[column] = districts_stats[column].round(2)

    districts_stats = districts_stats.sort_values(
        by="covered_500m_percent",
        ascending=False
    ).reset_index(drop=True)

    districts_stats["rank_coverage_500m"] = range(1, len(districts_stats) + 1)

    districts_stats = districts_stats.sort_values(
        by="covered_1000m_percent",
        ascending=False
    ).reset_index(drop=True)

    districts_stats["rank_coverage_1000m"] = range(1, len(districts_stats) + 1)

    districts_stats = districts_stats.sort_values("district_name").reset_index(drop=True)

    return districts_stats


# ---------------------------------------------------------
# Saving results
# ---------------------------------------------------------

def save_results(
    buffers_500: gpd.GeoDataFrame,
    buffers_1000: gpd.GeoDataFrame,
    service_area_500: gpd.GeoDataFrame,
    service_area_1000: gpd.GeoDataFrame,
    uncovered_area_500: gpd.GeoDataFrame,
    uncovered_area_1000: gpd.GeoDataFrame,
    district_coverage: gpd.GeoDataFrame
) -> None:
    """
    Saves buffer analysis results.
    """
    print("Saving buffer analysis results...")

    save_geodataframe(buffers_500, OUTPUT_BUFFERS_500)
    save_geodataframe(buffers_1000, OUTPUT_BUFFERS_1000)

    save_geodataframe(service_area_500, OUTPUT_SERVICE_AREA_500)
    save_geodataframe(service_area_1000, OUTPUT_SERVICE_AREA_1000)

    save_geodataframe(uncovered_area_500, OUTPUT_UNCOVERED_AREA_500)
    save_geodataframe(uncovered_area_1000, OUTPUT_UNCOVERED_AREA_1000)

    save_geodataframe(district_coverage, OUTPUT_DISTRICT_BUFFER_STATS_GEOJSON)

    district_coverage_table = district_coverage.drop(columns="geometry")
    district_coverage_table.to_csv(
        OUTPUT_DISTRICT_BUFFER_STATS,
        index=False,
        encoding="utf-8"
    )

    print(f"Saved: {OUTPUT_DISTRICT_BUFFER_STATS}")


# ---------------------------------------------------------
# Visualization
# ---------------------------------------------------------

def create_buffer_map(
    city_boundary: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    pharmacies: gpd.GeoDataFrame,
    service_area: gpd.GeoDataFrame,
    uncovered_area: gpd.GeoDataFrame,
    distance_m: int,
    output_path: Path
) -> None:
    """
    Creates map showing pharmacy service area and uncovered area.
    """
    print(f"Creating {distance_m} m buffer map...")

    fig, ax = plt.subplots(figsize=(10, 10))

    uncovered_area.plot(ax=ax, alpha=0.4, edgecolor="none")
    service_area.plot(ax=ax, alpha=0.5, edgecolor="none")

    districts.boundary.plot(ax=ax, linewidth=0.5, color="black")
    city_boundary.boundary.plot(ax=ax, linewidth=1.2, color="black")
    pharmacies.plot(ax=ax, markersize=6, color="red", alpha=0.8)

    ax.set_title(f"Pharmacy service area in Lublin - {distance_m} m buffer")
    ax.set_axis_off()

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

    print(f"Saved: {output_path}")


def create_uncovered_map_500(
    city_boundary: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    pharmacies: gpd.GeoDataFrame,
    uncovered_area_500: gpd.GeoDataFrame
) -> None:
    """
    Creates map focused on areas outside 500 m pharmacy buffer.
    """
    print("Creating uncovered area map for 500 m buffer...")

    fig, ax = plt.subplots(figsize=(10, 10))

    city_boundary.plot(ax=ax, alpha=0.15, edgecolor="black")
    uncovered_area_500.plot(ax=ax, alpha=0.7, edgecolor="black")

    districts.boundary.plot(ax=ax, linewidth=0.5, color="black")
    pharmacies.plot(ax=ax, markersize=6, color="red", alpha=0.8)

    ax.set_title("Areas outside 500 m pharmacy service area in Lublin")
    ax.set_axis_off()

    plt.tight_layout()
    plt.savefig(OUTPUT_MAP_UNCOVERED_500, dpi=300)
    plt.close()

    print(f"Saved: {OUTPUT_MAP_UNCOVERED_500}")


def create_district_coverage_map(
    district_coverage: gpd.GeoDataFrame,
    column: str,
    title: str,
    output_path: Path
) -> None:
    """
    Creates choropleth map for district buffer coverage.
    """
    print(f"Creating district coverage map: {title}")

    fig, ax = plt.subplots(figsize=(10, 10))

    district_coverage.plot(
        column=column,
        ax=ax,
        legend=True,
        edgecolor="black",
        linewidth=0.5,
        cmap="Greens"
    )

    ax.set_title(title)
    ax.set_axis_off()

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

    print(f"Saved: {output_path}")


def create_coverage_chart(district_coverage: gpd.GeoDataFrame) -> None:
    """
    Creates horizontal chart comparing 500 m and 1000 m coverage by district.
    """
    print("Creating district coverage chart...")

    stats = district_coverage.sort_values("covered_500m_percent", ascending=True)

    fig, ax = plt.subplots(figsize=(11, 9))

    y_positions = range(len(stats))
    bar_height = 0.4

    ax.barh(
        [y - bar_height / 2 for y in y_positions],
        stats["covered_500m_percent"],
        height=bar_height,
        label="500 m"
    )

    ax.barh(
        [y + bar_height / 2 for y in y_positions],
        stats["covered_1000m_percent"],
        height=bar_height,
        label="1000 m"
    )

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(stats["district_name"])

    ax.set_title("District area covered by pharmacy buffers")
    ax.set_xlabel("Covered area [%]")
    ax.set_ylabel("District")
    ax.legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_COVERAGE_CHART, dpi=300)
    plt.close()

    print(f"Saved: {OUTPUT_COVERAGE_CHART}")


def create_visualizations(
    city_boundary: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    pharmacies: gpd.GeoDataFrame,
    service_area_500: gpd.GeoDataFrame,
    service_area_1000: gpd.GeoDataFrame,
    uncovered_area_500: gpd.GeoDataFrame,
    uncovered_area_1000: gpd.GeoDataFrame,
    district_coverage: gpd.GeoDataFrame
) -> None:
    """
    Creates all maps and charts for buffer analysis.
    """
    create_buffer_map(
        city_boundary=city_boundary,
        districts=districts,
        pharmacies=pharmacies,
        service_area=service_area_500,
        uncovered_area=uncovered_area_500,
        distance_m=500,
        output_path=OUTPUT_MAP_500
    )

    create_buffer_map(
        city_boundary=city_boundary,
        districts=districts,
        pharmacies=pharmacies,
        service_area=service_area_1000,
        uncovered_area=uncovered_area_1000,
        distance_m=1000,
        output_path=OUTPUT_MAP_1000
    )

    create_uncovered_map_500(
        city_boundary=city_boundary,
        districts=districts,
        pharmacies=pharmacies,
        uncovered_area_500=uncovered_area_500
    )

    create_district_coverage_map(
        district_coverage=district_coverage,
        column="covered_500m_percent",
        title="District coverage by 500 m pharmacy buffer [%]",
        output_path=OUTPUT_MAP_DISTRICT_COVERAGE_500
    )

    create_district_coverage_map(
        district_coverage=district_coverage,
        column="covered_1000m_percent",
        title="District coverage by 1000 m pharmacy buffer [%]",
        output_path=OUTPUT_MAP_DISTRICT_COVERAGE_1000
    )

    create_coverage_chart(district_coverage)


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

def print_summary(
    city_coverage_results: list[dict],
    district_coverage: gpd.GeoDataFrame
) -> None:
    """
    Prints summary of buffer analysis.
    """
    print("\n--- BUFFER ANALYSIS SUMMARY ---")

    for result in city_coverage_results:
        print(f"\nBuffer distance: {result['buffer_distance_m']} m")
        print(f"City area: {result['city_area_km2']} km²")
        print(f"Covered area: {result['covered_area_km2']} km²")
        print(f"Uncovered area: {result['uncovered_area_km2']} km²")
        print(f"Covered percent: {result['covered_percent']}%")
        print(f"Uncovered percent: {result['uncovered_percent']}%")

    top_500 = district_coverage.sort_values("covered_500m_percent", ascending=False).head(5)
    bottom_500 = district_coverage.sort_values("covered_500m_percent", ascending=True).head(5)

    top_1000 = district_coverage.sort_values("covered_1000m_percent", ascending=False).head(5)
    bottom_1000 = district_coverage.sort_values("covered_1000m_percent", ascending=True).head(5)

    print("\nTop 5 districts by 500 m coverage:")
    for _, row in top_500.iterrows():
        print(f"- {row['district_name']}: {row['covered_500m_percent']}%")

    print("\nBottom 5 districts by 500 m coverage:")
    for _, row in bottom_500.iterrows():
        print(f"- {row['district_name']}: {row['covered_500m_percent']}%")

    print("\nTop 5 districts by 1000 m coverage:")
    for _, row in top_1000.iterrows():
        print(f"- {row['district_name']}: {row['covered_1000m_percent']}%")

    print("\nBottom 5 districts by 1000 m coverage:")
    for _, row in bottom_1000.iterrows():
        print(f"- {row['district_name']}: {row['covered_1000m_percent']}%")

    print("--------------------------------\n")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main() -> None:
    print("Starting pharmacy buffer analysis...")

    city_boundary, districts, pharmacies = load_data()

    city_boundary, districts, pharmacies = prepare_layers(
        city_boundary=city_boundary,
        districts=districts,
        pharmacies=pharmacies
    )

    buffers_500 = create_individual_buffers(pharmacies, 500)
    buffers_1000 = create_individual_buffers(pharmacies, 1000)

    service_area_500 = create_service_area(city_boundary, buffers_500, 500)
    service_area_1000 = create_service_area(city_boundary, buffers_1000, 1000)

    uncovered_area_500 = create_uncovered_area(city_boundary, service_area_500, 500)
    uncovered_area_1000 = create_uncovered_area(city_boundary, service_area_1000, 1000)

    city_coverage_500 = calculate_city_coverage(city_boundary, service_area_500, 500)
    city_coverage_1000 = calculate_city_coverage(city_boundary, service_area_1000, 1000)

    district_coverage = calculate_district_coverage(
        districts=districts,
        service_area_500=service_area_500,
        service_area_1000=service_area_1000
    )

    save_results(
        buffers_500=buffers_500,
        buffers_1000=buffers_1000,
        service_area_500=service_area_500,
        service_area_1000=service_area_1000,
        uncovered_area_500=uncovered_area_500,
        uncovered_area_1000=uncovered_area_1000,
        district_coverage=district_coverage
    )

    create_visualizations(
        city_boundary=city_boundary,
        districts=districts,
        pharmacies=pharmacies,
        service_area_500=service_area_500,
        service_area_1000=service_area_1000,
        uncovered_area_500=uncovered_area_500,
        uncovered_area_1000=uncovered_area_1000,
        district_coverage=district_coverage
    )

    print_summary(
        city_coverage_results=[city_coverage_500, city_coverage_1000],
        district_coverage=district_coverage
    )

    print("Pharmacy buffer analysis completed successfully.")


if __name__ == "__main__":
    main()