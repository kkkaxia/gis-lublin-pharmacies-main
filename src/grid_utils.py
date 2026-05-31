from shapely.geometry import Point
import geopandas as gpd
import numpy as np


def generate_points_in_polygon(geometry, spacing=500):

    minx, miny, maxx, maxy = geometry.bounds

    points = []

    x_values = np.arange(minx, maxx, spacing)
    y_values = np.arange(miny, maxy, spacing)

    for x in x_values:
        for y in y_values:

            point = Point(x, y)

            if geometry.contains(point):
                points.append(point)

    return points