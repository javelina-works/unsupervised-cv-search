import geopandas as gpd
import pandas as pd
import numpy as np

# TODO: remove plant_search dependency
from plant_search.macro_planning import calculate_intra_cell_workload


def create_cells_depots_df(depots_gdf, cells_gdf, target_crs="EPSG:32613"):
    """
    Associates cells with depots, computing the closest depot and associated depots.
    Ensures CRS is in meters for accurate distance calculations.
    
    Parameters:
        depots_gdf (GeoDataFrame): Depots with geometry and radius.
        cells_gdf (GeoDataFrame): Cells with geometry.
        target_crs (str): Target CRS (e.g., "EPSG:32614") for distance calculations.
    
    Returns:
        cells_depots_df: DataFrame containing cell-depot associations with distances.
    """

    # Copy and reproject GeoDataFrames to the target CRS
    depots_proj = depots_gdf.to_crs(target_crs)
    cells_proj = cells_gdf.to_crs(target_crs)

    records = [] # Initialize list to store results

    # Iterate through each cell to compute associations
    for _, cell in cells_proj.iterrows():

        # Filter depots where the cell is fully within the depot's range radius
        associated_depots = [
            depot["depot_id"]
            for _, depot in depots_proj.iterrows()
            if cell.geometry.within(depot["geometry"].buffer(depot.get("depot_radius", 0)))
        ]
        
        # Compute distances to associated depots and find the closest one
        if associated_depots:
            distances = {
                depot["depot_id"]: cell.geometry.centroid.distance(depot["geometry"])
                for _, depot in depots_proj[depots_proj["depot_id"].isin(associated_depots)].iterrows()
            }
            closest_depot = min(distances, key=distances.get)
            closest_distance = distances[closest_depot]
        else:
            closest_depot = None
            closest_distance = None

        records.append({
            "cell_id": cell["cell_id"],
            "closest_depot": closest_depot,
            "associated_depots": associated_depots,
            "distance": closest_distance,
        })

    cells_depots_df = pd.DataFrame(records)
    return cells_depots_df



def create_cell_targets_df(cells_gdf, targets_gdf):
    """
    Associates each target with a cell

    Parameters:
    - targets_gdf: GeoDataFrame
        GeoDataFrame of target centroids.
    - cells_gdf: GeoDataFrame
        GeoDataFrame of cells (e.g., Voronoi or other tessellation).
    """
    # Assure GDFs are valid
    targets_gdf["geometry"] = targets_gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
    cells_gdf["geometry"] = cells_gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)

    # Targets within each cell
    joined_gdf = gpd.sjoin(targets_gdf, cells_gdf, how="left", predicate="intersects")
    
    # Remove all targets not in any cell (out of bounds)
    joined_gdf = joined_gdf[joined_gdf["index_right"].notna()]

    cell_targets_df = joined_gdf.assign(
        target_index=joined_gdf.index,
        target_id=joined_gdf["target_id"],
        cell_id=joined_gdf["index_right"]
    ).reset_index(drop=True)[["cell_id", "target_index", "target_id", "geometry"]]

    return cell_targets_df



def create_cell_workloads_df(cells_gdf, targets_gdf, cell_targets_df=None):
    """
    Creates a DataFrame summarizing the workload for each cell, including target count and intra-cell workload.

    Parameters:
    - cells_gdf (GeoDataFrame): GeoDataFrame containing cell geometries.
    - targets_gdf (GeoDataFrame): GeoDataFrame containing target geometries.
    - cell_targets_df (DataFrame, optional): Precomputed DataFrame associating targets with cells.

    Returns:
    - DataFrame: A DataFrame containing cell_id, target_count, and workload for each cell.
    """
    # Assure GDFs are valid
    cells_gdf["geometry"] = cells_gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
    targets_gdf["geometry"] = targets_gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)

    # Create cell-target associations if not passed in
    if cell_targets_df is None:
        cell_targets_df = create_cell_targets_df(cells_gdf, targets_gdf)

    cell_workloads = []
    for cell_id, group in cell_targets_df.groupby("cell_id"):
        target_ids = group['target_id'].values # IDs of all targets associated with this cell_id

        # Get GDFs of all these targets
        cell_targets = targets_gdf[targets_gdf['target_id'].isin(target_ids)]

        # Extract coordinates from geometry
        targets_coords = np.array([[geom.x, geom.y] for geom in cell_targets["geometry"]])

        workload = calculate_intra_cell_workload(targets_coords) if len(targets_coords) > 1 else 0
        cell_workloads.append({
            "cell_id": cell_id,
            "target_count": len(group),
            "workload": workload
        })

    cell_workloads_df = pd.DataFrame(cell_workloads)
    return cell_workloads_df
