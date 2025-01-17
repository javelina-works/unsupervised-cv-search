---
jupyter:
  jupytext:
    notebook_metadata_filter: all
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.16.4
  kernelspec:
    display_name: venv
    language: python
    name: python3
  language_info:
    codemirror_mode:
      name: ipython
      version: 3
    file_extension: .py
    mimetype: text/x-python
    name: python
    nbconvert_exporter: python
    pygments_lexer: ipython3
    version: 3.11.5
---

# Target Auditing

We want to verify that the targets identified by our CV algorithm are correct and comprehensive.

```python
import sys
import geopandas as gpd
from pathlib import Path
sys.path.append(str(Path.cwd().parent))
```

```python
region_crs = 32613 # Use this everywhere for consistency
visualization_crs = 4326 # Use this when we need leaflet visualizations

region_contour_geojson = '../input/interactive_proto/region_contour.geojson'
micro_routes_filename = '../input/interactive_proto/micro_routes.geojson'
targets_plants_filename = '../input/interactive_proto/targets.geojson'
depots_filename = '../input/interactive_proto/depot_points.geojson'

```

```python
from ipyleaflet import (
    Map, GeoJSON, LayersControl, ScaleControl, 
    FullScreenControl, GeomanDrawControl,
    TileLayer, LocalTileLayer, GeoData,
)
from ipyleaflet.projections import projections
from ipywidgets import Layout

from shapely.geometry import shape
from shapely.wkt import loads
import json
import geopandas as gpd

from ipyleaflet.projections import projections

def plot_route_on_image(region_geojson, depots_filename, micro_routes_filename, targets_plants_filename):

    # Get image data
    # image, transform, bounds, image_crs = load_image(orthophoto_path)

    with open(region_geojson, "r") as f:
        region_contour_data = json.load(f)
    region_geometry = shape(region_contour_data['features'][0]['geometry'])
    region_center = region_geometry.centroid

    with open(depots_filename, "r") as f:
        depot_data = json.load(f)

    with open(micro_routes_filename, "r") as f:
        micro_routes_data = json.load(f)

    with open(targets_plants_filename, "r") as f:
        targets_data = json.load(f)
    
    
    
    bboxes_gdf = gpd.read_file(targets_plants_filename) # Read in from file
    bboxes_gdf['bounding_box'] = bboxes_gdf['bounding_box'].apply(loads) # str to Polygon
    bboxes_gdf.set_geometry('bounding_box', inplace=True) # It is the primary geometry
    bboxes_gdf = bboxes_gdf.drop(columns=['region_outline_version', 'geometry']) # remove confusing cols
    bboxes_gdf = bboxes_gdf.set_crs(region_crs).to_crs(visualization_crs) # Needs CRS, then convert

    
    # bounding_boxes_gdf = gpd.GeoDataFrame(bboxes_gdf, geometry='geometry', crs=bboxes_gdf.crs)
    # bounding_boxes_geojson = bounding_boxes_gdf.to_json()

    # Set up the map
    m = Map(center=(region_center.y, region_center.x),
            zoom=16, scroll_wheel_zoom=True,
            layout=Layout(height="700px"),  # Set desired dimensions
            # crs=projections.EPSG4326
        )

    # Add orthophoto overlay
    tile_layer = TileLayer(
        url="http://localhost:8000/{z}/{x}/{y}.png",
        min_zoom=15,
        max_zoom=22,
        show_loading=True,
        max_requests_per_tile=5,  # Adjust as needed
        name="Region Image")
    m.add_layer(tile_layer)

    # Add the region border to the map
    region_layer = GeoJSON(
        data=region_contour_data, 
        style={'color': 'blue', 'fillOpacity': 0.05, 'weight': 2},
        name=region_contour_data['name'])
    m.add(region_layer)

    depot_points = GeoJSON(
        data=depot_data,
        style={'color': 'black', 'radius':10, 'fillColor': '#3366cc', 'opacity':0.5, 'weight':1.9, 'dashArray':'2', 'fillOpacity':0.6},
        hover_style={'fillColor': 'red' , 'fillOpacity': 0.2},
        point_style={'radius': 3, 'color': 'red', 'fillOpacity': 0.8, 'fillColor': 'blue', 'weight': 3},
        name=depot_data['name']
    )
    m.add(depot_points)

    routes_layer = GeoJSON(
        data=micro_routes_data, 
        style={'color': 'green', 'fillColor': 'green', 'opacity': 0.75, 'weight': 4},
        hover_style={'color': 'red' , 'opacity': 0.8, 'weight': 3},
        name=f'Micro Routes'
    )
    m.add(routes_layer)

    targets_layer = GeoJSON(
        data=targets_data,
        style={'color': 'black', 'radius':3, 'fillColor': 'red', 'opacity':0.5, 'weight':1, 'fillOpacity':0.6},
        hover_style={'fillColor': 'red' , 'fillOpacity': 0.2},
        point_style={'radius': 3, 'color': 'red', 'fillOpacity': 0.8, 'fillColor': 'blue', 'weight': 3},
        name=targets_data['name']
    )
    # m.add(targets_layer)

    bboxes_layer = GeoData(geo_dataframe = bboxes_gdf,
                   style={'color': 'red', 'opacity':0.5, 'weight':1.9,
                          'fill': False, 'fillColor': 'red', 'fillOpacity': 0.2
                          },
                   hover_style={'color': 'red' , 'opacity': 1.0, 'fill': False},
                   name = 'Countries')
    m.add(bboxes_layer)

    draw_control = GeomanDrawControl()
    draw_control.circlemarker = {}
    draw_control.rotate = False
    draw_control.cut = False
    draw_control.drag = False
    m.add(draw_control)

    # m.add(FullScreenControl(position='topleft'))
    m.add(LayersControl(position='topright'))
    m.add(ScaleControl(position='bottomleft'))
    return m

m = plot_route_on_image(region_contour_geojson, depots_filename, micro_routes_filename, targets_plants_filename)
m
```
