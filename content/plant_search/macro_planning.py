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
    targets_gdf["parent_cell_id"] = int(joined_gdf["index_right"])  # Assign cell_id based on spatial join

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