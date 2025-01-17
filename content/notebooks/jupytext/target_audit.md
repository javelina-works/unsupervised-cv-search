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
region_contour_geojson = '../input/interactive_proto/region_contour.geojson'
micro_routes_filename = '../input/interactive_proto/micro_routes.geojson'
```

```python
from ipyleaflet import (
    Map, GeoJSON, LayersControl, ScaleControl, ImageOverlay, TileLayer
)
from plant_search.load_image import load_image
from shapely.geometry import shape
import json

from ipyleaflet.projections import projections

def plot_route_on_image(region_geojson, micro_routes_filename):

    # Get image data
    # image, transform, bounds, image_crs = load_image(orthophoto_path)

    with open(region_geojson, "r") as f:
        region_contour_data = json.load(f)
    region_geometry = shape(region_contour_data['features'][0]['geometry'])
    region_center = region_geometry.centroid

    with open(micro_routes_filename, "r") as f:
        micro_routes_data = json.load(f)


    
    # Set up the map
    m = Map(center=(region_center.y, region_center.x),
            zoom=16, scroll_wheel_zoom=True)

    # Add orthophoto overlay
    tile_layer = TileLayer(
        url="http://localhost:8000/{z}/{x}/{y}.png",
        # min_zoom=15,
        # max_zoom=20,
        name="Region Image")
    m.add_layer(tile_layer)

    # Add the region border to the map
    region_layer = GeoJSON(
        data=region_contour_data, 
        style={'color': 'blue', 'fillOpacity': 0.05, 'weight': 2},
        name=region_contour_data['name'])
    m.add(region_layer)

    routes_layer = GeoJSON(
        data=micro_routes_data, 
        style={'color': 'green', 'fillColor': 'green', 'opacity': 0.25, 'weight': 1},
        hover_style={'color': 'red' , 'opacity': 0.8, 'weight': 3},
        name=f'Micro Routes'
    )
    # m.add(routes_layer)

    m.add(LayersControl(position='topright'))
    m.add(ScaleControl(position='bottomleft'))
    return m

m = plot_route_on_image(region_contour_geojson, micro_routes_filename)
m
```
