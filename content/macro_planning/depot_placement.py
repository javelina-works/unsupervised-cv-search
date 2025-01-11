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



def assign_cells_to_depot(depots_gdf, cell_gdf):

    selected_depots = depots_gdf.geometry

    def distance_to_depot(polygon, depot):
        return polygon.centroid.distance(Point(depot.x, depot.y))

    # Determine the closest depot for multi-depot cells
    def closest_depot(polygon, depot_IDs):
        distances = {i: distance_to_depot(polygon, depots_gdf.loc[depots_gdf['depot_id'] == i]['geometry']) for i in depot_IDs}
        return min(distances, key=distances.get)


    # Assign each cell to its covering depots
    cell_depots_gdf = cell_gdf.copy() # Create new GDF associating cells with depots
    cell_depots_gdf['associated_depots'] = cell_depots_gdf['geometry'].apply(
        lambda polygon: [
            depot.get("depot_id", i) for i, depot in depots_gdf.iterrows()
            if polygon.within(depot['geometry'].buffer(depot.get("depot_radius", 0)))
        ]
    )

    cell_depots_gdf['closest_depot'] = cell_depots_gdf.apply(
        lambda row:
            row['associated_depots'][0]
            if len(row['associated_depots']) == 1
            else closest_depot(row['geometry'], row['associated_depots']),
            axis=1
    )


    # # Prepare a GeoDataFrame for single-depot cells
    # single_depot_gdf = cell_depots_gdf[cell_depots_gdf['associated_depots'].apply(len) == 1].copy()
    # single_depot_gdf['depot_id'] = single_depot_gdf['associated_depots'].apply(lambda x: x[0])

    # # Prepare a GeoDataFrame for multi-depot cells
    # multi_depot_gdf = cell_gdf[cell_depots_gdf['associated_depots'].apply(len) > 1].copy()
    # multi_depot_gdf['closest_depot'] = multi_depot_gdf.apply(
    #     lambda row: closest_depot(row['geometry'], row['associated_depots']),
    #     axis=1
    # )

    return  cell_depots_gdf