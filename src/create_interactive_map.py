from pathlib import Path

import geopandas as gpd
import pandas as pd
import folium
import branca.colormap as cm
from folium.plugins import MarkerCluster, MiniMap, MeasureControl, Fullscreen


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
MAPS_DIR = BASE_DIR / "maps"

MAPS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Input files
# ---------------------------------------------------------

INPUT_CITY_BOUNDARY = PROCESSED_DATA_DIR / "lublin_boundary_2180.geojson"
INPUT_DISTRICT_STATS = PROCESSED_DATA_DIR / "district_pharmacy_stats_2180.geojson"
INPUT_DISTRICT_COVERAGE = PROCESSED_DATA_DIR / "district_buffer_coverage_stats_2180.geojson"
INPUT_PHARMACIES = PROCESSED_DATA_DIR / "pharmacies_with_districts_2180.geojson"

INPUT_SERVICE_AREA_500 = PROCESSED_DATA_DIR / "pharmacy_service_area_500m_2180.geojson"
INPUT_SERVICE_AREA_1000 = PROCESSED_DATA_DIR / "pharmacy_service_area_1000m_2180.geojson"

INPUT_UNCOVERED_AREA_500 = PROCESSED_DATA_DIR / "pharmacy_uncovered_area_500m_2180.geojson"
INPUT_UNCOVERED_AREA_1000 = PROCESSED_DATA_DIR / "pharmacy_uncovered_area_1000m_2180.geojson"


# ---------------------------------------------------------
# Output file
# ---------------------------------------------------------

OUTPUT_INTERACTIVE_MAP = MAPS_DIR / "lublin_pharmacies_interactive_map.html"


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

PROJECTED_CRS = "EPSG:2180"
WEB_CRS = "EPSG:4326"


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def union_geometries(gdf: gpd.GeoDataFrame):
    """
    Returns one geometry created from all geometries in a GeoDataFrame.
    """
    if hasattr(gdf.geometry, "union_all"):
        return gdf.geometry.union_all()

    return gdf.geometry.unary_union


def clean_value(value, default: str = "No data") -> str:
    """
    Cleans values for popups.
    """
    if value is None:
        return default

    if isinstance(value, float) and pd.isna(value):
        return default

    value = str(value)

    if value.lower() in ["nan", "none", ""]:
        return default

    return value


def load_layer(path: Path, layer_name: str) -> gpd.GeoDataFrame:
    """
    Loads a GeoJSON layer and prepares geometry.
    """
    print(f"Loading {layer_name}...")

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError(f"{layer_name} layer is empty.")

    if gdf.crs is None:
        gdf = gdf.set_crs(PROJECTED_CRS)

    gdf = gdf.to_crs(PROJECTED_CRS)

    gdf = gdf[gdf.geometry.notnull()]
    gdf = gdf[~gdf.geometry.is_empty]

    try:
        gdf["geometry"] = gdf.geometry.make_valid()
    except Exception:
        gdf["geometry"] = gdf.geometry.buffer(0)

    print(f"{layer_name} rows: {len(gdf)}")
    print(f"{layer_name} CRS: {gdf.crs}")

    return gdf


def to_web_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Converts layer to EPSG:4326 for Folium.
    """
    return gdf.to_crs(WEB_CRS)


def get_map_center(city_boundary_2180: gpd.GeoDataFrame) -> list[float]:
    """
    Calculates map center from projected city boundary.
    """
    city_geometry = union_geometries(city_boundary_2180)
    center_point_2180 = city_geometry.centroid

    center_gdf = gpd.GeoDataFrame(
        geometry=[center_point_2180],
        crs=PROJECTED_CRS
    ).to_crs(WEB_CRS)

    center_point_4326 = center_gdf.geometry.iloc[0]

    return [center_point_4326.y, center_point_4326.x]


def calculate_basic_stats(
    city_boundary_2180: gpd.GeoDataFrame,
    pharmacies_2180: gpd.GeoDataFrame,
    service_area_500_2180: gpd.GeoDataFrame,
    service_area_1000_2180: gpd.GeoDataFrame
) -> dict:
    """
    Calculates simple city-level statistics for the information panel.
    """
    city_area_km2 = union_geometries(city_boundary_2180).area / 1_000_000

    service_500_area_km2 = union_geometries(service_area_500_2180).area / 1_000_000
    service_1000_area_km2 = union_geometries(service_area_1000_2180).area / 1_000_000

    return {
        "city_area_km2": round(city_area_km2, 2),
        "pharmacy_count": len(pharmacies_2180),
        "covered_500_km2": round(service_500_area_km2, 2),
        "covered_1000_km2": round(service_1000_area_km2, 2),
        "covered_500_percent": round(service_500_area_km2 / city_area_km2 * 100, 2),
        "covered_1000_percent": round(service_1000_area_km2 / city_area_km2 * 100, 2),
    }


# ---------------------------------------------------------
# Map layers
# ---------------------------------------------------------

def add_city_boundary(
    m: folium.Map,
    city_boundary_4326: gpd.GeoDataFrame
) -> None:
    """
    Adds city boundary layer.
    """
    folium.GeoJson(
        city_boundary_4326.to_json(),
        name="Granica miasta Lublin",
        style_function=lambda feature: {
            "fillColor": "transparent",
            "color": "black",
            "weight": 3,
            "fillOpacity": 0,
        },
    ).add_to(m)


def add_pharmacy_count_layer(
    m: folium.Map,
    district_stats_4326: gpd.GeoDataFrame
) -> None:
    """
    Adds choropleth layer showing number of pharmacies by district.
    """
    print("Adding pharmacy count layer...")

    min_value = int(district_stats_4326["pharmacies_count"].min())
    max_value = int(district_stats_4326["pharmacies_count"].max())

    colormap = cm.linear.YlOrRd_09.scale(min_value, max_value)
    colormap.caption = "Number of pharmacies by district"

    def style_function(feature):
        value = feature["properties"].get("pharmacies_count", 0)

        if value is None:
            value = 0

        return {
            "fillColor": colormap(value),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.65,
        }

    layer = folium.FeatureGroup(
        name="Liczba aptek w dzielnicach",
        show=True
    )

    folium.GeoJson(
        district_stats_4326.to_json(),
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "district_name",
                "pharmacies_count",
                "pharmacies_per_km2",
                "area_km2",
                "rank_by_count",
                "rank_by_density",
            ],
            aliases=[
                "Dzielnica:",
                "Liczba aptek:",
                "Apteki/km²:",
                "Powierzchnia km²:",
                "Ranking liczby:",
                "Ranking gęstości:",
            ],
            localize=True,
            sticky=True,
        ),
    ).add_to(layer)

    layer.add_to(m)
    colormap.add_to(m)


def add_coverage_layer(
    m: folium.Map,
    district_coverage_4326: gpd.GeoDataFrame,
    column: str,
    layer_name: str,
    show: bool
) -> None:
    """
    Adds district coverage choropleth layer.
    """
    print(f"Adding coverage layer: {layer_name}")

    colormap = cm.linear.Greens_09.scale(0, 100)
    colormap.caption = "District area covered by pharmacy buffer [%]"

    def style_function(feature):
        value = feature["properties"].get(column, 0)

        if value is None:
            value = 0

        return {
            "fillColor": colormap(value),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.65,
        }

    layer = folium.FeatureGroup(
        name=layer_name,
        show=show
    )

    folium.GeoJson(
        district_coverage_4326.to_json(),
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "district_name",
                "covered_500m_percent",
                "covered_1000m_percent",
                "uncovered_500m_percent",
                "uncovered_1000m_percent",
            ],
            aliases=[
                "Dzielnica:",
                "Pokrycie 500 m [%]:",
                "Pokrycie 1000 m [%]:",
                "Poza 500 m [%]:",
                "Poza 1000 m [%]:",
            ],
            localize=True,
            sticky=True,
        ),
    ).add_to(layer)

    layer.add_to(m)


def add_service_area_layer(
    m: folium.Map,
    service_area_4326: gpd.GeoDataFrame,
    layer_name: str,
    fill_color: str,
    show: bool
) -> None:
    """
    Adds dissolved pharmacy service area layer.
    """
    print(f"Adding service area layer: {layer_name}")

    layer = folium.FeatureGroup(
        name=layer_name,
        show=show
    )

    folium.GeoJson(
        service_area_4326.to_json(),
        style_function=lambda feature: {
            "fillColor": fill_color,
            "color": fill_color,
            "weight": 1,
            "fillOpacity": 0.35,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["buffer_distance_m", "area_km2"],
            aliases=["Bufor m:", "Powierzchnia km²:"],
            localize=True,
            sticky=True,
        ),
    ).add_to(layer)

    layer.add_to(m)


def add_uncovered_area_layer(
    m: folium.Map,
    uncovered_area_4326: gpd.GeoDataFrame,
    layer_name: str,
    show: bool
) -> None:
    """
    Adds uncovered area layer.
    """
    print(f"Adding uncovered area layer: {layer_name}")

    layer = folium.FeatureGroup(
        name=layer_name,
        show=show
    )

    folium.GeoJson(
        uncovered_area_4326.to_json(),
        style_function=lambda feature: {
            "fillColor": "#d7191c",
            "color": "#d7191c",
            "weight": 1,
            "fillOpacity": 0.35,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["buffer_distance_m", "area_km2"],
            aliases=["Poza buforem m:", "Powierzchnia km²:"],
            localize=True,
            sticky=True,
        ),
    ).add_to(layer)

    layer.add_to(m)


def add_pharmacy_markers(
    m: folium.Map,
    pharmacies_4326: gpd.GeoDataFrame
) -> None:
    """
    Adds pharmacy markers with popups.
    """
    print("Adding pharmacy markers...")

    marker_cluster = MarkerCluster(
        name="Apteki - punkty",
        show=True
    ).add_to(m)

    for _, row in pharmacies_4326.iterrows():
        geometry = row.geometry

        if geometry.geom_type != "Point":
            geometry = geometry.representative_point()

        pharmacy_name = clean_value(row.get("name"), "Unknown pharmacy")
        district_name = clean_value(row.get("district_name"), "No district")
        pharmacy_id = clean_value(row.get("pharmacy_id"), "No ID")

        street = clean_value(row.get("addr:street"), "")
        house_number = clean_value(row.get("addr:housenumber"), "")

        address = f"{street} {house_number}".strip()

        if not address:
            address = "No address data"

        popup_html = f"""
        <div style="font-family: Arial; font-size: 13px;">
            <b>{pharmacy_name}</b><br>
            <hr style="margin: 5px 0;">
            <b>Dzielnica:</b> {district_name}<br>
            <b>Adres:</b> {address}<br>
            <b>ID:</b> {pharmacy_id}
        </div>
        """

        folium.Marker(
            location=[geometry.y, geometry.x],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=pharmacy_name,
            icon=folium.Icon(color="red", icon="plus-sign")
        ).add_to(marker_cluster)


def add_information_panel(
    m: folium.Map,
    stats: dict
) -> None:
    """
    Adds custom information panel to the map.
    """
    html = f"""
    <div style="
        position: fixed;
        bottom: 40px;
        left: 40px;
        width: 310px;
        z-index: 9999;
        background-color: white;
        border: 2px solid #444;
        border-radius: 8px;
        padding: 12px;
        font-family: Arial;
        font-size: 13px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.3);
    ">
        <h4 style="margin-top: 0;">GIS: Pharmacy Accessibility in Lublin</h4>
        <b>City area:</b> {stats["city_area_km2"]} km²<br>
        <b>Number of pharmacies:</b> {stats["pharmacy_count"]}<br>
        <b>500 m coverage:</b> {stats["covered_500_percent"]}% 
        ({stats["covered_500_km2"]} km²)<br>
        <b>1000 m coverage:</b> {stats["covered_1000_percent"]}% 
        ({stats["covered_1000_km2"]} km²)<br>
        <hr style="margin: 8px 0;">
        <span style="font-size: 12px;">
            Distances are based on Euclidean buffers, not real walking routes.
        </span>
    </div>
    """

    m.get_root().html.add_child(folium.Element(html))


# ---------------------------------------------------------
# Main map creation
# ---------------------------------------------------------

def create_interactive_map() -> None:
    """
    Creates the final interactive Folium map.
    """
    print("Starting interactive map creation...")

    # Load projected layers
    city_boundary_2180 = load_layer(INPUT_CITY_BOUNDARY, "city boundary")
    district_stats_2180 = load_layer(INPUT_DISTRICT_STATS, "district pharmacy statistics")
    district_coverage_2180 = load_layer(INPUT_DISTRICT_COVERAGE, "district buffer coverage")
    pharmacies_2180 = load_layer(INPUT_PHARMACIES, "pharmacies")

    service_area_500_2180 = load_layer(INPUT_SERVICE_AREA_500, "500 m service area")
    service_area_1000_2180 = load_layer(INPUT_SERVICE_AREA_1000, "1000 m service area")

    uncovered_area_500_2180 = load_layer(INPUT_UNCOVERED_AREA_500, "500 m uncovered area")
    uncovered_area_1000_2180 = load_layer(INPUT_UNCOVERED_AREA_1000, "1000 m uncovered area")

    # Calculate stats before conversion to EPSG:4326
    stats = calculate_basic_stats(
        city_boundary_2180=city_boundary_2180,
        pharmacies_2180=pharmacies_2180,
        service_area_500_2180=service_area_500_2180,
        service_area_1000_2180=service_area_1000_2180
    )

    # Convert layers to EPSG:4326 for Folium
    city_boundary_4326 = to_web_crs(city_boundary_2180)
    district_stats_4326 = to_web_crs(district_stats_2180)
    district_coverage_4326 = to_web_crs(district_coverage_2180)
    pharmacies_4326 = to_web_crs(pharmacies_2180)

    service_area_500_4326 = to_web_crs(service_area_500_2180)
    service_area_1000_4326 = to_web_crs(service_area_1000_2180)

    uncovered_area_500_4326 = to_web_crs(uncovered_area_500_2180)
    uncovered_area_1000_4326 = to_web_crs(uncovered_area_1000_2180)

    # Create base map
    map_center = get_map_center(city_boundary_2180)

    m = folium.Map(
        location=map_center,
        zoom_start=12,
        tiles="CartoDB positron",
        control_scale=True
    )

    # Add layers
    add_city_boundary(m, city_boundary_4326)

    add_service_area_layer(
        m=m,
        service_area_4326=service_area_1000_4326,
        layer_name="Zasięg aptek - bufor 1000 m",
        fill_color="#2b83ba",
        show=False
    )

    add_service_area_layer(
        m=m,
        service_area_4326=service_area_500_4326,
        layer_name="Zasięg aptek - bufor 500 m",
        fill_color="#1a9641",
        show=False
    )

    add_uncovered_area_layer(
        m=m,
        uncovered_area_4326=uncovered_area_500_4326,
        layer_name="Obszary poza zasięgiem 500 m",
        show=False
    )

    add_uncovered_area_layer(
        m=m,
        uncovered_area_4326=uncovered_area_1000_4326,
        layer_name="Obszary poza zasięgiem 1000 m",
        show=False
    )

    add_pharmacy_count_layer(m, district_stats_4326)

    add_coverage_layer(
        m=m,
        district_coverage_4326=district_coverage_4326,
        column="covered_500m_percent",
        layer_name="Pokrycie dzielnic buforem 500 m [%]",
        show=False
    )

    add_coverage_layer(
        m=m,
        district_coverage_4326=district_coverage_4326,
        column="covered_1000m_percent",
        layer_name="Pokrycie dzielnic buforem 1000 m [%]",
        show=False
    )

    add_pharmacy_markers(m, pharmacies_4326)

    # Plugins
    MiniMap(toggle_display=True).add_to(m)
    MeasureControl(
        position="topleft",
        primary_length_unit="meters",
        secondary_length_unit="kilometers"
    ).add_to(m)
    Fullscreen(position="topleft").add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    add_information_panel(m, stats)

    # Save map
    m.save(OUTPUT_INTERACTIVE_MAP)

    print(f"Saved interactive map: {OUTPUT_INTERACTIVE_MAP}")
    print("Interactive map creation completed successfully.")


if __name__ == "__main__":
    create_interactive_map()