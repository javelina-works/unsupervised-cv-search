import matplotlib.pyplot as plt
import geopandas as gpd

def plot_targets_by_route(region_outline_gdf, cells_gdf, targets_gdf, depot_id):
    """
    Plot all targets for a single depot, coloring targets by route_id.

    Parameters:
    - targets_gdf: GeoDataFrame
        GeoDataFrame containing target points with 'route_id' and 'parent_cell_id' columns.
    - depot_id: str
        The depot_id to filter and plot routes from.
    """
    # Filter targets for the given depot_id
    depot_targets = targets_gdf[targets_gdf['route_id'].str.startswith(depot_id)]
    
    # Get unique route_ids for the depot
    unique_routes = depot_targets['route_id'].unique()
    
    # Set up the plot
    fig, ax = plt.subplots(figsize=(10, 8))
    region_outline_gdf.boundary.plot(ax=ax, color="blue", linestyle="--", label="Simplified Region Outline")
    cells_gdf.boundary.plot(ax=ax, color="blue", linewidth=1, alpha=0.5, label="Voronoi Cells")  # Region cells
    # base_station_gdf.plot(ax=ax, color='red', markersize=80, marker='*', zorder=10, label='Base Station')
    
    # Plot targets for each route_id in a different color
    for route_id in unique_routes:
        route_targets = depot_targets[depot_targets['route_id'] == route_id]
        route_targets.plot(ax=ax, marker='o', label=route_id, alpha=0.6)
    
    # Set plot labels and legend
    ax.set_title(f"Targets by Route for Depot {depot_id}", fontsize=16)
    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)
    ax.legend(title="Route ID", fontsize=10, loc='best')
    plt.show()


def plot_depot_micro_routes(region_outline_gdf, cells_gdf, results, depot_point):
    """
    Plot TSP routes for all route_ids associated with a depot.

    Parameters:
    - results: dict
        Dictionary of TSP results, where keys are route_ids and values are
        {'ordered_points': list of shapely.geometry.Point, 'total_distance': float}.
    - depot_point: shapely.geometry.Point
        Coordinates of the depot, plotted as a reference point.
    - macro_routes_gdf: GeoDataFrame
        GeoDataFrame containing route information for labeling.
    """
    # Set up the plot
    fig, ax = plt.subplots(figsize=(12, 10))
    region_outline_gdf.boundary.plot(ax=ax, color="blue", linestyle="--", label="Simplified Region Outline")
    cells_gdf.boundary.plot(ax=ax, color="blue", linewidth=1, alpha=0.5, label="Voronoi Cells")  # Region cells
    
    # Plot each route with a unique color
    for route_id, data in results.items():
        ordered_points = data['ordered_points']
        x_coords, y_coords = zip(*[(point.x, point.y) for point in ordered_points])
        
        # Plot the route as a line
        ax.plot(x_coords, y_coords, label=f"{route_id} (Distance: {data['total_distance']:.2f})", alpha=0.7)
        ax.scatter(x_coords, y_coords, s=40)  # Plot the points
        
    # Plot the depot
    ax.scatter(depot_point.x, depot_point.y, color='red', s=100, label='Depot', zorder=5)
    
    # Set plot labels and legend
    ax.set_title("TSP Routes by Route ID", fontsize=16)
    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)
    ax.legend(title="Routes", fontsize=10, loc='best')
    plt.show()
