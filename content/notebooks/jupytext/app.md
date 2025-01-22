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

# Panel App: Target Audit

A multi-stage application for auditing the targets within our region orthophoto.

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
# import param
# import panel as pn
# import geopandas as gpd
# import matplotlib.pyplot as plt
# from io import BytesIO
# import json
# from PIL import Image

# pn.extension('filedropper')


# class TargetAuditApp(param.Parameterized):
#     # Parameters for tracking uploaded files
#     region_image_upload = param.Parameter(default=None)
#     region_geojson_upload = param.Parameter(default=None)

#     # FileDropper widgets

#     # Accepted filetypes bug for this widget: https://github.com/holoviz/panel/issues/7153
#     # accepted_filetypes=["allowed/geojson", ".geojson"],
#     # Unable to handle our large geoTiff images
#     image_dropper = pn.widgets.FileDropper(height=100, max_file_size ="500MB", chunk_size=30000000)
#     geojson_dropper = pn.widgets.FileDropper(height=100, max_file_size ="100MB")

#     def __init__(self, **params):
#         super().__init__(**params)

#         # Link FileDropper outputs to parameters
#         self.image_dropper.param.watch(self._update_region_image, "value")
#         self.geojson_dropper.param.watch(self._update_region_geojson, "value")

#     # Update methods for parameters
#     def _update_region_image(self, event):
#         if event.new:
#             self.region_image_upload = event.new

#     def _update_region_geojson(self, event):
#         if event.new:
#             # first_file_name = list(event.new.keys())[0] # Dict of file names:bytes
#             # file_bytes_string = event.new[first_file_name].decode("utf-8") # Bytes to string
#             # self.region_geojson = json.loads(file_bytes_string)  # String to JSON dict
#             self.region_geojson_upload = event.new

#     def get_region_image(self):
#         image_upload_dict = self.region_image_upload # Stays as dict of files
#         first_file_name = list(image_upload_dict.keys())[0] # Dict of file names:bytes
#         image_stream  = BytesIO(image_upload_dict[first_file_name]) # Bytes to Stream
#         region_image = Image.open(image_stream)  # Stream to PIL image
#         return region_image

#     def get_region_geojson(self):
#         geojson_upload_dict = self.region_geojson_upload # Dict of files
#         first_file_name = list(geojson_upload_dict.keys())[0] # Dict of file names:bytes
#         file_bytes_string = geojson_upload_dict[first_file_name].decode("utf-8") # Bytes to string
#         region_geojson = json.loads(file_bytes_string)  # String to JSON dict
#         return region_geojson

#     # A method to display the uploaded region image
#     def view_image(self):
#         if self.region_image_upload:
#             try:
#                 image_data = self.get_region_image()
#                 fig, ax = plt.subplots(figsize=(4, 4))
#                 ax.imshow(image_data)
#                 ax.axis('off')
#                 return pn.pane.Matplotlib(fig)
#             except Exception as e:
#                 return f"Error displaying image: {e}"
#         else:
#             return "No image uploaded."

#     # A method to display the GeoJSON region outline
#     def view_geojson(self):
#         if self.region_geojson_upload:
#             try:
#                 region_geojson = self.get_region_geojson()
#                 return pn.pane.JSON(region_geojson, depth=2, name="Uploaded GeoJSON")
#             except Exception as e:
#                 return f"Error processing GeoJSON: {e}"
#         else:
#             return "No GeoJSON uploaded."

#     # Panel layout combining file droppers and visualizations
#     def panel(self):
#         return pn.Column(
#             pn.Row(
#                 pn.Column("**Drop Region Image Here**", self.image_dropper),
#                 pn.Column("**Drop GeoJSON Here**", self.geojson_dropper),
#             ),
#             pn.Row(
#                 pn.Column("**Uploaded Region Image**", self.view_image),
#                 pn.Column("**Uploaded GeoJSON Outline**", self.view_geojson),
#             ),
#         )


# # Run the app
# target_audit_app = TargetAuditApp()
# target_audit_app.panel().servable()

# target_audit_app.panel()
```

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

```python
import ipywidgets as widgets
from IPython.display import display

slider = widgets.IntSlider(value=10, min=0, max=100, step=1, description="Slider:")
display(slider)

```

```python
import panel as pn
import ipywidgets as widgets

pn.extension('ipywidgets')

slider = widgets.IntSlider(value=10, min=0, max=100, step=1, description="Slider:")
# pn.pane.IPyWidget(slider).show()
pn.pane.IPyWidget(slider)

```

```python
from ipyleaflet import Map, VideoOverlay
import panel as pn
import ipywidgets as ipw

pn.extension('ipywidgets')
# pn.extension()

# m = Map(center=(25, -115), zoom=4)

# video = VideoOverlay(
#     url="https://www.mapbox.com/bites/00188/patricia_nasa.webm",
#     bounds=((13, -130), (32, -100))
# )

# m.add(video);
# pn.panel(m)
```

```python
date   = ipw.DatePicker(description='Date')
slider = ipw.FloatSlider(description='Float')
play   = ipw.Play()

layout = ipw.HBox(children=[date, slider, play])
# layout = pn.Column(
#     pn.pane.Markdown("# IPyWidgets Example"),
#     pn.pane.IPyWidget(slider),
#     pn.pane.IPyWidget(play),
# )

# pn.panel(layout).show()
# layout.show()
pn.panel(layout)
```

```python
# from ipyleaflet import Map, GeoJSON, TileLayer, GeoData, WidgetControl, LayersControl, ScaleControl, GeomanDrawControl
# import param
# import json
# from shapely.geometry import shape
# import panel as pn

# class MapView(param.Parameterized):
#     # region_image_path = param.String(doc="Path to the orthophoto image")
#     region_geojson_path = param.String(doc="Path to the GeoJSON file defining the region")
    
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

#         # self.tile_layer = TileLayer(
#         #     url="http://localhost:8000/{z}/{x}/{y}.png",
#         #     min_zoom=15, max_zoom=22,
#         #     name="Region Image"
#         # )
#         # self.map.add(self.tile_layer)

#         self._add_region_outline_layer()
#         self._add_draw_control()
#         self._add_scale_and_layer_controls()

#     def _add_region_outline_layer(self):
#         # Add the region border to the map
#         region_layer = GeoJSON(
#             data=self.region_data, 
#             style={'color': 'blue', 'fillOpacity': 0.05, 'weight': 2},
#             name=self.region_data['name'])
#         self.map.add(region_layer)


#     def _add_draw_control(self):
#         self.draw_control = GeomanDrawControl()
#         self.draw_control.rectangle = {"pathOptions": {"weight": 2, "color": "green", "fillOpacity": 0.1}}
#         self.map.add(self.draw_control)

#     def _add_scale_and_layer_controls(self):
#         self.map.add(LayersControl(position="topright"))
#         self.map.add(ScaleControl(position="bottomleft"))

# map_view = MapView(
#     region_geojson_path = region_contour_geojson
# )

# pn.extension()
# # pn.Column(map_view.map)
# pn.panel(map_view.map)

```

<!-- #raw vscode={"languageId": "raw"} -->
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

pn.extension()
pn.Column(sampler.param, sampler.get_samples)
<!-- #endraw -->

<!-- #raw vscode={"languageId": "raw"} -->
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

def plot_targets_on_map(region_geojson, targets_gdf):

    # Get image data
    # image, transform, bounds, image_crs = load_image(orthophoto_path)

    with open(region_geojson, "r") as f:
        region_contour_data = json.load(f)
    region_geometry = shape(region_contour_data['features'][0]['geometry'])
    region_center = region_geometry.centroid

    # Set up the map
    m = Map(center=(region_center.y, region_center.x),
            zoom=16, scroll_wheel_zoom=True,
            double_click_zoom=False,
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


    targets_points_gdf = targets_gdf.copy()
    targets_points_gdf = targets_points_gdf.drop(columns=['bounding_box']) # remove confusing cols

    targets_layer = GeoData(geo_dataframe = targets_points_gdf,
                            style={'color': 'black', 'radius':6, 'fillColor': 'red', 'opacity':0.5, 'weight':1, 'fillOpacity':0.3},
                            hover_style={'fillColor': 'red' , 'fillOpacity': 0.2},
                            point_style={'radius': 3, 'color': 'red', 'fillOpacity': 0.8, 'fillColor': 'blue', 'weight': 3},
                            draggable=True,
                            name="Identified targets"
                            )
    m.add(targets_layer)


    bboxes_gdf = targets_gdf.copy()
    # bboxes_gdf['bounding_box'] = bboxes_gdf['bounding_box'].apply(loads) # str to Polygon
    bboxes_gdf.set_geometry('bounding_box', inplace=True) # It is the primary geometry
    bboxes_gdf = bboxes_gdf.drop(columns=['geometry']) # remove confusing cols
    # bboxes_gdf = bboxes_gdf.set_crs(region_crs).to_crs(visualization_crs) # Needs CRS, then convert

    bboxes_layer = GeoData(geo_dataframe = bboxes_gdf,
                   style={'color': 'red', 'opacity':0.5, 'weight':1.9,
                          'fill': False, 'fillColor': 'red', 'fillOpacity': 0.2 },
                   hover_style={'color': 'red' , 'opacity': 1.0, 'fill': False},
                   name = 'Target bounding boxes')
    m.add(bboxes_layer)


    draw_control = GeomanDrawControl()
    draw_control.circlemarker = {}
    draw_control.rotate = False
    # draw_control.cut = False
    draw_control.drag = False
    m.add(draw_control)

    # m.add(FullScreenControl(position='topleft'))
    m.add(LayersControl(position='topright'))
    m.add(ScaleControl(position='bottomleft'))
    return m

m = plot_targets_on_map(region_contour_geojson, targets_gdf)
m
<!-- #endraw -->
