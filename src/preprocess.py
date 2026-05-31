from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
MAPS_DIR = BASE_DIR / "maps"

PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

INPUT_BOUNDARY = RAW_DATA_DIR / "lublin_boundary.geojson"
INPUT_PHARMACIES = RAW_DATA_DIR / "pharmacies_lublin.geojson"

OUTPUT_BOUNDARY_2180 = PROCESSED_DATA_DIR / "lublin_boundary_2180.geojson"
OUTPUT_PHARMACIES_CLEAN_4326 = PROCESSED_DATA_DIR / "pharmacies_lublin_clean_4326.geojson"
OUTPUT_PHARMACIES_POINTS_2180 = PROCESSED_DATA_DIR / "pharmacies_lublin_points_2180.geojson"
OUTPUT_PHARMACIES_CSV = PROCESSED_DATA_DIR / "pharmacies_lublin_clean.csv"

OUTPUT_PREVIEW_MAP = MAPS_DIR / "pharmacies_preview.png"

TARGET_CRS = "EPSG:2180"


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def load_data() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Loads raw boundary and pharmacy data.
    """
    print("Loading raw data...")

    if not INPUT_BOUNDARY.exists():
        raise FileNotFoundError(f"Missing file: {INPUT_BOUNDARY}")

    if not INPUT_PHARMACIES.exists():
        raise FileNotFoundError(f"Missing file: {INPUT_PHARMACIES}")

    boundary = gpd.read_file(INPUT_BOUNDARY)
    pharmacies = gpd.read_file(INPUT_PHARMACIES)

    print(f"Boundary rows: {len(boundary)}")
    print(f"Pharmacy rows: {len(pharmacies)}")
    print(f"Boundary CRS: {boundary.crs}")
    print(f"Pharmacies CRS: {pharmacies.crs}")

    return boundary, pharmacies


def fix_crs(boundary: gpd.GeoDataFrame, pharmacies: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Ensures that both layers use EPSG:4326 at the raw stage.
    """
    print("Checking CRS...")

    if boundary.crs is None:
        boundary = boundary.set_crs(epsg=4326)

    if pharmacies.crs is None:
        pharmacies = pharmacies.set_crs(epsg=4326)

    boundary = boundary.to_crs(epsg=4326)
    pharmacies = pharmacies.to_crs(epsg=4326)

    return boundary, pharmacies


def remove_empty_geometries(gdf: gpd.GeoDataFrame, layer_name: str) -> gpd.GeoDataFrame:
    """
    Removes rows with missing or empty geometry.
    """
    before = len(gdf)

    gdf = gdf[gdf.geometry.notnull()]
    gdf = gdf[~gdf.geometry.is_empty]

    after = len(gdf)

    print(f"{layer_name}: removed {before - after} rows with empty geometry.")

    return gdf


def create_point_layer(pharmacies: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Converts pharmacy geometries to points.

    Some OSM objects may be saved as polygons instead of points.
    For accessibility analysis, every pharmacy should be represented by one point.
    """
    print("Converting pharmacy geometries to points...")

    pharmacies = pharmacies.copy()

    pharmacies["original_geometry_type"] = pharmacies.geometry.geom_type

    pharmacies["geometry"] = pharmacies.geometry.apply(
        lambda geom: geom if geom.geom_type == "Point" else geom.representative_point()
    )

    return pharmacies


def filter_pharmacies_inside_lublin(
    boundary: gpd.GeoDataFrame,
    pharmacies: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Keeps only pharmacies located inside the Lublin boundary.
    """
    print("Filtering pharmacies inside Lublin boundary...")

    before = len(pharmacies)

    if hasattr(boundary.geometry, "union_all"):
        city_geometry = boundary.geometry.union_all()
    else:
        city_geometry = boundary.geometry.unary_union

    pharmacies = pharmacies[pharmacies.geometry.within(city_geometry)]

    after = len(pharmacies)

    print(f"Pharmacies before filtering: {before}")
    print(f"Pharmacies after filtering: {after}")
    print(f"Removed pharmacies outside boundary: {before - after}")

    return pharmacies


def add_basic_columns(pharmacies: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Adds useful columns for later analysis.
    """
    print("Adding basic columns...")

    pharmacies = pharmacies.copy()
    pharmacies = pharmacies.reset_index(drop=True)

    pharmacies["pharmacy_id"] = range(1, len(pharmacies) + 1)

    pharmacies["longitude"] = pharmacies.geometry.x
    pharmacies["latitude"] = pharmacies.geometry.y

    if "name" not in pharmacies.columns:
        pharmacies["name"] = None

    pharmacies["name"] = pharmacies["name"].fillna("Unknown pharmacy")

    return pharmacies


def prepare_for_saving(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Converts complex column values to strings if needed.
    This prevents errors when saving to GeoJSON.
    """
    gdf = gdf.copy()

    for column in gdf.columns:
        if column == gdf.geometry.name:
            continue

        gdf[column] = gdf[column].apply(
            lambda value: ", ".join(map(str, value))
            if isinstance(value, list)
            else str(value)
            if isinstance(value, dict)
            else value
        )

    return gdf


def save_processed_data(
    boundary: gpd.GeoDataFrame,
    pharmacies_clean_4326: gpd.GeoDataFrame,
    pharmacies_points_2180: gpd.GeoDataFrame
) -> None:
    """
    Saves cleaned datasets.
    """
    print("Saving processed data...")

    boundary_2180 = boundary.to_crs(TARGET_CRS)

    boundary_2180 = prepare_for_saving(boundary_2180)
    pharmacies_clean_4326 = prepare_for_saving(pharmacies_clean_4326)
    pharmacies_points_2180 = prepare_for_saving(pharmacies_points_2180)

    boundary_2180.to_file(OUTPUT_BOUNDARY_2180, driver="GeoJSON", encoding="utf-8")
    pharmacies_clean_4326.to_file(OUTPUT_PHARMACIES_CLEAN_4326, driver="GeoJSON", encoding="utf-8")
    pharmacies_points_2180.to_file(OUTPUT_PHARMACIES_POINTS_2180, driver="GeoJSON", encoding="utf-8")

    pharmacies_table = pharmacies_clean_4326.drop(columns="geometry")
    pharmacies_table.to_csv(OUTPUT_PHARMACIES_CSV, index=False, encoding="utf-8")

    print(f"Saved: {OUTPUT_BOUNDARY_2180}")
    print(f"Saved: {OUTPUT_PHARMACIES_CLEAN_4326}")
    print(f"Saved: {OUTPUT_PHARMACIES_POINTS_2180}")
    print(f"Saved: {OUTPUT_PHARMACIES_CSV}")


def create_preview_map(
    boundary_2180: gpd.GeoDataFrame,
    pharmacies_2180: gpd.GeoDataFrame
) -> None:
    """
    Creates a simple static preview map.
    """
    print("Creating preview map...")

    fig, ax = plt.subplots(figsize=(10, 10))

    boundary_2180.boundary.plot(ax=ax, linewidth=1)
    pharmacies_2180.plot(ax=ax, markersize=8)

    ax.set_title("Pharmacies in Lublin - preview map")
    ax.set_xlabel("X coordinate")
    ax.set_ylabel("Y coordinate")

    plt.tight_layout()
    plt.savefig(OUTPUT_PREVIEW_MAP, dpi=300)
    plt.close()

    print(f"Saved: {OUTPUT_PREVIEW_MAP}")


def print_summary(
    boundary_2180: gpd.GeoDataFrame,
    pharmacies_2180: gpd.GeoDataFrame
) -> None:
    """
    Prints basic information about the processed data.
    """
    city_area_km2 = boundary_2180.geometry.area.sum() / 1_000_000

    print("\n--- SUMMARY ---")
    print(f"Number of pharmacies: {len(pharmacies_2180)}")
    print(f"Lublin area: {city_area_km2:.2f} km²")
    print(f"Pharmacies per km²: {len(pharmacies_2180) / city_area_km2:.2f}")
    print(f"Target CRS: {TARGET_CRS}")
    print("----------------\n")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main() -> None:
    print("Starting preprocessing...")

    boundary, pharmacies = load_data()

    boundary, pharmacies = fix_crs(boundary, pharmacies)

    boundary = remove_empty_geometries(boundary, "Boundary")
    pharmacies = remove_empty_geometries(pharmacies, "Pharmacies")

    pharmacies_points_4326 = create_point_layer(pharmacies)
    pharmacies_points_4326 = filter_pharmacies_inside_lublin(boundary, pharmacies_points_4326)
    pharmacies_points_4326 = add_basic_columns(pharmacies_points_4326)

    boundary_2180 = boundary.to_crs(TARGET_CRS)
    pharmacies_points_2180 = pharmacies_points_4326.to_crs(TARGET_CRS)

    save_processed_data(
        boundary=boundary,
        pharmacies_clean_4326=pharmacies_points_4326,
        pharmacies_points_2180=pharmacies_points_2180
    )

    create_preview_map(boundary_2180, pharmacies_points_2180)

    print_summary(boundary_2180, pharmacies_points_2180)

    print("Preprocessing completed successfully.")


if __name__ == "__main__":
    main()