from pathlib import Path
from urllib.request import urlretrieve
from zipfile import ZipFile
import shutil

import geopandas as gpd
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
MAPS_DIR = BASE_DIR / "maps"

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

# Official Lublin Open Data SHP resource for district boundaries
DISTRICTS_URL = "https://gis.lublin.eu/api/shp/administracja/dzielnice_granice"

DISTRICTS_ZIP = RAW_DATA_DIR / "lublin_districts.zip"
DISTRICTS_SHP_DIR = RAW_DATA_DIR / "lublin_districts_shp"

OUTPUT_DISTRICTS_4326 = PROCESSED_DATA_DIR / "lublin_districts_4326.geojson"
OUTPUT_DISTRICTS_2180 = PROCESSED_DATA_DIR / "lublin_districts_2180.geojson"

OUTPUT_PREVIEW_MAP = MAPS_DIR / "districts_preview.png"

# PL-1992, good for area/distance calculations in Poland
TARGET_CRS = "EPSG:2180"

# The source description says the SHP is in "układ 2000 strefa 8".
# This is EPSG:2179.
SOURCE_FALLBACK_CRS = "EPSG:2179"


# ---------------------------------------------------------
# Manual fixes for broken Polish characters
# ---------------------------------------------------------

DISTRICT_NAME_FIXES = {
    "?ródmie?cie": "Śródmieście",
    "�ródmie�cie": "Śródmieście",

    "S?awinek": "Sławinek",
    "S�awinek": "Sławinek",

    "S?awin": "Sławin",
    "S�awin": "Sławin",

    "W?glin Pd.": "Węglin Pd.",
    "W�glin Pd.": "Węglin Pd.",

    "W?glin P?n.": "Węglin Płn.",
    "W�glin P�n.": "Węglin Płn.",

    "Dziesi?ta": "Dziesiąta",
    "Dziesi�ta": "Dziesiąta",

    "G?usk": "Głusk",
    "G�usk": "Głusk",

    "Hajdów - Zad?bie": "Hajdów - Zadębie",
    "Hajdów - Zad�bie": "Hajdów - Zadębie",

    "Ko?minek": "Kośminek",
    "Ko�minek": "Kośminek",

    "Czechów P?.": "Czechów Płn.",
    "Czechów P�.": "Czechów Płn.",

    "Czuby P?n.": "Czuby Płn.",
    "Czuby P�n.": "Czuby Płn.",

    "Za Cukrowni?": "Za Cukrownią",
    "Za Cukrowni�": "Za Cukrownią",
}


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def has_broken_characters(names: list[str]) -> bool:
    """
    Checks if district names contain broken characters.
    """
    return any(("?" in name) or ("�" in name) for name in names)


def repair_district_name(name: str) -> str:
    """
    Repairs broken Polish characters in district names.
    """
    name = str(name).strip()

    if name in DISTRICT_NAME_FIXES:
        return DISTRICT_NAME_FIXES[name]

    return name


def download_zip() -> None:
    """
    Downloads district boundaries ZIP file.
    """
    print("Downloading Lublin district boundaries...")

    urlretrieve(DISTRICTS_URL, DISTRICTS_ZIP)

    if not DISTRICTS_ZIP.exists():
        raise FileNotFoundError("District ZIP file was not downloaded.")

    print(f"Saved: {DISTRICTS_ZIP}")


def unzip_file() -> None:
    """
    Unzips downloaded SHP archive.
    """
    print("Unzipping district boundaries...")

    # Remove old extracted files to avoid using stale data
    if DISTRICTS_SHP_DIR.exists():
        shutil.rmtree(DISTRICTS_SHP_DIR)

    DISTRICTS_SHP_DIR.mkdir(parents=True, exist_ok=True)

    with ZipFile(DISTRICTS_ZIP, "r") as zip_ref:
        zip_ref.extractall(DISTRICTS_SHP_DIR)

    print(f"Extracted to: {DISTRICTS_SHP_DIR}")


def find_shapefile() -> Path:
    """
    Finds the first .shp file in the extracted directory.
    """
    print("Searching for .shp file...")

    shp_files = list(DISTRICTS_SHP_DIR.rglob("*.shp"))

    if not shp_files:
        raise FileNotFoundError("No .shp file found in extracted district data.")

    shp_path = shp_files[0]

    print(f"Found shapefile: {shp_path}")

    return shp_path


def read_shapefile_with_best_encoding(shp_path: Path) -> tuple[gpd.GeoDataFrame, str]:
    """
    Tries different encodings and returns the version with the cleanest names.

    Sometimes GeoPandas can read the file, but the Polish characters are already
    damaged in the loaded text. That is why we do not accept the first successful
    read automatically.
    """
    encodings_to_try = [
        "utf-8",
        "cp1250",
        "windows-1250",
        "iso-8859-2",
        "latin2",
    ]

    best_districts = None
    best_encoding = "unknown"
    best_broken_count = 10**9

    for encoding in encodings_to_try:
        try:
            print(f"Trying encoding: {encoding}")

            temp_districts = gpd.read_file(shp_path, encoding=encoding)

            if "nazwa" not in temp_districts.columns:
                print(f"Encoding {encoding}: column 'nazwa' not found.")
                continue

            names = temp_districts["nazwa"].astype(str).tolist()

            broken_count = sum(
                name.count("?") + name.count("�")
                for name in names
            )

            print(f"Encoding {encoding}: broken characters count = {broken_count}")

            if broken_count < best_broken_count:
                best_districts = temp_districts
                best_encoding = encoding
                best_broken_count = broken_count

            if broken_count == 0:
                break

        except Exception as error:
            print(f"Encoding failed: {encoding}. Error: {error}")

    if best_districts is None:
        raise ValueError("Could not read district boundaries with tested encodings.")

    return best_districts, best_encoding


def load_districts(shp_path: Path) -> gpd.GeoDataFrame:
    """
    Loads district boundaries from SHP.
    """
    print("Loading district boundaries...")

    districts, used_encoding = read_shapefile_with_best_encoding(shp_path)

    print(f"Used encoding: {used_encoding}")
    print(f"District rows: {len(districts)}")
    print(f"Original CRS: {districts.crs}")
    print("Columns:")
    print(list(districts.columns))

    if "nazwa" in districts.columns:
        print("District names preview before repair:")
        print(districts["nazwa"].head(10).astype(str).tolist())

    if districts.empty:
        raise ValueError("District layer is empty.")

    if districts.crs is None:
        print(f"CRS is missing. Setting fallback CRS: {SOURCE_FALLBACK_CRS}")
        districts = districts.set_crs(SOURCE_FALLBACK_CRS)

    return districts


def clean_districts(districts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Cleans district data and creates a standard district_name column.
    """
    print("Cleaning district data...")

    districts = districts.copy()

    districts = districts[districts.geometry.notnull()]
    districts = districts[~districts.geometry.is_empty]

    districts["geometry"] = districts.geometry.make_valid()

    possible_name_columns = [
        "nazwa",
        "NAZWA",
        "Nazwa",
        "dzielnica",
        "DZIELNICA",
        "Dzielnica",
        "name",
        "NAME",
    ]

    name_column = None

    for column in possible_name_columns:
        if column in districts.columns:
            name_column = column
            break

    if name_column is None:
        object_columns = [
            column for column in districts.columns
            if districts[column].dtype == "object" and column != "geometry"
        ]

        if object_columns:
            name_column = object_columns[0]
            print(f"No obvious name column found. Using first text column: {name_column}")
        else:
            print("No text column found. Creating artificial district names.")
            districts["district_name"] = [
                f"District {i}" for i in range(1, len(districts) + 1)
            ]
            name_column = "district_name"

    # Create repaired district name
    districts["district_name"] = districts[name_column].astype(str).apply(repair_district_name)

    # Check if there are still broken names after manual repair
    repaired_names = districts["district_name"].astype(str).tolist()

    if has_broken_characters(repaired_names):
        print("\nWARNING: Some district names still contain broken characters:")
        for name in repaired_names:
            if "?" in name or "�" in name:
                print(f"- {name}")
        print("Add these names to DISTRICT_NAME_FIXES if needed.\n")
    else:
        print("District names repaired successfully.")

    districts = districts.reset_index(drop=True)
    districts["district_id"] = range(1, len(districts) + 1)

    # Keep useful columns only
    districts = districts[["district_id", "district_name", "geometry"]]

    return districts


def save_districts(districts: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Saves districts in EPSG:4326 and EPSG:2180.
    """
    print("Saving processed district data...")

    districts_4326 = districts.to_crs(epsg=4326)
    districts_2180 = districts.to_crs(TARGET_CRS)

    districts_4326.to_file(OUTPUT_DISTRICTS_4326, driver="GeoJSON", encoding="utf-8")
    districts_2180.to_file(OUTPUT_DISTRICTS_2180, driver="GeoJSON", encoding="utf-8")

    print(f"Saved: {OUTPUT_DISTRICTS_4326}")
    print(f"Saved: {OUTPUT_DISTRICTS_2180}")

    return districts_4326, districts_2180


def create_preview_map(districts_2180: gpd.GeoDataFrame) -> None:
    """
    Creates a preview map with district boundaries and labels.
    """
    print("Creating district preview map...")

    fig, ax = plt.subplots(figsize=(10, 10))

    districts_2180.boundary.plot(ax=ax, linewidth=1)

    for _, row in districts_2180.iterrows():
        point = row.geometry.representative_point()
        ax.text(
            point.x,
            point.y,
            row["district_name"],
            fontsize=6,
            ha="center"
        )

    ax.set_title("District boundaries in Lublin")
    ax.set_xlabel("X coordinate")
    ax.set_ylabel("Y coordinate")

    plt.tight_layout()
    plt.savefig(OUTPUT_PREVIEW_MAP, dpi=300)
    plt.close()

    print(f"Saved: {OUTPUT_PREVIEW_MAP}")


def print_summary(districts_2180: gpd.GeoDataFrame) -> None:
    """
    Prints district summary.
    """
    districts_2180 = districts_2180.copy()
    districts_2180["area_km2"] = districts_2180.geometry.area / 1_000_000

    print("\n--- DISTRICTS SUMMARY ---")
    print(f"Number of districts: {len(districts_2180)}")
    print(f"Total area: {districts_2180['area_km2'].sum():.2f} km²")
    print("\nDistricts:")

    for name in districts_2180["district_name"].sort_values():
        print(f"- {name}")

    print("-------------------------\n")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main() -> None:
    print("Starting district data download and preprocessing...")

    download_zip()
    unzip_file()

    shp_path = find_shapefile()

    districts = load_districts(shp_path)
    districts = clean_districts(districts)

    _, districts_2180 = save_districts(districts)

    create_preview_map(districts_2180)
    print_summary(districts_2180)

    print("District data preprocessing completed successfully.")


if __name__ == "__main__":
    main()