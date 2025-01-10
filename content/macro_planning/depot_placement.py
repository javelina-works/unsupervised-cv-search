from typing import Union
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, PULP_CBC_CMD, HiGHS_CMD
import matplotlib.pyplot as plt


def find_depots(depot_radius: float, cell_gdf: gpd.GeoDataFrame, region_polygon: Union[Polygon, gpd.GeoDataFrame], grid_density:int=2) -> gpd.GeoDataFrame:
    """
    Find the optimal depot locations to cover all cells within a given region.

    Parameters:
    - depot_radius (float): The radius within which a depot can cover a cell.
    - cell_gdf (GeoDataFrame): GeoDataFrame of cells with geometries (polygons).
    - region_polygon (Union[Polygon, GeoDataFrame]): The overall work region as a Polygon or GeoDataFrame.
    - grid_density (int): Density of points for candidate depot locations (higher is slower, more robust)

    Returns:
    - GeoDataFrame: GeoDataFrame containing the optimal depot locations.
    """
    # Validate inputs
    if depot_radius <= 0:
        raise ValueError("Depot radius must be a positive value.")
    if cell_gdf.empty:
        raise ValueError("The cells GeoDataFrame is empty.")
    if not isinstance(region_polygon, (Polygon, gpd.GeoDataFrame)):
        raise TypeError("Region polygon must be a Shapely Polygon or a GeoDataFrame.")
    
    if isinstance(region_polygon, gpd.GeoDataFrame):
        region_polygon = region_polygon.unary_union  # Combine geometries if a GeoDataFrame

    
    # Define bounds of the work region
    min_x, min_y, max_x, max_y = cell_gdf.total_bounds

    # Generate grid points with a fixed spacing
    grid_spacing = depot_radius / grid_density  # Adjust this value for finer or coarser grids (more candidate points)
    grid_points = [
        Point(x, y)
        for x in np.arange(min_x, max_x, grid_spacing)
        for y in np.arange(min_y, max_y, grid_spacing)
        if region_polygon.contains(Point(x, y))  # Only keep points within the work region
    ]

    # List of all points we will check for a possible valid depot location
    potential_depots = [polygon.centroid for polygon in cell_gdf['geometry']] + grid_points

    coverage_matrix = [] # Coverage matrix: is a given cell covered by a depot location?
    for polygon in cell_gdf['geometry']:
        row = [polygon.within(depot.buffer(depot_radius)) for depot in potential_depots]
        coverage_matrix.append(row)

    problem = LpProblem("Geometric_Set_Cover", LpMinimize) # ILP Problem Definition

    # Variables: 1 if depot is selected, 0 otherwise
    depot_vars = [LpVariable(f"depot_{i}", cat="Binary") for i in range(len(potential_depots))]
    problem += lpSum(depot_vars) # Objective: Minimize the number of depots

    # Constraints: Each polygon must be covered by at least one depot
    for i, polygon in enumerate(cell_gdf['geometry']):
        problem += lpSum(depot_vars[j] for j, covers in enumerate(coverage_matrix[i]) if covers) >= 1
    problem.solve(PULP_CBC_CMD(msg=False))

    # Extract selected depots
    selected_depots = [
        {"geometry": potential_depots[i], "depot_radius": depot_radius, "depot_id": f"depot_{i}"}
        for i, var in enumerate(depot_vars) if var.varValue == 1
    ]
    depots_gdf = gpd.GeoDataFrame(selected_depots, crs=cell_gdf.crs)

    return depots_gdf

