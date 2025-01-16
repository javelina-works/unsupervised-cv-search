from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from shapely.geometry import LineString, Point
import geopandas as gpd

def calculate_tsp_route(route_targets_gdf, depot_point):
    """
    Calculate the TSP approximate shortest path for targets in a given route.

    Parameters:
    - route_targets_gdf: GeoDataFrame
        GeoDataFrame of targets for a specific route_id.
    - depot_point: shapely.geometry.Point
        Coordinates of the depot, used as the starting and ending point.

    Returns:
    - ordered_points: list of shapely.geometry.Point
        The ordered sequence of points representing the TSP route.
    - total_distance: float
        The total distance of the TSP route.
    """
    # Combine depot and targets into a single list of points
    points = [depot_point] + list(route_targets_gdf["geometry"])
    num_points = len(points)
    
    # Create distance matrix
    def distance_matrix():
        return [
            [points[i].distance(points[j]) for j in range(num_points)]
            for i in range(num_points)
        ]
    
    dist_matrix = distance_matrix()

    # Create the TSP solver
    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(dist_matrix[from_node][to_node] * 1000)  # Scale for integer optimization

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Solve TSP
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        raise ValueError("No solution found for TSP!")

    # Extract the ordered sequence of points
    index = routing.Start(0)
    ordered_points = []
    while not routing.IsEnd(index):
        node_index = manager.IndexToNode(index)
        ordered_points.append(points[node_index])
        index = solution.Value(routing.NextVar(index))
    ordered_points.append(points[0])  # Return to depot

    # Calculate total distance
    total_distance = sum(
        ordered_points[i].distance(ordered_points[i + 1]) for i in range(len(ordered_points) - 1)
    )
    
    return ordered_points, total_distance



def calculate_all_routes_tsp(routed_targets_gdf, depot_point_gdf):
    """
    Calculate the TSP route for all targets grouped by route_id.
    
    Parameters:
    - targets_gdf: GeoDataFrame
        GeoDataFrame of all targets, including route_id and geometry.
    - macro_routes_gdf: GeoDataFrame
        GeoDataFrame of macro routes with route_id and associated route_cells.
    - depot_point: shapely.geometry.Point
        Coordinates of the depot, used as the starting and ending point.

    Returns:
    - results: dict
        Dictionary where keys are route_ids and values are (ordered_points, total_distance).
    """
    results = {}
    unique_route_ids = routed_targets_gdf["route_id"].unique()

    plot_depot_id = depot_point_gdf.iloc[0]['depot_id']
    route_targets_gdf = routed_targets_gdf[routed_targets_gdf['closest_depot'] == plot_depot_id]
    depot_point = depot_point_gdf.iloc[0]['geometry']

    for route_id in unique_route_ids:
        route_targets = route_targets_gdf[route_targets_gdf["route_id"] == route_id]
        if not route_targets.empty:
            ordered_points, total_distance = calculate_tsp_route(route_targets, depot_point)
            results[route_id] = {"ordered_points": ordered_points, "total_distance": total_distance}
    
    return results



def create_micro_routes_gdf(results, macro_routes_gdf, depot_point):
    """
    Create a GeoDataFrame of polylines for the solved micro routes.

    Parameters:
    - results: dict
        Dictionary of TSP results, where keys are route_ids and values are
        {'ordered_points': list of shapely.geometry.Point, 'total_distance': float}.
    - macro_routes_gdf: GeoDataFrame
        GeoDataFrame containing route information (e.g., route_cells, route_id).
    - depot_point: shapely.geometry.Point
        Coordinates of the depot.

    Returns:
    - routes_gdf: GeoDataFrame
        GeoDataFrame of polylines with columns for 'route_id', 'closest_depot', and 'route_cells'.
    """
    route_ids = []
    polylines = []
    closest_depots = []
    route_cells_list = []

    for route_id, data in results.items():
        ordered_points = data['ordered_points']
        route_line = LineString(ordered_points)  # Create a LineString from the ordered points

        # Get the corresponding row in macro_routes_gdf for additional attributes
        macro_route_row = macro_routes_gdf[macro_routes_gdf['route_id'] == route_id].iloc[0]
        route_cells = macro_route_row['route_cells']

        # Append data for the GeoDataFrame
        route_ids.append(route_id)
        polylines.append(route_line)
        closest_depots.append(depot_point)
        route_cells_list.append(route_cells)

    # Create the GeoDataFrame
    routes_gdf = gpd.GeoDataFrame({
        "route_id": route_ids,
        "geometry": polylines,
        "closest_depot": closest_depots,
        "route_cells": route_cells_list
    }, crs=macro_routes_gdf.crs)
    
    return routes_gdf