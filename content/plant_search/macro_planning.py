import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import distance_matrix
from scipy.sparse.csgraph import minimum_spanning_tree
from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def calculate_intra_cell_workload(cell_targets):
    """
    Calculate the intra-cell workload as the sum of the Minimum Spanning Tree (MST) distances.

    Parameters:
    - cell_targets: ndarray of shape (n, 2)
        Coordinates of the targets within a cell.

    Returns:
    - mst_distance: float
        Total intra-cell workload based on MST distances.
    """
    if cell_targets.shape[0] < 2:
        return 0

    # Compute pairwise distance matrix
    pairwise_dist = distance_matrix(cell_targets, cell_targets)

    mst = minimum_spanning_tree(pairwise_dist) # Compute MST and sum its edges
    mst_distance = mst.sum()
    return mst_distance


def calculate_cell_workloads(cells_gdf, targets_gdf):
    """
    Determine workload per cell from targets. 
    Updates 'cells_gdf' in-place, adding columns.

    Parameters:
    - cells_gdf: GeoDataFrame
        GeoDataFrame of cells (e.g., Voronoi or other tessellation).
    - targets_gdf: GeoDataFrame
        GeoDataFrame of target centroids.
    """
    # Assure GDFs are valid
    cells_gdf["geometry"] = cells_gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
    targets_gdf["geometry"] = targets_gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)


    # 1. Associate targets with cells
    joined_gdf = gpd.sjoin(targets_gdf, cells_gdf, how="left", predicate="within")
    targets_gdf["parent_cell_id"] = joined_gdf["index_right"]  # Assign cell_id based on spatial join

    # 2. Determine total work in each cell
    # joined = gpd.sjoin(cells_gdf, targets_gdf, how="left", predicate="contains")
    # joined_gdf = gpd.sjoin(cells_gdf, targets_gdf, how="inner", predicate="intersects") #  Spatial join: count targets within each cell
    counts = joined_gdf.groupby(targets_gdf['parent_cell_id']).size()  # Count centroids in each cell
    cells_gdf["target_count"] = counts  # Add counts to cells GeoDataFrame
    cells_gdf["target_count"] = cells_gdf["target_count"].fillna(0).astype(int)  # Fill NaN with 0

     # 2. Calculate workloads for each cell
    workloads = []
    for cell_id, cell_row in cells_gdf.iterrows():
        # Get targets associated with the current cell
        cell_targets = targets_gdf[targets_gdf["parent_cell_id"] == cell_id]

        if not cell_targets.empty:
            # Extract target coordinates
            target_coords = np.array([(point.x, point.y) for point in cell_targets["geometry"]])
            workload = calculate_intra_cell_workload(target_coords)
        else:
            workload = 0  # No targets in the cell

        workloads.append(workload)

    cells_gdf["intra_workload"] = workloads # Add workload as a new column in cells_gdf

    return joined_gdf


def create_distance_matrix(cell_gdf, base_station_gdf):
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
            # distance_matrix[i][j] = dist + row_j.intra_workload
            distance_matrix[i][j] = dist

    # Add depot distances
    for i, row in enumerate(cell_gdf.itertuples()):
        dist_to_depot = depot_geometry.distance(row.cell_centroid)
        distance_matrix[i, depot_index] = dist_to_depot  # To depot
        distance_matrix[depot_index, i] = dist_to_depot  # From depot

    
    distance_matrix[depot_index, depot_index] = 0 # Depot has no self-distance

    integer_distance_matrix = np.ceil(distance_matrix).astype(int) # OR-tools doesn't work with np.float64
    return integer_distance_matrix


def print_vrp_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f"Objective: {solution.ObjectiveValue()}")
    max_route_distance = 0
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        plan_output = f"Route for vehicle {vehicle_id}:\n"
        route_distance = 0
        while not routing.IsEnd(index):
            plan_output += f" {manager.IndexToNode(index)} -> "
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id
            )
        plan_output += f"{manager.IndexToNode(index)}\n"
        plan_output += f"Distance of the route: {route_distance}m\n"
        print(plan_output)
        max_route_distance = max(route_distance, max_route_distance)
    print(f"Maximum of the route distances: {max_route_distance}m")


def solve_basic_vrp(data, print_routes=False):
    # Setup OR-Tools
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]),  # +1 for depot
        data["num_vehicles"],      # vehicles count
        data["depot"])      # Depot is at the last index

    routing = pywrapcp.RoutingModel(manager)

    # Distance callback
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["distance_matrix"][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add our distance constraint
    distance_dimension_name = "Distance"
    routing.AddDimension(
        transit_callback_index,  # Callback index
        0,                       # Slack
        data["max_distance"],            # Maximum distance per vehicle
        True,                    # Start cumulative at zero
        distance_dimension_name
    )
    distance_dimension = routing.GetDimensionOrDie(distance_dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Solve the problem
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    solution = routing.SolveWithParameters(search_parameters)
    
    # Extract the solution
    if solution and print_routes:
        print_vrp_solution(data, manager, routing, solution)

    if solution:
        routes = []
        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                route.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            routes.append(route)
        return routes
    else:
        return "No solution found."




# Useful visualizations
# ========================

def plot_cells_with_targets(cells_gdf):
    """
    Plot the region with cells colored by the number of target centroids.

    Parameters:
    - cells_gdf: GeoDataFrame
        GeoDataFrame of cells (e.g., Voronoi or other tessellation).
    - targets_gdf: GeoDataFrame
        GeoDataFrame of target centroids.
    """
    # Plot cells colored by the count of centroids
    fig, ax = plt.subplots(figsize=(10, 8))
    cells_gdf.plot(
        column="target_count",
        cmap="viridis",
        legend=True,
        edgecolor="black",
        ax=ax
    )

    # Annotate cells with the number of centroids
    for _, row in cells_gdf.iterrows():
        if row["target_count"]:  # Only label cells with centroids
            ax.annotate(
                text=row["target_count"],
                xy=row["geometry"].centroid.coords[0],
                ha="center",
                va="center",
                fontsize=8,
                color="white"
            )

    plt.title("Cells Colored by Number of Target Centroids")
    plt.show()


def plot_cells_ids(cells_gdf):
    """
    Plot the region with cells (labeled with IDs) colored by the number of target centroids.

    Parameters:
    - cells_gdf: GeoDataFrame
        GeoDataFrame of cells (e.g., Voronoi or other tessellation).
    - targets_gdf: GeoDataFrame
        GeoDataFrame of target centroids.
    """
    # Plot cells colored by the count of centroids
    fig, ax = plt.subplots(figsize=(10, 8))
    cells_gdf.plot(
        column="target_count",
        cmap="viridis",
        legend=True,
        edgecolor="black",
        ax=ax
    )

    # Annotate cells with the number of centroids
    for _, row in cells_gdf.iterrows():
        ax.annotate(
            text=row["cell_id"],
            xy=row["geometry"].centroid.coords[0],
            ha="center",
            va="center",
            fontsize=8,
            color="white"
        )

    plt.title("Cells Colored by Number of Target Centroids")
    plt.show()