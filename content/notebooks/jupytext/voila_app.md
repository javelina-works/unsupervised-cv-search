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

# Voila App: Target Audit

A multi-stage mini-app for auditing the targets within our region orthophoto.

- Upload region image
- Select samples of region
- Set parameters for CV search
    - Visualize parameters
- Run parameters on full orthophoto
    - View output
- Generate binary mask
- Audit detected targets on map
- Save targets to local geoJSON



```python
import sys
import geopandas as gpd
from pathlib import Path
sys.path.append(str(Path.cwd().parent))
```

```python
region_crs = 32613 # Use this everywhere for consistency
visualization_crs = 4326 # Use this when we need leaflet visualizations

# region_image_path = '../input/IGNORE_Brewster-2024-all-orthophoto-UTM-32613.tif'
region_image_path = '../tile_server/input/IGNORE_reprojected_region.tif'

region_contour_geojson = '../input/interactive_proto/region_contour.geojson'
micro_routes_filename = '../input/interactive_proto/micro_routes.geojson'
targets_plants_filename = '../input/interactive_proto/targets.geojson'
depots_filename = '../input/interactive_proto/depot_points.geojson'

```

## 1. Sample Images

Take random and manual samples of region orthophoto. We want variety, to ensure that our search parameters are effective across varying environmental conditions. 

```python
import param
import json
from shapely.geometry import shape
import panel as pn
from plant_search.verify_targets import get_image_sample_coordinates


class RegionSampler(param.Parameterized):
    region_image_path = param.String(doc="Path to the orthophoto image")
    region_geojson_path = param.String(doc="Path to the GeoJSON file defining the region")

    sample_size = param.Integer(1024, bounds=(512, 4096), step=256, doc="Size of individual samples")
    num_samples = param.Integer(5, bounds=(1, 12), doc="Number of random samples")
    save_samples = param.Action(lambda self: self._save_samples(), label="Save Samples")
    
    def __init__(self, **params):
        super().__init__(**params)
        self.sample_boxes_gdf = None
        self.get_samples()

    def __call__(self):
        return self.sample_boxes_gdf

    def get_samples(self):
        self.sample_boxes_gdf = get_image_sample_coordinates(
            self.region_image_path, self.sample_size, self.num_samples, self.region_geojson_path
        )
        return self.sample_boxes_gdf
        # return get_image_sample_coordinates(
        #     self.region_image_path, self.sample_size, self.num_samples, self.region_geojson_path
        # )

    # @param.depends('sample_size', 'num_samples', watch=True)
    # def update_samples(self):
    #     self.sample_boxes_gdf = get_image_sample_coordinates(
    #         self.region_image_path, self.sample_size, self.num_samples, self.region_geojson_path
    #     )

# Instantiate and serve the app
sampler = RegionSampler(
    region_image_path = region_image_path,
    region_geojson_path = region_contour_geojson
)

# pn.extension()
# pn.Column(sampler.param, sampler.get_samples)
# sampler.panel()
sampler.param
```

```python
sampler.sample_boxes_gdf
```

```python
from ipyleaflet import Map, GeoJSON, TileLayer, GeoData, WidgetControl, LayersControl, ScaleControl, GeomanDrawControl


class MapView(param.Parameterized):
    # region_image_path = param.String(doc="Path to the orthophoto image")
    region_geojson_path = param.String(doc="Path to the GeoJSON file defining the region")
    
    def __init__(self, **params):
        super().__init__(**params)
        self.map = None
        self.sample_boxes_gdf = None
        self.combined_gdf = None
        self.region_data = None
        self._initialize_region_data()
        self._initialize_map()

    def _initialize_region_data(self):
        with open(self.region_geojson_path, "r") as f:
            self.region_data = json.load(f)
        region_geometry = shape(self.region_data['features'][0]['geometry'])
        self.region_center = region_geometry.centroid

    def _initialize_map(self):
        self.map = Map(center=(self.region_center.y, self.region_center.x), zoom=16, scroll_wheel_zoom=True)
        region_layer = GeoJSON(data=self.region_data, style={'color': 'blue', 'fill': False, 'weight': 2})
        self.map.add(region_layer)
        self.tile_layer = TileLayer(
            url="http://localhost:8000/{z}/{x}/{y}.png",
            min_zoom=15, max_zoom=22,
            name="Region Image"
        )
        self.map.add(self.tile_layer)
        self._add_draw_control()
        self._add_scale_and_layer_controls()

    def _add_draw_control(self):
        self.draw_control = GeomanDrawControl()
        self.draw_control.rectangle = {"pathOptions": {"weight": 2, "color": "green", "fillOpacity": 0.1}}
        self.map.add(self.draw_control)

    def _add_scale_and_layer_controls(self):
        self.map.add(LayersControl(position="topright"))
        self.map.add(ScaleControl(position="bottomleft"))

# view_map = MapView(
#     region_geojson_path = region_contour_geojson
# )

# # pn.extension('ipywidgets')
# pn.Column(view_map.map)


```

```python
# type(view_map.map)
# view_map.map
```

```python
# import panel as pn
# import param
# from ipyleaflet import Map, GeoJSON, TileLayer, GeoData, WidgetControl, LayersControl, ScaleControl, GeomanDrawControl
# from shapely.geometry import shape
# import geopandas as gpd
# import json
# from plant_search.verify_targets import get_image_sample_coordinates

# class RegionSampler(param.Parameterized):
#     region_image_path = param.String(doc="Path to the orthophoto image")
#     region_geojson_path = param.String(doc="Path to the GeoJSON file defining the region")
#     sample_size = param.Integer(2048, bounds=(512, 4096), doc="Size of individual samples")
#     num_samples = param.Integer(5, bounds=(1, 20), doc="Number of random samples")
#     save_samples = param.Action(lambda self: self._save_samples(), label="Save Samples")
    
#     def __init__(self, **params):
#         super().__init__(**params)
#         self.map = None
#         self.sample_boxes_gdf = None
#         self.combined_gdf = None
#         self.region_data = None
#         self._initialize_region_data()
#         self._initialize_map()

#     def _initialize_region_data(self):
#         with open(self.region_geojson_path, "r") as f:
#             self.region_data = json.load(f)
#         region_geometry = shape(self.region_data['features'][0]['geometry'])
#         self.region_center = region_geometry.centroid

#     def _initialize_map(self):
#         self.map = Map(center=(self.region_center.y, self.region_center.x), zoom=16, scroll_wheel_zoom=True)
#         region_layer = GeoJSON(data=self.region_data, style={'color': 'blue', 'fill': False, 'weight': 2})
#         self.map.add(region_layer)
#         self.tile_layer = TileLayer(
#             url="http://localhost:8000/{z}/{x}/{y}.png",
#             min_zoom=15, max_zoom=22,
#             name="Region Image"
#         )
#         self.map.add(self.tile_layer)
#         self._add_draw_control()
#         self._add_scale_and_layer_controls()

#     def _add_draw_control(self):
#         self.draw_control = GeomanDrawControl()
#         self.draw_control.rectangle = {"pathOptions": {"weight": 2, "color": "green", "fillOpacity": 0.1}}
#         self.map.add(self.draw_control)

#     def _add_scale_and_layer_controls(self):
#         self.map.add(LayersControl(position="topright"))
#         self.map.add(ScaleControl(position="bottomleft"))

#     @param.depends('sample_size', 'num_samples', watch=True)
#     def update_samples(self):
#         self.sample_boxes_gdf = get_image_sample_coordinates(
#             self.region_image_path, self.sample_size, self.num_samples, self.region_geojson_path
#         )
#         samples_layer = GeoData(
#             geo_dataframe=self.sample_boxes_gdf,
#             style={'color': 'blue', 'weight': 2},
#             name="Random Samples"
#         )
#         self.map.add(samples_layer)

#     def _save_samples(self):
#         # Save the combined GeoDataFrame
#         if self.combined_gdf is not None:
#             self.combined_gdf.to_file("combined_features.geojson", driver="GeoJSON")
#             print("Samples saved to combined_features.geojson.")

#     def panel(self):
#         controls = pn.Param(
#             self.param,
#             widgets={
#                 'sample_size': pn.widgets.IntSlider,
#                 'num_samples': pn.widgets.IntSlider,
#                 'save_samples': pn.widgets.Button,
#             },
#             show_name=False
#         )
#         return pn.Column(controls, pn.pane.IPyWidget(self.map))

# # Instantiate and serve the app
# sampler = RegionSampler(
#     region_image_path="path/to/image.tif",
#     region_geojson_path="path/to/region.geojson"
# )
# sampler.update_samples()
# pn.extension()
# sampler.panel().servable()

```

```python
# import geopandas as gpd
# from shapely.geometry import box

# class SampleGenerator:
#     def __init__(self, image_path, geojson_path):
#         self.image_path = image_path
#         self.geojson_path = geojson_path

#     def generate_samples(self, sample_size, num_samples):
#         # Example logic to generate sample boxes
#         # Replace with your actual sampling logic
#         samples = []
#         for i in range(num_samples):
#             samples.append(box(i * sample_size, 0, (i + 1) * sample_size, sample_size))
#         return gpd.GeoDataFrame(geometry=samples, crs="EPSG:4326")

```

```python
# from ipyleaflet import Map, GeoData

# class MapView:
#     def __init__(self, center, zoom):
#         self.map = Map(center=center, zoom=zoom)

#     def add_samples_layer(self, geo_dataframe):
#         samples_layer = GeoData(
#             geo_dataframe=geo_dataframe,
#             style={'color': 'blue', 'weight': 2},
#             name="Samples"
#         )
#         self.map.add(samples_layer)

#     def get_map(self):
#         return self.map

```
