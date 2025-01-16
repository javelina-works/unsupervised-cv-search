# ---
# jupyter:
#   jupytext:
#     notebook_metadata_filter: all
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.4
#   kernelspec:
#     display_name: venv
#     language: python
#     name: python3
#   language_info:
#     codemirror_mode:
#       name: ipython
#       version: 3
#     file_extension: .py
#     mimetype: text/x-python
#     name: python
#     nbconvert_exporter: python
#     pygments_lexer: ipython3
#     version: 3.11.5
# ---

# # Work Planning Prototype
#
# **Background**: In our previous notebooks, we have a collection of techniques for performing, allocating, and analyzing our work. We anticipate that the scope of work will be greater than our hardware's ability to complete in a single charge. We should therefore carefully plan the work we aim to do in advance of arriving at a work site so that we come much more prepared.
#
#
# Perhaps we follow a plan like:
# - Prepare region image
#     - Consolidate to single geotiff
#     - Re-project CRS
#     - Filter, smooth, simplify, downsample
# - Parition region into manageable pieces
#     - Call them "work areas/sites/plots", e.g. 1/2 acre spaces
# - Segmentation & masking?
# - Plan macro/micro routes
#     - Macro: 1/2 acre work spaces
#     - Micro: route between plants in a work space
# - Execute? Store execution results? Analyze performance?
#

# ## Prepare Region Image
#
# - Consolidate to single geotiff
# - Reproject CRS
# - Image pre-processing

# +
import sys
from pathlib import Path

# Add the parent directory to the Python path
# So we can find local modules e.g. "plant_search"
sys.path.append(str(Path.cwd().parent))

# file_path = 'input/ESPG-4326-orthophoto.tif'
# file_path = 'input/MADRID_RGB.tif'
# file_path = '../input/aerial-trees.jpg'

# file_path = '../input/DJI_0010.JPG'
# file_path = '../input/DJI_0015.JPG'
# file_path = '../input/DJI_0093.JPG'
# file_path = '../input/DJI_0119.JPG'

# file_path = '../input/IGNORE_Brewster-ortho.tif'
file_path = '../input/IGNORE_Brewster-2024-all-orthophoto-UTM-32613.tif'


# +
from plant_search.load_image import load_image, plot_image, plot_geotiff

ds = 4 # downscale ratio

image, transform, bounds, image_crs = load_image(file_path)

# We have a georeferenced image
if image is not None and transform and bounds:
    original_image_shape = image.shape
    image = image[::ds, ::ds]
    # Calculate extent in geographic coordinates
    image_extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
    plot_geotiff(image, transform, bounds, "Working Region")

# We have image, but not georeferenced
elif image is not None and bounds:
    original_image_shape = image.shape
    height, width = image.shape[:2]
    image_extent = (0, width, 0, height)
    image = image[::ds, ::ds]
    plot_image(image, "Original Image")

print(f"Image dimensions: {image.shape}")
# -

# ## Parition Region
# - Create outline polygon of full work region
#     - Simplify geometry for faster execution
# - Divide full region into working areas

# +
region_crs = 32613 # Use this everywhere for consistency

simplification_tolerance = 5

# Convert target area to square meters
target_area_acres = 0.5
# target_area_acres = 1.5
# target_area_acres = 2.5

max_iterations = 15

# +
from plant_search.region_partition import (
    extract_region_contour,
    simplify_polygon,
    generate_voronoi_partition,
    centroidal_voronoi_tessellation,
)
import matplotlib.pyplot as plt
import geopandas as gpd


region_contour_gpd = extract_region_contour(file_path)
contour_gdf_projected = region_contour_gpd.to_crs(epsg=region_crs)  # Example: UTM Zone 14N
simplified_polygon = simplify_polygon(contour_gdf_projected.geometry.iloc[0], simplification_tolerance)

target_area_sqm = target_area_acres * 4046.86
num_points = int(simplified_polygon.area / target_area_sqm)

# voronoi_gdf, points_gdf = generate_voronoi_partition(simplified_polygon, num_points)
cell_gdf = centroidal_voronoi_tessellation(simplified_polygon, num_points, max_iterations)


fig, ax = plt.subplots(figsize=(10, 10))

gpd.GeoDataFrame({"geometry": [simplified_polygon]}).boundary.plot(ax=ax, color="blue", linestyle="--", label="Simplified Region Outline")
cell_gdf.boundary.plot(ax=ax, color="blue", alpha=0.5, label="Voronoi Cell Polygons")
cell_gdf.set_geometry('cell_centroid').plot(ax=ax, color="red", markersize=10, label="Cell Centroid Points")

plt.legend()
plt.title("Region Partition")
plt.show()
# -

# ## Macro Planning
#
# ### Background
#
# This section is predicated on a number of assumptions about the nature of our work.
#
# **Assumptions:**
# -  Our greatest priority is to minimize total time on job, and therefore operational expense
#     - Battery charging duration is greatest time bottleneck
#     - Travel distance and time is secondary efficiency concern
# -  We cannot complete our work areas in a single trip (on a single battery charge)
#     - ⇒ Traveling Salesman Problem solution is insufficient (not contiguous, single path)
#     - "Stopping" and "resuming" TSP to recharge is inefficient
#         - Adds unaccounted overhead with returns
# - A high-level macro-plan simplification of our work area is a useful and representative approximation of our work area
# - The presented solution will be useful and representative of future work areas
#
# **Problem Approach:**
# What problem are we trying to solve?
#
# We want to plan a number of routes such that:
# 1. We have the fewest reasonable number of routes (minimal turn-around)
# 2. Each route uses almost all of the battery (no wasted capacity)
# 3. Each route uses battery efficiently (implied by 1, energy expended working, not in transit)
# 4. Routes do not interfere with efficiency of other routes (2,3)
#     - Each route is efficient individually, while together all routes are efficient
#     - Implies simultaneous solving
#
#
# ### Intro
#
# Since we have divided our working region into smaller, more manageable portions, we can now plan our approach. We will use our cells to help measure area completion and divide work areas more efficiently. 
#
# This section is concerned with:
# - clustering of cells into trips
# - prioritization of cells
# - global trip efficiency
#     - A.K.A. Multi-Trip Routing Problem (MTRP)
# - Completion efficiency
#
# Our planning inputs:
# - cells and centroids
# - base station location
#     - where drones launch and land
# - drone battery range
# - target density per cell

# ### Simple Macro Routing
# We want to compute routes which are efficient and cover our work area in the fewest total trips. This is known as a **Vehicle Routing Problem** (VRP), in which our only dimension of constraint is the range of our drone. 
#
# In this section we  will generate efficient routes to visit the centroid of every cell in our working area such that the routes meet our above requirements. Of course, our greater goal is not to just visit every cell in our area. Later, we will account for the work (number, density, distance of targets) in each cell.
#
#
# Parameters:
# - `max_distance`: The maximum range of the drone, in meters. We will try to find trips as close to this length as possible to use up the full battery.
# - `distance_slack`: Represents amount of "slack" we can have in a route without incurring penalty. We will rarely ever find a route at *exactly* 'max_distance'. This variable sets how permissive we can be for these routes.
#  - `distance_slack_penalty`: Multiplier for penalty incurred when a route is less than a lower bound distance. We set the soft lower bound to 'max_distance' and the multiplier high to encourage routes to get as close to full length as possible.
#  - `slack_routes`: The number of routes we are *not* going to try to force to the max distance. We will use this to clean up "remainder" routes/cells after full-length routes are generated.

# +
from shapely.geometry import Point
import geopandas as gpd

# Base station location
base_station_coords = (634500,3347200) # Center of region
# base_station_coords = (634400,3347100) # Where we parked
base_station_gdf = gpd.GeoDataFrame(
    [{'geometry': Point(base_station_coords)}],
    crs=region_crs
)

# + tags=["parameters"]
max_distance = 990  # Max distance per trip (meters)
distance_slack = 50
distance_slack_penalty = 10_000
slack_routes = 5
num_vehicles = 20

# +
from macro_planning.trip_routing import (
    create_distance_matrix,
    solve_basic_vrp,
)
from macro_planning.visualize_routing import plot_vrp_solution

distance_matrix = create_distance_matrix(cell_gdf, base_station_gdf) # excluding intra-workload cost
num_cells = len(distance_matrix)-1 # Number of stops
# num_vehicles = math.ceil(math.sqrt(num_cells)) + 1

# print(f"num_cells: {num_cells}")
# print(f"num_vehicles: {num_vehicles}")

data = {
    "core": {
        "distance_matrix": distance_matrix,
        "num_vehicles": num_vehicles,
        "depot_index": num_cells,
        "max_distance": max_distance,
        "distance_slack": distance_slack,
        "distance_slack_penalty": distance_slack_penalty,
        "slack_routes": slack_routes
    }
}

print_routes = True # Set to True to see individual route statistics
routes = solve_basic_vrp(data, print_routes)

# If solved, plot solution
plot_vrp_solution(cell_gdf, distance_matrix, simplified_polygon, base_station_gdf, routes)

# -

# ### Region Target Search
#
# If not computationally prohibitive, we can perform our target search on the full working area. Even at a much lower resolution, this can help us determine the total number of target plants in each cell, and ultimately on each route.
#
# This is just using the CV search techniques we explored earlier.

# +
from plant_search.image_preprocess import (
    generate_target_mask,
    correct_binary_mask,
    identify_targets,
)
import rasterio

# binary_mask = generate_target_mask(image) # Generate

# Load mask the easy way
binary_mask_path = "../outputs/region_binary_mask.tif"
with rasterio.open(binary_mask_path) as src:
    binary_mask = src.read(1)  # Read the first band
    bin_transform = src.transform  # Get the affine transform
    bin_crs = src.crs  # Get the CRS

full_binary_mask = correct_binary_mask(binary_mask, original_image_shape)
targets_gdf = identify_targets(full_binary_mask, transform)


del full_binary_mask # Gimme back my RAM
print(f"Number of targets (detected plants): {len(targets_gdf)}")

# +
# # Instead of re-computing, save to image
# binary_mask_scaled = (binary_mask * 255).astype("uint8")

# with rasterio.open(file_path) as src:
#     image_region_crs = src.crs

# # Save the georeferenced binary mask with the correct scaling
# with rasterio.open(
#     "../outputs/region_binary_mask.tif",
#     "w",
#     driver="GTiff",
#     height=binary_mask.shape[0],
#     width=binary_mask.shape[1],
#     count=1,
#     dtype="uint8",
#     crs=image_region_crs,
#     transform=transform,
# ) as dst:
#     dst.write(binary_mask_scaled, 1)

# +
# test_point_coords = (634191.0566301036, 3347310.085296234) 
# test_point_gdf = gpd.GeoDataFrame(
#     [{'geometry': Point(test_point_coords)}],
#     crs=region_crs
# )

# +
import matplotlib.patches as mpatches

# Display identified targets
fig, ax = plt.subplots(figsize=(15, 15))
# ax.imshow(image, extent=image_extent, alpha=0.8) # Display original image
ax.imshow(binary_mask, extent=image_extent, cmap='gray') # Show targets binary mask

# Region outline, cells, centroids
gpd.GeoDataFrame({"geometry": [simplified_polygon]}).boundary.plot(ax=ax, color="blue", linestyle="--", label="Simplified Region Outline")
cell_gdf.boundary.plot(ax=ax, color="blue", alpha=0.5, label="Voronoi Cells") # Region cells
# cell_gdf.set_geometry('cell_centroid').plot(ax=ax, color="red", markersize=10, label="Cell Centroids")
base_station_gdf.plot(ax=ax, color='red', markersize=60, marker='*', label='Base Station')
# test_point_gdf.plot(ax=ax, color='purple', markersize=60, marker='*', label='Base Station')

targets_gdf.plot(ax=ax, color='green', markersize=3, label='Centroids') # Plot targets centroids
targets_gdf.set_geometry('bounding_box').plot(ax=ax, edgecolor='orange', facecolor='none', linewidth=1.0) # Plot targets bounding boxes

# Fix legend for bounding boxes
handles, labels = ax.get_legend_handles_labels()
bounding_box_patch = mpatches.Patch(edgecolor='orange', facecolor='none', label='Bounding Boxes') # Add a custom handle for the bounding boxes
handles.append(bounding_box_patch)
labels.append('Bounding Boxes')

ax.legend(handles, labels, loc='upper right')
# plt.legend()
plt.title("Region Partition with Targets")
plt.show()
# -

# ### Calculate Cell Densities
#
# First-pass system to determine:
# - Number of targets in each cell
# - Distance to traverse all targets in each cell

# +
from plant_search.macro_planning import (
    calculate_cell_workloads,
    plot_cells_with_targets,
    plot_cells_ids,
)


calculate_cell_workloads(cell_gdf, targets_gdf) # In-place updates

# Ensure base station is a valid Point geometry

# Compute distance from each cell centroid to the base station
base_station_point = base_station_gdf.geometry.iloc[0]
cell_gdf['home_distance'] = cell_gdf['cell_centroid'].distance(base_station_point)
# cell_gdf['total_workload'] = cell_gdf['intra_workload'] + (2 * cell_gdf['home_distance'])

# Visualize cell workloads
# plot_cells_with_targets(cell_gdf)
plot_cells_ids(cell_gdf)

# targets_gdf
# joined
# cell_gdf
# -

# ### Target-Compensated Trip Routing
#
# In our previous section, we solved for routes which efficiently covered every cell in our working area. However, this assumed that the only cost associated with each cell was the distance to its centroid. 
#
# To make our approximation more effective, we will also want to account for the distance *within* each cell that the drone will take to address all of the targets. We will add `intra_workload` to our distance matrix to approximate this distance.

t_max_distance = 1100  # Max distance per trip (meters)
t_distance_slack = 50
t_distance_slack_penalty = 10_000
t_slack_routes = 5
t_num_vehicles = 25

# +
from macro_planning.trip_routing import (
    create_distance_matrix,
    solve_basic_vrp,
)
from macro_planning.visualize_routing import (
    plot_vrp_solution,
    distance_matrix_heatmap,
    distance_matrix_plot_distances
)

compensate_for_targets = True
t_distance_matrix = create_distance_matrix(cell_gdf, base_station_gdf, compensate_for_targets) # excluding intra-workload cost
t_num_cells = len(t_distance_matrix)-1 # Number of stops
# num_vehicles = math.ceil(math.sqrt(num_cells)) + 1

# distance_matrix_heatmap(t_distance_matrix)
# distance_matrix_plot_distances(cell_gdf, t_distance_matrix, simplified_polygon, base_station_gdf)

# print(f"num_cells: {num_cells}")
# print(f"num_vehicles: {num_vehicles}")

target_data = {
    "core": {
        "distance_matrix": t_distance_matrix,
        "num_vehicles": t_num_vehicles,
        "depot_index": t_num_cells,
        "max_distance": t_max_distance,
        "distance_slack": t_distance_slack,
        "distance_slack_penalty": t_distance_slack_penalty,
        "slack_routes": t_slack_routes
    }
}

print_routes = True # Set to True to see individual route statistics
target_routes = solve_basic_vrp(target_data, print_routes)

# If solved, plot solution
if target_routes and isinstance(target_routes, list):
    t_title = "Workload-Compensated Routes"
    plot_vrp_solution(cell_gdf, t_distance_matrix, simplified_polygon, base_station_gdf, target_routes, t_title)

# -

# ### Depot Placement
#
# At some point, our work area will be simply too large to address every cell which contains targets. We will need to have multiple depot points from which we launch drones. 
#
# But how can we determine where these depot points might be? Using our same Voronoi partitioning skills from earlier.

# +
# cell_gdf
# cell_gdf['cell_centroid'].aggregate('union')

# +
import numpy as np


# Step 2: Smallest Enclosing Sphere (SES) for each cluster
def smallest_enclosing_circle(points):
    """
    Compute the smallest enclosing circle (2D sphere) for a set of points.
    Uses Welzl's algorithm for efficiency.
    """
    center = np.mean(points, axis=0)  # Initial guess: centroid
    max_dist = max(np.linalg.norm(points - center, axis=1))
    return center, max_dist


# +
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt


# Parameters
depot_radius = 200  # Max distance a depot can cover

# Function to find polygons fully covered by a circle
def polygons_within_circle(center, polygons, radius):
    coverage_circle = center.buffer(radius)
    return [polygon for polygon in polygons if coverage_circle.contains(polygon)]

# Greedy algorithm to solve the Geometric Set Cover Problem for polygons
remaining_polygons = list(cell_gdf['geometry'])
depots = []

while remaining_polygons:
    # Find the point that covers the maximum number of remaining polygons
    best_center = None
    best_coverage = []
    for candidate_polygon in remaining_polygons:
        candidate_center = candidate_polygon.centroid
        coverage = polygons_within_circle(candidate_center, remaining_polygons, depot_radius)
        if len(coverage) > len(best_coverage):
            best_center = candidate_center
            best_coverage = coverage
    
    # Place a depot at the best center
    depots.append((best_center.x, best_center.y))
    
    # Remove covered polygons from the list of remaining polygons
    remaining_polygons = [polygon for polygon in remaining_polygons if polygon not in best_coverage]

# Visualization
fig, ax = plt.subplots(figsize=(12, 12))
cell_gdf.plot(ax=ax, color='blue', alpha=0.6, label='Polygons')

for depot in depots:
    circle = plt.Circle(depot, depot_radius, color='red', fill=False, linestyle='--', label='Depot Coverage')
    ax.add_patch(circle)
    ax.scatter(depot[0], depot[1], color='red', marker='x', s=100, label='Depot')

plt.title("Geometric Set Cover Solution for Polygons")
plt.xlabel("X Coordinate")
plt.ylabel("Y Coordinate")
# plt.legend()
plt.grid(True)
plt.show()

print(f"Number of depots placed: {len(depots)}")


# +
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, PULP_CBC_CMD, HiGHS_CMD
import matplotlib.pyplot as plt


# Parameters
depot_radius = 220  # Max distance a depot can cover

# Define bounds of the work region
min_x, min_y, max_x, max_y = cell_gdf.total_bounds

# Generate grid points with a fixed spacing
grid_spacing = depot_radius / 2  # Adjust this value for finer or coarser grids
grid_points = [
    Point(x, y)
    for x in np.arange(min_x, max_x, grid_spacing)
    for y in np.arange(min_y, max_y, grid_spacing)
    if simplified_polygon.contains(Point(x, y))  # Only keep points within the work region
]

potential_depots = [polygon.centroid for polygon in cell_gdf['geometry']] + grid_points



# Create coverage matrix
coverage_matrix = []
for polygon in cell_gdf['geometry']:
    row = [polygon.within(depot.buffer(depot_radius)) for depot in potential_depots]
    coverage_matrix.append(row)

# ILP Problem Definition
problem = LpProblem("Geometric_Set_Cover", LpMinimize)

# Variables: 1 if depot is selected, 0 otherwise
depot_vars = [LpVariable(f"depot_{i}", cat="Binary") for i in range(len(potential_depots))]
problem += lpSum(depot_vars) # Objective: Minimize the number of depots

# Constraints: Each polygon must be covered by at least one depot
for i, polygon in enumerate(cell_gdf['geometry']):
    problem += lpSum(depot_vars[j] for j, covers in enumerate(coverage_matrix[i]) if covers) >= 1
problem.solve(PULP_CBC_CMD(msg=False))

# Extract selected depots
selected_depots = [potential_depots[i] for i, var in enumerate(depot_vars) if var.varValue == 1]



# Visualizations
fig, ax = plt.subplots(figsize=(12, 12))
cell_gdf.boundary.plot(ax=ax, color='blue', alpha=0.6, label='Cell Polygons')

potential_depots_gdf = gpd.GeoDataFrame({'geometry': [Point(depot.x, depot.y) for depot in potential_depots]})
potential_depots_gdf.plot(ax=ax, color='green', marker='o', label='Potential Depots', markersize=3)


# Plot selected depots and their coverage
for depot in selected_depots:
    circle = plt.Circle((depot.x, depot.y), depot_radius, color='red', fill=False, linestyle='--', label='Depot Coverage')
    ax.add_patch(circle)
    ax.scatter(depot.x, depot.y, color='red', marker='x', s=100, label='Depot')

plt.title("Optimal Depot Placement (ILP Solution)")
plt.xlabel("X Coordinate")
plt.ylabel("Y Coordinate")
# plt.legend()
plt.grid(True)
plt.show()

print(f"Number of depots placed: {len(selected_depots)}")


# +
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
from matplotlib.colors import ListedColormap
import random

def distance_to_depot(polygon, depot):
    return polygon.centroid.distance(Point(depot.x, depot.y))

# Determine the closest depot for multi-depot cells
def closest_depot(polygon, depot_indices):
    distances = {i: distance_to_depot(polygon, selected_depots[i]) for i in depot_indices}
    return min(distances, key=distances.get)


# Assign each cell to its covering depots
cell_gdf['associated_depots'] = cell_gdf['geometry'].apply(
    lambda polygon: [
        i for i, depot in enumerate(selected_depots)
        if polygon.within(Point(depot.x, depot.y).buffer(depot_radius))
    ]
)

# Prepare a GeoDataFrame for single-depot cells
single_depot_gdf = cell_gdf[cell_gdf['associated_depots'].apply(len) == 1].copy()
single_depot_gdf['depot_id'] = single_depot_gdf['associated_depots'].apply(lambda x: x[0])

# Prepare a GeoDataFrame for multi-depot cells
multi_depot_gdf = cell_gdf[cell_gdf['associated_depots'].apply(len) > 1].copy()
multi_depot_gdf['closest_depot'] = multi_depot_gdf.apply(
    lambda row: closest_depot(row['geometry'], row['associated_depots']),
    axis=1
)

# Generate a colormap for depots
num_depots = len(selected_depots)
colors = plt.cm.tab20(range(num_depots))  # Use tab20 colormap for up to 20 depots
depot_colors = {i: colors[i] for i in range(num_depots)}




# Plotting
fig, ax = plt.subplots(figsize=(12, 12))

# Plot single-depot cells
for depot_id, group in single_depot_gdf.groupby('depot_id'):
    group.plot(ax=ax, color=depot_colors[depot_id])

# Plot multi-depot cells, hatched but colored by the closest depot
for depot_id, group in multi_depot_gdf.groupby('closest_depot'):
    group.plot(ax=ax, color=depot_colors[depot_id], edgecolor='black', hatch='//')

# Plot depots
for i, depot in enumerate(selected_depots):
    circle = plt.Circle((depot.x, depot.y), depot_radius, color=depot_colors[i], fill=False, linestyle='--', label='Depot Coverage')
    ax.add_patch(circle)
    plt.scatter(depot.x, depot.y, color=depot_colors[i], edgecolor='black', marker='o', s=100, label=f'Depot {i}')

# Plot work region
gpd.GeoDataFrame({'geometry': [simplified_polygon]}).boundary.plot(ax=ax, color='black', linestyle='--', label='Work Region')

plt.title("Cells Color-Coded by Associated Depot(s)")
plt.xlabel("X Coordinate")
plt.ylabel("Y Coordinate")
plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1))
plt.grid(True)
plt.show()

# Count cells associated with each depot
for idx, depot in enumerate(selected_depots):
    only_count = single_depot_gdf.groupby('depot_id').size().get(idx, 0)
    closest_count = multi_depot_gdf.groupby('closest_depot').size().get(idx, 0)
    print(f"Depot {idx}: {only_count} (+{closest_count}) cells")

# -

# Group cells associated with each depot
grouped_regions = []
for idx, depot in enumerate(selected_depots):
    only_cells = single_depot_gdf[single_depot_gdf['depot_id'] == idx]['geometry'].tolist()
    closest_cells = multi_depot_gdf[multi_depot_gdf['closest_depot'] == idx]['geometry'].tolist()
    grouped_regions.append(only_cells + closest_cells)
    # print(f"Depot {idx}: {grouped_regions}) cells")

# #### Determine Region of Valid Depot Locations
#
# - This is an interesting, challenging problem
# - Looks like we need to find the Minkowski difference of the range and circumscribed region.  
#
# **Attempt 1**: Find the minimum enclosing circle. Expand from centroid to include space in the difference between range and minimum enclosing circle.

# +
from shapely.geometry import MultiPoint, Point
from scipy.spatial import ConvexHull
import numpy as np
import matplotlib.pyplot as plt

def minimum_enclosing_circle(polygon):
    """
    Compute the minimum enclosing circle for a given polygon.

    Parameters:
        polygon (Polygon): A Shapely Polygon object.

    Returns:
        tuple: (center_x, center_y, radius) of the minimum enclosing circle.
    """
    def dist(p1, p2):
        """Compute the Euclidean distance between two points."""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def circle_from_three_points(p1, p2, p3):
        """Compute the circle defined by three points."""
        ax, ay = p1
        bx, by = p2
        cx, cy = p3
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
        uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
        center = (ux, uy)
        radius = dist(center, p1)
        return center, radius

    def welzl(points, boundary):
        """Recursive function for Welzl's algorithm."""
        if len(points) == 0 or len(boundary) == 3:
            if len(boundary) == 0:
                return (0, 0), 0
            elif len(boundary) == 1:
                return boundary[0], 0
            elif len(boundary) == 2:
                center = ((boundary[0][0] + boundary[1][0]) / 2, (boundary[0][1] + boundary[1][1]) / 2)
                radius = dist(boundary[0], boundary[1]) / 2
                return center, radius
            elif len(boundary) == 3:
                return circle_from_three_points(*boundary)

        point = points[-1]
        center, radius = welzl(points[:-1], boundary)

        if dist(center, point) <= radius:
            return center, radius

        return welzl(points[:-1], boundary + [point])

    # Extract the points from the polygon's exterior
    points = list(polygon.exterior.coords)

    # Compute the convex hull of the points
    hull = ConvexHull(points)
    hull_points = [points[vertex] for vertex in hull.vertices]

    # Run Welzl's algorithm on the convex hull points
    center, radius = welzl(hull_points, [])
    return center, radius



# +
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union
from scipy.spatial import ConvexHull
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def combine_cells_to_convex_hull(cells):
    """
    Combine a list of cells (polygons) into a single convex hull.

    Parameters:
        cells (list of Polygon): List of Shapely Polygon objects.

    Returns:
        Polygon: A single convex hull encompassing all input cells.
    """
    unioned = unary_union(cells)
    # if isinstance(unioned, MultiPolygon):
    #     points = [point for polygon in unioned for point in polygon.exterior.coords]
    # else:
    #     points = list(unioned.exterior.coords)
    # hull = ConvexHull(points)
    # hull_points = [points[vertex] for vertex in hull.vertices]
    return Polygon(unioned)

def visualize_regions_and_circles(regions, depot_radius):
    """
    Visualize the convex hull and minimum enclosing circle for each region.

    Parameters:
        regions (list of list of Polygon): List of groups of cells (each group is a list of polygons).
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    for i, cells in enumerate(regions):
        # Combine cells into a convex hull
        hull = combine_cells_to_convex_hull(cells)

        # Compute minimum enclosing circle
        center, radius = minimum_enclosing_circle(hull)

        # Plot the convex hull
        x, y = hull.exterior.xy
        ax.fill(x, y, alpha=0.5, label=f'Region {i+1} Convex Hull')

        # Plot the minimum enclosing circle
        circle = plt.Circle(center, radius, color='red', fill=False, linestyle='--', alpha=0.3, label=f'Region {i+1} Min. Enclosing Circle')
        ax.add_patch(circle)

        radius_circle = plt.Circle(center, depot_radius, color='green', fill=False, linestyle='--', alpha=0.3, label=f'Region Depot Radius')
        ax.add_patch(radius_circle)

        viable_circle = plt.Circle(center, depot_radius-radius, color='green', alpha=0.3, label=f'Region Depot Radius')
        ax.add_patch(viable_circle)

        # Plot the circle center
        ax.scatter(*center, color='red')

    ax.set_aspect('equal', adjustable='datalim')
    # plt.legend()
    plt.title("Convex Hulls and Minimum Enclosing Circles for Regions")
    plt.xlabel("X-axis")
    plt.ylabel("Y-axis")
    plt.grid(True)
    plt.show()


visualize_regions_and_circles(grouped_regions, depot_radius)


# +
from shapely.geometry import Polygon, Point
from shapely.affinity import translate
import matplotlib.pyplot as plt

def visualize_valid_translations(polygon, circle_radius):
    """
    Visualize the valid translations of a convex polygon such that it is fully circumscribed by a circle.

    Parameters:
        polygon_coords (list of tuples): Coordinates of the convex polygon vertices.
        circle_radius (float): Radius of the large circle.
    """

    # Define the large circle (centered at origin, radius circle_radius)
    circle_center = Point(polygon.centroid.x, polygon.centroid.y)
    circle = circle_center.buffer(circle_radius)

    # Buffer the polygon to compute the Minkowski difference (polygon + circle_radius)
    buffered_polygon = polygon.buffer(
        circle_radius, 
        cap_style="flat", 
        join_style="mitre",
        mitre_limit=1.0,
        single_sided=True
    )

    # Visualization
    fig, ax = plt.subplots(figsize=(8, 8))

    # Plot the original circle
    circle_patch = plt.Circle((circle_center.x, circle_center.y), circle_radius, color='blue', alpha=0.3, label='Circle (C)')
    ax.add_patch(circle_patch)

    # Plot the original polygon
    x, y = polygon.exterior.xy
    ax.fill(x, y, color='green', alpha=0.5, label='Original Polygon (P)')

    # Plot the buffered polygon
    x_buf, y_buf = buffered_polygon.exterior.xy
    ax.fill(x_buf, y_buf, color='red', alpha=0.3, label='Buffered Polygon (P + r)')

    # Set limits and aspect ratio
    # ax.set_xlim(-10, 10)
    # ax.set_ylim(-10, 10)
    ax.set_aspect('equal', adjustable='datalim')

    # Add legend and labels
    plt.legend()
    plt.title("Valid Translations of Polygon within Circle")
    plt.xlabel("X-axis")
    plt.ylabel("Y-axis")
    plt.grid(True)
    plt.show()

# Example usage
polygon_coords = [(2, 2), (5, 1), (4, 4)]  # Define a convex polygon (triangle)
circle_radius = 500  # Radius of the large circle
visualize_valid_translations(simplified_polygon, circle_radius)

# -

# ## Micro Planning
#
# Perform image analysis on each smaller section of our greater region.
