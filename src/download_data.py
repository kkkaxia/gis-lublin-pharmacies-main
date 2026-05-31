from pathlib import Path

import geopandas as gpd
import osmnx as ox


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Project settings
# ---------------------------------------------------------

PLACE_NAME = "Lublin, województwo lubelskie, Poland"

PHARMACY_TAGS = {
    "amenity": "pharmacy"
}


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def save_geodataframe(gdf: gpd.GeoDataFrame, output_path: Path) -> None:
    """
    Saves GeoDataFrame to GeoJSON.
    """
    gdf.to_file(output_path, driver="GeoJSON", encoding="utf-8")
    print(f"Saved: {output_path}")


def clean_osm_features(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Cleans OSM features downloaded by OSMnx.

    OSMnx returns many columns. For this project, we keep only
    the most useful and safe columns.
    """
    gdf = gdf.copy()

    # OSMnx usually returns a MultiIndex: element type + OSM id.
    # We convert it to normal columns.
    gdf = gdf.reset_index()

    useful_columns = [
        "element",
        "id",
        "name",
        "amenity",
        "dispensing",
        "healthcare",
        "opening_hours",
        "phone",
        "website",
        "addr:street",
        "addr:housenumber",
        "addr:city",
        "geometry",
    ]

    existing_columns = [col for col in useful_columns if col in gdf.columns]

    gdf = gdf[existing_columns]

    # Remove rows without geometry
    gdf = gdf[gdf.geometry.notnull()]

    # Set CRS if missing
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)

    return gdf


# ---------------------------------------------------------
# Download functions
# ---------------------------------------------------------

def download_lublin_boundary() -> gpd.GeoDataFrame:
    """
    Downloads the boundary polygon of Lublin from OpenStreetMap.
    """
    print("Downloading Lublin boundary...")

    boundary = ox.geocoder.geocode_to_gdf(PLACE_NAME)

    if boundary.empty:
        raise ValueError("Could not download Lublin boundary.")

    boundary = boundary.to_crs(epsg=4326)

    output_path = RAW_DATA_DIR / "lublin_boundary.geojson"
    save_geodataframe(boundary, output_path)

    print(f"Lublin boundary rows: {len(boundary)}")
    print(f"CRS: {boundary.crs}")

    return boundary


def download_pharmacies() -> gpd.GeoDataFrame:
    """
    Downloads pharmacies in Lublin from OpenStreetMap.
    """
    print("Downloading pharmacies from OpenStreetMap...")

    pharmacies = ox.features.features_from_place(
        PLACE_NAME,
        tags=PHARMACY_TAGS
    )

    if pharmacies.empty:
        raise ValueError("No pharmacies found for Lublin.")

    pharmacies = clean_osm_features(pharmacies)
    pharmacies = pharmacies.to_crs(epsg=4326)

    output_geojson = RAW_DATA_DIR / "pharmacies_lublin.geojson"
    save_geodataframe(pharmacies, output_geojson)

    # CSV without geometry is useful for quick preview
    pharmacies_table = pharmacies.drop(columns="geometry")
    output_csv = RAW_DATA_DIR / "pharmacies_lublin.csv"
    pharmacies_table.to_csv(output_csv, index=False, encoding="utf-8")

    print(f"Saved: {output_csv}")
    print(f"Number of pharmacies: {len(pharmacies)}")
    print(f"CRS: {pharmacies.crs}")

    return pharmacies


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main() -> None:
    print("Starting data download...")

    download_lublin_boundary()
    download_pharmacies()

    print("Data download completed successfully.")


if __name__ == "__main__":
    main()