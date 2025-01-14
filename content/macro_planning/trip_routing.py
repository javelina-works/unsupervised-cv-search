import numpy as np
import math
from shapely.geometry import LineString
import geopandas as gpd
import pandas as pd

def create_distance_matrix(cell_gdf, base_station_gdf, workload_compensated=False):
    num_cells = len(cell_gdf)

    # Create a distance matrix (excluding intra-workload cost)
    distance_matrix = np.zeros((num_cells + 1, num_cells + 1)) # +1 for the depot location

    depot_geometry = base_station_gdf.geometry.iloc[0]
    # depot_geometry = cell_gdf.iloc[depot_cell_index].geometry.centroid
    depot_index = num_cells # last in the matrix

    for i, row_i in enumerate(cell_gdf.itertuples()):
        for j, row_j in enumerate(cell_gdf.itertuples()):
            if i == j:
                continue # zero for self

            dist = row_i.cell_centroid.distance(row_j.cell_centroid)
            if workload_compensated:
                dist += row_j.intra_workload
            distance_matrix[i][j] = dist

    # Add depot distances
    for i, row in enumerate(cell_gdf.itertuples()):
        dist_to_depot = depot_geometry.distance(row.cell_centroid)
        if workload_compensated:
            dist_to_depot += row.intra_workload

        distance_matrix[i, depot_index] = dist_to_depot  # To depot
        distance_matrix[depot_index, i] = dist_to_depot  # From depot

    distance_matrix[depot_index, depot_index] = 0 # Depot has no self-distance

    integer_distance_matrix = np.ceil(distance_matrix).astype(int) # OR-tools doesn't work with np.float64
    return integer_distance_matrix


# Routing Solvers
# ================
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# from visualize_routing import print_vehicle_details
from macro_planning.visualize_routing import print_vehicle_details

def setup_distance_dimension(routing, manager, core_data):
    """
    Configures the distance dimension to prioritize filling routes close to max_distance,
    leaving the remainder for the last vehicle(s).

    We want to solve routes for our target area such that:
    - We have the fewest total routes to run (fewest batteries to charge)
        - ⇒ routes must be efficient (minimize total distance across all routes)
        - ⇒ routes must be close to max_distance of drone (get the most of each charge)

    Args:
        routing (RoutingModel): The OR-Tools RoutingModel.
        manager (RoutingIndexManager): The OR-Tools RoutingIndexManager.
        core_data (dict): A dictionary containing the data needed for core distance constraint solving

    Returns:
        Dimension: The configured distance dimension.
    """
    # Distance solving callback
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return core_data["distance_matrix"][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add our distance constraint
    distance_dimension_name = "Distance"
    routing.AddDimension(
        transit_callback_index,             # Callback index
        core_data["distance_slack"],        # Slack buffer
        core_data["max_distance"],          # Maximum distance per vehicle
        True,                               # Start cumulative at zero
        distance_dimension_name
    )
    distance_dimension = routing.GetDimensionOrDie(distance_dimension_name) # Class RoutingDimension
    distance_dimension.SetGlobalSpanCostCoefficient(0) # Penalty for difference between longest and shortest routes


    # Penalize routes that don't use the full distance
    num_vehicles = core_data['num_vehicles']
    slack_vehicles = core_data['slack_routes'] # Number of vehicles NOT pushing to fill routes

    for vehicle_id in range(manager.GetNumberOfVehicles()):
        if vehicle_id < num_vehicles - slack_vehicles:
            end_index = routing.End(vehicle_id)
            # Set soft lower bound for all but first N vehicles
            distance_dimension.SetCumulVarSoftLowerBound(end_index, core_data["max_distance"], core_data["distance_slack_penalty"])
        else:
            pass # No lower bound for the first N vehicles (flexible)

    return distance_dimension



def solve_basic_vrp(data, print_routes=False):
    # Setup OR-Tools
    manager = pywrapcp.RoutingIndexManager(
        len(data["core"]["distance_matrix"]),  # Number of nodes (including depot)
        data["core"]["num_vehicles"],          # vehicles (routes) count
        data["core"]["depot_index"])           # Index in distance_matrix representing depot

    routing = pywrapcp.RoutingModel(manager)

    # Distance constraint dimension
    distance_dimension = setup_distance_dimension(routing, manager, data["core"])


    # Solve the problem
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        # routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        routing_enums_pb2.FirstSolutionStrategy.PATH_MOST_CONSTRAINED_ARC
        # routing_enums_pb2.FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION
        # routing_enums_pb2.FirstSolutionStrategy.LOCAL_CHEAPEST_COST_INSERTION
    )

    search_parameters.time_limit.FromSeconds(15)

    solution = routing.SolveWithParameters(search_parameters)
    
    if solution and print_routes:
        # print_vrp_solution(data, manager, routing, solution)
        print_vehicle_details(routing, manager, solution, distance_dimension, data["core"]["max_distance"])

    if solution:
        routes = []
        for vehicle_id in range(data["core"]["num_vehicles"]):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                route.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            routes.append(route)
        return routes
    else:
        print("No solution found.")
        return None



def routes_to_gdf(station_cells_gdf, base_station_gdf, target_routes):
    filtered_routes = [route for route in target_routes if len(route) > 1]

    num_station_cells = len(station_cells_gdf)

    # Convert route indices into actual points
    route_ids = []
    polylines = []
    route_cells = []
    depot_id = base_station_gdf.iloc[0]["depot_id"]

    for i, route in enumerate(filtered_routes):
            cell_ids = []
            points = []
            for index in route:
                if index < num_station_cells:
                    # Point from station_cells_gdf
                    points.append(station_cells_gdf.iloc[index].cell_centroid)
                    cell_ids.append(station_cells_gdf.iloc[index]['cell_id'])
                else:
                    # Must be base station
                    points.append(base_station_gdf.iloc[0].geometry)
                    
            points.append(base_station_gdf.iloc[0].geometry) # Add back home base
            
            route_id = f"{depot_id}_R{i}"
            route_ids.append(route_id)
            polylines.append(LineString(points))
            route_cells.append(cell_ids)

    # Create a GeoDataFrame for the polylines
    routes_gdf = gpd.GeoDataFrame({
        "geometry": polylines,
        "route_id": route_ids,
        "route_depot": depot_id,
        "route_cells": route_cells
    }, crs=station_cells_gdf.crs)
    return routes_gdf




def assign_targets_to_routes(targets_gdf, depots_gdf):
    assignments = []
    for _, target in targets_gdf.iterrows():
        closest_depot = depots_gdf.iloc[target["geometry"].distance(depots_gdf["geometry"]).idxmin()]
        assignments.append({
            "target_id": target.name,  # Assuming unique index as ID
            "route_id": f"route_{closest_depot['depot_id']}",  # Example route naming
            "depot_id": closest_depot["depot_id"]
        })
    
    return pd.DataFrame(assignments)




