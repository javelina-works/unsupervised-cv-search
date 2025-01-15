import geopandas as gpd


def targets_cells_df(targets_gdf, cells_gdf):
    """
    Determine workload per cell from targets. 
    Updates 'cells_gdf' in-place, adding columns.

    Parameters:
    - targets_gdf: GeoDataFrame
        GeoDataFrame of target centroids.
    - cells_gdf: GeoDataFrame
        GeoDataFrame of cells (e.g., Voronoi or other tessellation).
    """
    # Assure GDFs are valid
    targets_gdf["geometry"] = targets_gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
    cells_gdf["geometry"] = cells_gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)


    joined_gdf = gpd.sjoin(targets_gdf, cells_gdf, how="left", predicate="intersects")
    cell_targets_df = joined_gdf.assign(
        target_id=joined_gdf.index,
        cell_id=joined_gdf["index_right"]
    ).reset_index(drop=True)[["cell_id", "target_id", "geometry"]]

    # Extract target coordinates
    cell_targets_df["geometry"] = cell_targets_df["geometry"]
    # cell_targets_df = cell_targets_df.drop(columns=["geometry"])

    return cell_targets_df