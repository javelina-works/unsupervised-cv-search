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

# # Panel App: Target Audit
#
# A multi-stage application for auditing the targets within our region orthophoto.
#
# - Upload region image
# - Select samples of region
# - Set parameters for CV search
#     - Visualize parameters
# - Run parameters on full orthophoto
#     - View output
# - Generate binary mask
# - Audit detected targets on map
# - Save targets to local geoJSON
#
#

# +
import param
import panel as pn

pipeline = pn.pipeline.Pipeline()
# -

import sys
import geopandas as gpd
from pathlib import Path
sys.path.append(str(Path.cwd().parent))

# +
region_crs = 32613 # Use this everywhere for consistency
visualization_crs = 4326 # Use this when we need leaflet visualizations

# region_image_path = '../input/IGNORE_Brewster-2024-all-orthophoto-UTM-32613.tif'
region_image_path = '../tile_server/input/IGNORE_reprojected_region.tif'

region_contour_geojson = '../input/interactive_proto/region_contour.geojson'
micro_routes_filename = '../input/interactive_proto/micro_routes.geojson'
targets_plants_filename = '../input/interactive_proto/targets.geojson'
depots_filename = '../input/interactive_proto/depot_points.geojson'

# -

# ## Upload Input Files

# +
import param
import panel as pn
import geopandas as gpd
from io import BytesIO
import json
from PIL import Image
import geoviews as gv

gv.extension('bokeh')
pn.extension('filedropper')

class UploadRegionFiles(param.Parameterized):
    # Parameters for tracking uploaded files
    region_image_upload = param.Parameter(default=None)
    region_geojson_upload = param.Parameter(default=None)
    
    region_image_upload_name = param.Parameter(default=None)
    region_geojson_upload_name = param.Parameter(default=None)

    # FileDropper widgets

    # Accepted filetypes bug for this widget: https://github.com/holoviz/panel/issues/7153
    # accepted_filetypes=["allowed/geojson", ".geojson"],
    # Unable to handle our large geoTiff images
    image_dropper = pn.widgets.FileDropper(height=100, max_file_size ="500MB", chunk_size=30000000)
    geojson_dropper = pn.widgets.FileDropper(height=100, max_file_size ="100MB")

    def __init__(self, **params):
        super().__init__(**params)

        # Link FileDropper outputs to parameters
        self.image_dropper.param.watch(self._update_region_image, "value")
        self.geojson_dropper.param.watch(self._update_region_geojson, "value")

    # Update methods for parameters
    def _update_region_image(self, event):
            # Upate for all events, including removal of file
            self.region_image_upload = event.new
            self.get_region_image() # Update name & contents when possible

    def _update_region_geojson(self, event):
        self.region_geojson_upload = event.new
        self.get_region_geojson() # Update name & contents when event triggered

    def get_region_image(self):
        if self.region_image_upload:
            image_upload_dict = self.region_image_upload # Stays as dict of files
            first_file_name = list(image_upload_dict.keys())[0] # Dict of file names:bytes
            image_stream  = BytesIO(image_upload_dict[first_file_name]) # Bytes to Stream
            region_image = Image.open(image_stream)  # Stream to PIL image
            self.region_image_upload_name = first_file_name
            return region_image
        else:
            self.region_image_upload_name = None
            return None

    def get_region_geojson(self):
        if self.region_geojson_upload:
            geojson_upload_dict = self.region_geojson_upload # Dict of files
            first_file_name = list(geojson_upload_dict.keys())[0] # Dict of file names:bytes
            file_bytes_string = geojson_upload_dict[first_file_name].decode("utf-8") # Bytes to string
            region_geojson = json.loads(file_bytes_string)  # String to JSON dict
            
            self.region_geojson_upload_name = first_file_name
            return region_geojson
        else:
            self.region_geojson_upload_name = None # Remember to reset when deleted
            return None

    def view_image(self):
        if self.region_image_upload:
            try:
                image_data = self.get_region_image()
                return pn.pane.Image(image_data, height=500, width=500)
            except Exception as e:
                return f"Error displaying image: {e}"
        else:
            return "No image uploaded."

    # A method to display the GeoJSON region outline
    def view_geojson(self):
        if self.region_geojson_upload:
            try:
                region_geojson = self.get_region_geojson()
                json_pane = pn.pane.JSON(region_geojson, depth=2, name="Uploaded GeoJSON")

                gdf = gpd.GeoDataFrame.from_features(region_geojson["features"])
                gv_geojson = gv.Polygons(gdf, vdims=["name"] if "name" in gdf.columns else None).opts(
                    fill_alpha=0.5,
                    line_width=2,
                    color="blue",
                    tools=["hover"],
                    active_tools=["wheel_zoom"],
                    width=600,
                    height=400,
                    title="Region Outline Visualization"
                )

                geojson_row = pn.Row(json_pane, gv_geojson)

                return geojson_row
            except Exception as e:
                return f"Error processing GeoJSON: {e}"
        else:
            return "No GeoJSON uploaded."

    # Panel layout combining file droppers and visualizations
    def view(self):
        return pn.Column(
            pn.Row(
                pn.Column("**Drop Region Image Here**", self.image_dropper),
                pn.Column("**Drop GeoJSON Here**", self.geojson_dropper),
            ),
            pn.Row(
                pn.Column("**Uploaded Region Image**", self.view_image),
                pn.Column("**Uploaded GeoJSON Outline**", self.view_geojson),
            ),
        )


# Run the app
target_audit_app = UploadRegionFiles(

)
# target_audit_app.panel().servable()

target_audit_app.view().show()

# +

print(target_audit_app.region_image_upload)
# print(target_audit_app.get_region_image())

# target_audit_app.param

# +
import param

class StageUpload(param.Parameterized):
    
    def __init__(self, **params):
        super().__init__(**params)
        self._add_upload_widgets()

    @param.output()
    def output(self):
        return
    
    def _add_upload_widgets(self):
        self.upload_widgets = UploadRegionFiles()

    def panel(self):
        return self.upload_widgets.panel().servable()
# -



# ## Perform CV Search
# - Set parameters for CV seach
# - Perform on uploaded image

# +
import param

class StageSearch(param.Parameterized):
    
    def __init__(self, **params):
        super().__init__(**params)
        self._add_upload_widgets()

    @param.output()
    def output(self):
        return
    
    def _add_upload_widgets(self):
        self.upload_widgets = TargetAuditApp()

    def panel(self):
        return self.upload_widgets.panel().servable()


# -

# ## Audit Targets
# - Manually deselect targets missed by the algorithm

# +
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


# +
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


# +
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
    


# +
import geopandas as gpd

pn.extension()

# Convert from file to correct stage input type (gdf)
targets_gdf = gpd.read_file(targets_plants_filename)

audit_stage = StageAudit(
    targets_gdf=targets_gdf,
    region_geojson_path=region_contour_geojson
)

audit_stage.panel().show()

# map_panel = pn.pane.IPyWidget(map_view.map)
# map_panel = pn.panel(map_view.map).servable();
# map_panel = pn.panel(map_view.map)

# pn.template.FastListTemplate(
#     site="Panel",
#     title="Getting Started App",
#     sidebar=[dummy_button],
#     main=[layout],
# ).servable(); # The ; is needed in the notebook to not display the template. Its not needed in a script
# -

# ## Complete Pipeline Setup
# Add our initialized stages to the pipeline.

# +

pipeline.add_stage('Upload', StageUpload)
pipeline.add_stage('Search', StageSearch)
pipeline.add_stage('Audit', StageAudit)

# pipeline.show()

# + vscode={"languageId": "raw"} active=""
# import param
# import json
# from shapely.geometry import shape
# import panel as pn
# from plant_search.verify_targets import get_image_sample_coordinates
#
#
# class RegionSampler(param.Parameterized):
#     region_image_path = param.String(doc="Path to the orthophoto image")
#     region_geojson_path = param.String(doc="Path to the GeoJSON file defining the region")
#
#     sample_size = param.Integer(1024, bounds=(512, 4096), step=256, doc="Size of individual samples")
#     num_samples = param.Integer(5, bounds=(1, 12), doc="Number of random samples")
#     save_samples = param.Action(lambda self: self._save_samples(), label="Save Samples")
#     
#     def __init__(self, **params):
#         super().__init__(**params)
#         self.sample_boxes_gdf = None
#         self.get_samples()
#
#     def __call__(self):
#         return self.sample_boxes_gdf
#
#     def get_samples(self):
#         self.sample_boxes_gdf = get_image_sample_coordinates(
#             self.region_image_path, self.sample_size, self.num_samples, self.region_geojson_path
#         )
#         return self.sample_boxes_gdf
#         # return get_image_sample_coordinates(
#         #     self.region_image_path, self.sample_size, self.num_samples, self.region_geojson_path
#         # )
#
#     # @param.depends('sample_size', 'num_samples', watch=True)
#     # def update_samples(self):
#     #     self.sample_boxes_gdf = get_image_sample_coordinates(
#     #         self.region_image_path, self.sample_size, self.num_samples, self.region_geojson_path
#     #     )
#
# # Instantiate and serve the app
# sampler = RegionSampler(
#     region_image_path = region_image_path,
#     region_geojson_path = region_contour_geojson
# )
#
# pn.extension()
# pn.Column(sampler.param, sampler.get_samples)
