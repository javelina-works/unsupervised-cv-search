import rasterio
import numpy as np
import cv2
from shapely.geometry import Polygon
import geopandas as gpd


def extract_region_contour(geotiff_path, tolerance=5):
    """
    Extract the contour of a binary mask using OpenCV's findContours.
    Then simplify polygon by reducing its vertices.

    Parameters:
        geotiff_path (str): Path to the GeoTIFF file.
        tolerance (float): Tolerance for simplification. Higher values result in greater simplification.

    Returns:
        GeoDataFrame: (Simplified) Contour as a polygon.
    """
    with rasterio.open(geotiff_path) as src:
        data = src.read(1) # Read the first band

        # Create a binary mask for valid data
        mask = (data != 0).astype(np.uint8)  # Convert to uint8 for OpenCV
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest_contour = max(contours, key=cv2.contourArea) # Assume largest contour is primary region

        # Convert contour points to spatial coordinates
        contour_coords = [src.xy(int(pt[0][1]), int(pt[0][0])) for pt in largest_contour]
        contour_polygon = Polygon(contour_coords)

        # Simplify outline if non-zero tolerane passed
        if(tolerance > 0):
            contour_polygon = contour_polygon.simplify(tolerance, preserve_topology=True)

    # Convert to GeoDataFrame
    return gpd.GeoDataFrame({"geometry": [contour_polygon]}, crs=src.crs)





