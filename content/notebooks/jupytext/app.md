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
import param
import panel as pn

pn.extension()
pipeline = pn.pipeline.Pipeline()
```

```python
import geopandas as gpd
import sys
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
binary_mask_filename = '../input/interactive_proto/binary_mask.png'
targets_plants_filename = '../input/interactive_proto/targets.geojson'
depots_filename = '../input/interactive_proto/depot_points.geojson'

```

## Upload Input Files

```python
# from panel_app.upload_stage import StageUpload

# # Run first stage manually
# pn.extension()

# stage1 = StageUpload()
# # stage1.panel() # In notebook
# stage1.panel().show() # In browser
# # stage1.param.outputs()
```

## Perform CV Search
- Set parameters for CV seach
- Perform on uploaded image

```python
# from panel_app.search_stage import StageSearch
# from PIL import Image

# # Run stage manually
# pn.extension()

# image_path = region_image_path
# image = Image.open(image_path) # Pass as PIL image

# stage2 = StageSearch(
#     input_image = image
# )
# # stage2.panel() # In notebook
# stage2.panel().show() # In browser
# # stage2.param.outputs()
```

```python
# from bokeh.plotting import figure, show
# from bokeh.models import LinearColorMapper, ColorBar
# from bokeh.io import output_notebook
# from bokeh.layouts import column
# import numpy as np

# def bokeh_colormap(grayscale_image):

#     grayscale_normalized = grayscale_image / 255.0
#     color_mapper = LinearColorMapper(palette="Greens256", low=1, high=0)

#     # Create a Bokeh figure
#     p = figure(
#         title="Grayscale Image with Colormap",
#         x_range=(0, grayscale_image.shape[1]),
#         y_range=(0, grayscale_image.shape[0]),
#         # width=500,
#         max_height=400,
#         # max_width=1200,
#         # width_policy="fit",
#         # height=500,
#         aspect_ratio="auto",
#         # sizing_mode="scale_both",
#         tools="pan, wheel_zoom, reset",
#     )

#     # Plot the image
#     p.image(
#         image=[grayscale_normalized],
#         x=0, y=0, 
#         dw=grayscale_image.shape[1],
#         dh=grayscale_image.shape[0],
#         # color_mapper=color_mapper,
#     )

#     # Show the plot
#     output_notebook()  # Display in a notebook environment
#     show(p)  # Render the Bokeh plot

```

```python
# image_data = image_data[:, :, :3]
# print(image_data.shape)
# print(image_data.dtype)


# bokeh_colormap(image_data)

# # image_data = image_data[:, :, 1]

# # morphological = VegetationIndex()
# # smoothed = morphological.apply(image_data)
# # print(smoothed.shape)
# # print(smoothed.dtype)

# # smoothed = (smoothed * 255).astype(np.uint8)

# # bokeh_colormap(smoothed)
# # image = Image.fromarray(smoothed)

# # pn.pane.Image(image, height=300).show()
```

## Get Targets from Binary Mask

```python
import geopandas as gpd
import panel as pn
from io import BytesIO

class DownloadGeoJSON(param.Parameterized):
    # Parameter to hold the GeoDataFrame
    source_gdf = param.ClassSelector(class_=gpd.GeoDataFrame, default=None, allow_None=True)
    filename = param.String(default="output.geojson")
    button_type = param.String(default="primary")
    name = param.String(default="Download")

    def get_geojson_file(self):
        """
        Convert the current GeoDataFrame (source_gdf) to a GeoJSON string for download.
        """
        if self.source_gdf is None:
            print("No GeoDataFrame is set!")
            return BytesIO()  # Return an empty file
        bio = BytesIO()
        self.source_gdf.to_file(bio, driver="GeoJSON")
        bio.seek(0)
        return bio

    @param.depends("source_gdf", "filename", "button_type", "name")
    def download_widget(self):
        """
        Return a FileDownload widget based on the current state of the parameters.
        """
        return pn.widgets.FileDownload(
            callback=lambda: self.get_geojson_file(),
            filename=self.filename,
            button_type=self.button_type,
            name=self.name
        )
```

```python
import geopandas as gpd

from plant_search.image_preprocess import identify_targets
from plant_search.load_image import load_image


class AcquireTargetsWidget(param.Parameterized):
    binary_mask = param.Parameter(default=None, doc="2D np.array of binary mask")
    region_geotiff_path = param.Parameter(default=None, doc="Original orthophoto for georeference")
    targets_gdf = param.Parameter(default=None, doc="GDF of potential targets")

    def __init__(self, **params):
        super().__init__(**params)
        self.find_targets() # Auto-search on init


    @param.depends("binary_mask", "region_geotiff_path", watch=True)
    def find_targets(self):
        if not self.region_geotiff_path:
            return None
        if self.binary_mask is None:
            return None # Need binary mask to perform
        
        print("Generate GDF")
        image, transform, bounds, crs = load_image(self.region_geotiff_path)
        self.targets_gdf = identify_targets(self.binary_mask, transform)

    def _downscale_for_display(self, image, max_width=1000, max_height=1000):
        """Downscale an image for display purposes."""
        if len(image.shape) == 3 and image.shape[2] == 4:  # RGBA
            pil_image = Image.fromarray(image[:, :, :3])  # Strip alpha for display
        elif len(image.shape) == 3:  # RGB
            pil_image = Image.fromarray(image)
        else:  # Grayscale
            pil_image = Image.fromarray(image)

        pil_image.thumbnail((max_width, max_height))  # Resize while maintaining aspect ratio
        return pil_image


    def view_output_targets(self):
        output_panel = "Output here"
        return output_panel

    @param.depends("binary_mask", watch=False)
    def view_binary_mask(self):
        if self.binary_mask is not None:
            input_mask = self._downscale_for_display(self.binary_mask)
            return pn.Row(
                "Input binary mask",
                pn.pane.Image(input_mask, height=500, width=500)
            )
        else:
            return "No binary mask image uploaded!"

    def view(self):
        targeting_panel = pn.Column(
            pn.Row("#Find Targets from Mask"),
            self.view_binary_mask,
            
        )
        return targeting_panel



class StageAcquireTargets(param.Parameterized):
    binary_mask = param.Parameter(default=None, doc="2D np.array of binary mask")
    region_geotiff_path = param.String(default=None, doc="Path to OG geotiff")

    def __init__(self, **params):
        super().__init__(**params)
        self._add_aquire_targets_widgets()

        self.download_targets = DownloadGeoJSON(
            source_gdf=self.acquire_targets.targets_gdf,
            filename="targets.geojson",
            button_type="primary",
            name="Download Targets"
        )

    @param.output(binary_mask=param.Parameter())
    def output(self):
        return self.target_search.output_image
    
    def _add_aquire_targets_widgets(self):
        self.acquire_targets = AcquireTargetsWidget(
            binary_mask=self.binary_mask,
            region_geotiff_path=self.region_geotiff_path
        )

    def panel(self):
        return pn.Row(
            self.acquire_targets.view(),
            self.download_targets.download_widget)
```

```python
# from panel_app.search_stage import StageSearch
import numpy as np

# Run stage manually
pn.extension()

binary_mask_image = Image.open(binary_mask_filename)
binary_mask_array = np.array(binary_mask_image)

stage3 = StageAcquireTargets(
    binary_mask=binary_mask_array,
    region_geotiff_path=region_image_path,
)
# stage3.panel() # In notebook
stage3.panel().show() # In browser
# stage3.param.outputs()
```

## First Three Stages

```python
# from panel_app.upload_stage import StageUpload
# from panel_app.search_stage import StageSearch

# pipeline.add_stage('Upload', StageUpload)
# pipeline.add_stage('Search', StageSearch)
# pipeline.add_stage('Acquire Targets', StageAcquireTargets)
# pipeline.show()
```

## Audit Targets
- Manually deselect targets missed by the algorithm

```python
from ipyleaflet import (
    Map, GeoJSON, TileLayer, GeoData, 
    WidgetControl, LayersControl, ScaleControl, 
    GeomanDrawControl, FullScreenControl, ZoomControl
)
from panel.widgets import Button
import ipywidgets
import param
import panel as pn
import pandas as pd
import json
from shapely.geometry import shape

class MapView(param.Parameterized):
    # region_image_path = param.String(doc="Path to the orthophoto image")
    region_geojson_path = param.String(doc="Path to the GeoJSON file defining the region")
    targets_gdf = param.Parameter(default=None, doc="GeoPandas DF of potential targets")

    def __init__(self, **params):
        super().__init__(**params)
        self.map = None
        self.removed_targets_gdf = gpd.GeoDataFrame(columns=self.targets_gdf.columns, geometry='geometry')
        # self.sample_boxes_gdf = None
        # self.combined_gdf = None
        self.drawn_rectangles = []
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

        # self.tile_layer = TileLayer(
        #     url="http://localhost:8000/{z}/{x}/{y}.png",
        #     min_zoom=15, max_zoom=22,
        #     name="Region Image"
        # )
        # self.map.add(self.tile_layer)

        self._add_region_outline_layer()
        self._add_targets_layer()
        self._add_removed_targets_layer()
        self._add_map_controls()
        self._add_draw_control()
        self._add_mass_remove_button()

    def _add_region_outline_layer(self):
        region_layer = GeoJSON(
            data=self.region_data, 
            style={'color': 'blue', 'fillOpacity': 0.05, 'weight': 2},
            name=self.region_data['name'])
        self.map.add(region_layer) # Add the region border to the map

    def _add_targets_layer(self):
        self.targets_layer = GeoData(
            geo_dataframe=self.targets_gdf,
            style={'color': 'black', 'radius':6, 'fillColor': 'blue', 'opacity':0.5, 'weight':1, 'fillOpacity':0.3},
            hover_style={'fillColor': 'blue' , 'fillOpacity': 0.2},
            point_style={'radius': 3, 'color': 'red', 'fillOpacity': 0.8, 'fillColor': 'blue', 'weight': 3},
            draggable=True,
            name="Identified targets"
            )
        
        def on_click_target(event, feature, properties, id):
            # Move the clicked point to the removed targets layer
            target_id = properties['target_id']
            clicked_point = self.targets_gdf[self.targets_gdf['target_id'] == target_id]
            # Remove from targets_gdf
            self.targets_gdf = self.targets_gdf[self.targets_gdf['target_id'] != target_id]
            self.targets_layer.geo_dataframe = self.targets_gdf
            # Add to removed_targets_gdf
            self.removed_targets_gdf = pd.concat([self.removed_targets_gdf, clicked_point])
            self.removed_targets_layer.geo_dataframe = self.removed_targets_gdf

        self.targets_layer.on_click(on_click_target)
        self.map.add(self.targets_layer)

    def _add_removed_targets_layer(self):
        self.removed_targets_layer = GeoData(
            geo_dataframe=self.removed_targets_gdf,
            style={'color': 'black', 'radius':6, 'fillColor': 'red', 'opacity':0.5, 'weight':1, 'fillOpacity':0.3},
            hover_style={'fillColor': 'red' , 'fillOpacity': 0.2},
            point_style={'radius': 3, 'color': 'red', 'fillOpacity': 0.8, 'fillColor': 'blue', 'weight': 3},
            draggable=True,
            name="Removed targets"
            )
        
        def on_click_removed_target(event, feature, properties, id):
            target_id = properties['target_id']
            clicked_point = self.removed_targets_gdf[self.removed_targets_gdf['target_id'] == target_id]

            self.removed_targets_gdf = self.removed_targets_gdf[self.removed_targets_gdf['target_id'] != target_id]
            self.removed_targets_layer.geo_dataframe = self.removed_targets_gdf # Remove from removed_targets_gdf
            
            self.targets_gdf = pd.concat([self.targets_gdf, clicked_point]) # Add back to targets_gdf
            self.targets_layer.geo_dataframe = self.targets_gdf

        self.removed_targets_layer.on_click(on_click_removed_target)
        self.map.add(self.removed_targets_layer)

    def _add_draw_control(self):
        self.draw_control = GeomanDrawControl()
        
        self.draw_control.circlemarker = {}
        self.draw_control.polygon = {}
        self.draw_control.polyline = {}
        self.draw_control.rectangle = {"pathOptions": {"weight": 2, "color": "green", "fillOpacity": 0.1}}
        
        self.draw_control.rotate = False
        self.draw_control.cut = False
        self.draw_control.edit = False
        self.draw_control.drag = False # Does not maintain state 
        self.draw_control.remove = False # Swap GDFs, don't remove

        self.map.add(self.draw_control)

    def _add_map_controls(self):
        # self.map.add(ZoomControl(position='bottomleft'))
        self.map.add(FullScreenControl(position='topleft'))
        self.map.add(LayersControl(position="topright"))
        self.map.add(ScaleControl(position="bottomleft"))

    def _add_mass_remove_button(self):
        self.button = ipywidgets.Button(
            description="Process Rectangles", 
            tooltip="Remove all targets in selections",  # Tooltip text
            icon="rectangle-xmark"
        )

        def process_rectangles(event):
            if not self.draw_control.data or not isinstance(self.draw_control.data, list):
                print("no drawn")
                return # No drawn geometries
            drawn_geometries = [
                shape(item["geometry"])
                for item in self.draw_control.data # Extract valid geometries from draw control data
                if "geometry" in item
            ]
            if not drawn_geometries:
                print("no valid drawn")
                return # Exit early if no valid geometries are found
            
            all_selections = gpd.GeoSeries(drawn_geometries).union_all() # Combine selections
            points_in_selections = self.targets_gdf[self.targets_gdf.geometry.within(all_selections)]
            if points_in_selections.empty:
                return # No points found within the drawn rectangles

            self.removed_targets_gdf = pd.concat([self.removed_targets_gdf, points_in_selections])
            self.targets_gdf = self.targets_gdf[~self.targets_gdf.index.isin(points_in_selections.index)]

            self.targets_layer.geo_dataframe = self.targets_gdf # Update the layers
            self.removed_targets_layer.geo_dataframe = self.removed_targets_gdf
            self.draw_control.clear() # Clear the drawn rectangles
    
        self.button.on_click(process_rectangles)
        self.map.add(WidgetControl(widget=self.button, position='bottomright'))
```

```python
import geopandas as gpd
import panel as pn
from io import BytesIO

class DownloadGeoJSON(param.Parameterized):
    # Parameter to hold the GeoDataFrame
    source_gdf = param.ClassSelector(class_=gpd.GeoDataFrame, default=None, allow_None=True)
    filename = param.String(default="output.geojson")
    button_type = param.String(default="primary")
    name = param.String(default="Download")

    def get_geojson_file(self):
        """
        Convert the current GeoDataFrame (source_gdf) to a GeoJSON string for download.
        """
        if self.source_gdf is None:
            print("No GeoDataFrame is set!")
            return BytesIO()  # Return an empty file
        bio = BytesIO()
        self.source_gdf.to_file(bio, driver="GeoJSON")
        bio.seek(0)
        return bio

    @param.depends("source_gdf", "filename", "button_type", "name")
    def download_widget(self):
        """
        Return a FileDownload widget based on the current state of the parameters.
        """
        return pn.widgets.FileDownload(
            callback=lambda: self.get_geojson_file(),
            filename=self.filename,
            button_type=self.button_type,
            name=self.name
        )
```

```python
import param

class StageAudit(param.Parameterized):
    region_geojson_path = param.String(doc="Path to the GeoJSON file defining the region")
    targets_gdf = param.Parameter(default=None, doc="GeoPandas DF of potential targets")

    @param.output() # TBD best param type for geoJSON/GDFs
    def output(self):
        return self.map_view.targets_gdf, self.map_view.removed_targets_gdf

    def __init__(self, **params):
        super().__init__(**params)
        self._add_map()
        self._add_download_widgets()

    def _add_map(self):
        targets_points_gdf = self.targets_gdf[['geometry','target_id']] # remove confusing cols
        self.map_view = MapView(
            region_geojson_path = region_contour_geojson,
            targets_gdf = targets_points_gdf
        )

    def _add_download_widgets(self):
        download_targets = DownloadGeoJSON(
            source_gdf=self.map_view.targets_gdf,
            filename="targets.geojson",
            button_type="primary",
            name="Download Targets"
        )
        download_removed_targets = DownloadGeoJSON(
            source_gdf=self.map_view.removed_targets_gdf,
            filename="removed_targets.geojson",
            button_type="warning",
            name="Download Removed Targets"
        )
        self.download_widgets = pn.Column(
            "# Parameterized GeoJSON Downloads",
            pn.Row(
                download_targets.download_widget,
                download_removed_targets.download_widget,
                width=400
            )
        )
        
    def panel(self):
        map_panel = pn.panel(self.map_view.map)
        layout = pn.Column(
            map_panel,
            self.download_widgets
        )
        return layout
    
```

```python
import geopandas as gpd

pn.extension()

# Convert from file to correct stage input type (gdf)
targets_gdf = gpd.read_file(targets_plants_filename)

audit_stage = StageAudit(
    targets_gdf=targets_gdf,
    region_geojson_path=region_contour_geojson
)

# audit_stage.panel().show()

# map_panel = pn.pane.IPyWidget(map_view.map)
# map_panel = pn.panel(map_view.map).servable();
# map_panel = pn.panel(map_view.map)

# pn.template.FastListTemplate(
#     site="Panel",
#     title="Getting Started App",
#     sidebar=[dummy_button],
#     main=[layout],
# ).servable(); # The ; is needed in the notebook to not display the template. Its not needed in a script
```

## Complete Pipeline Setup
Add our initialized stages to the pipeline.

```python
# from panel_app.upload_stage import StageUpload
# from panel_app.search_stage import StageSearch

# pipeline.add_stage('Upload', StageUpload)
# pipeline.add_stage('Search', StageSearch)
# pipeline.add_stage('Audit', StageAudit)

# pipeline.show()
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
