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

## Upload Input Files

```python
import param
import panel as pn
import geopandas as gpd
from io import BytesIO
import json
from PIL import Image
import geoviews as gv

# gv.extension('bokeh')
pn.extension('filedropper')

class UploadRegionFiles(param.Parameterized):
    # Parameters for tracking uploaded files
    region_image_upload = param.Parameter(default=None)
    region_geojson_upload = param.Parameter(default=None)
    region_image_thumbnail_dims = param.Integer(default=1000, step=250, bounds=(250, 2000), doc="Max dims of uploaded image thumbnail")

    region_image_upload_name = param.Parameter(default=None)
    region_geojson_upload_name = param.Parameter(default=None)

    # FileDropper widgets

    # Accepted filetypes bug for this widget: https://github.com/holoviz/panel/issues/7153
    # accepted_filetypes=["allowed/geojson", ".geojson"],
    # Unable to handle our large geoTiff images
    image_dropper = pn.widgets.FileDropper(height=100, max_file_size ="500MB", chunk_size=10_000_000)
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
                pil_image = self.get_region_image()
                thumb_dim = self.region_image_thumbnail_dims
                pil_image.thumbnail((thumb_dim, thumb_dim))
                return pn.pane.Image(pil_image, height=500, width=500)
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

                # gdf = gpd.GeoDataFrame.from_features(region_geojson["features"])
                # # gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.001)  # Reduce geometry complexity
                # gv_geojson = gv.Polygons(gdf, vdims=["name"] if "name" in gdf.columns else None).opts(
                #     fill_alpha=0.5,
                #     line_width=2,
                #     color="blue",
                #     tools=["hover"],
                #     active_tools=["wheel_zoom"],
                #     width=600,
                #     height=400,
                #     title="Region Outline Visualization"
                # )
                # view_pane = pn.pane.HoloViews(gv_geojson, height=400, width=600)

                geojson_row = pn.Row(
                    json_pane, 
                    # view_pane
                )
                return pn.panel(geojson_row)
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


# # Run the app
# target_audit_app = UploadRegionFiles()
# target_audit_app.view().servable()

# target_audit_app.view().show()
```

```python
import param

class StageUpload(param.Parameterized):
    
    def __init__(self, **params):
        super().__init__(**params)
        self._add_upload_widgets()

    @param.output(input_image=param.Parameter, region_geojson=param.Parameter)
    def output(self):
        region_orthophoto = self.upload_widgets.get_region_image()
        region_geojson = self.upload_widgets.get_region_geojson()
        return region_orthophoto, region_geojson
    
    def _add_upload_widgets(self):
        self.upload_widgets = UploadRegionFiles()

    def panel(self):
        return pn.Row(self.upload_widgets.view())
```
```python
# # Run first stage manually

# stage1 = StageUpload()
# stage1.panel() # In notebook
# stage1.panel().show() # In browser
# # stage1.param.outputs()
```

```python
# import numpy as np

# img, gjson = stage1.output()
# print(type(gjson))
# print(type(img))

# image_array = np.array(img)
# print(type(image_array))  # Should print: <class 'numpy.ndarray'>
# print(image_array.shape)  # Shape of the array
```

## Perform CV Search
- Set parameters for CV seach
- Perform on uploaded image

```python
from skimage.exposure import equalize_adapthist
from skimage.filters import threshold_otsu
from skimage.morphology import opening, closing, disk
import cv2
import numpy as np

from plant_search.vegetation_indices import normalize_rgb, calculate_exg

import param
import panel as pn


class ProcessingTechnique(param.Parameterized):
    enabled = param.Boolean(default=True, doc="Choose to enable processing technique")
    input_image = param.Parameter(default=None, doc="Input image to process")
    output_image = param.Parameter(default=None, doc="Processed image after applying the technique")

    def __init__(self, **params):
        super().__init__(**params)
        # Assume output=input until technique is applied
        if self.output_image is None:
            self.output_image = self.input_image

        self._apply_button_widget = pn.widgets.Button(name="Apply", button_type="primary")
        self._apply_button_widget.on_click(self._handle_update_button)
        self._reset_button_widget = pn.widgets.Button(name="Reset Parameters", button_type="warning")
        self._reset_button_widget.on_click(self._reset_params)
        self.image_outdated = False
        self._watch_for_outdated()

    def perform_technique(self, image):
        raise NotImplementedError("Each technique must implement the `apply` method.")

    def _watch_for_outdated(self):
        """Set up watchers to mark the image as outdated when any parameter changes."""
        for name, parameter in self.param.objects("existing").items():
            if name not in {"output_image", "image_outdated"} and not parameter.constant and not parameter.readonly:
                self.param.watch(self._mark_outdated, name)

    def _mark_outdated(self, event=None):
        """Mark the image as outdated."""
        self.image_outdated = True

    def _handle_update_button(self, event):
            # Manually apply technique to prevent large overhead
            # Originally auto-computed, but cascading updates too expensive
            self.image_outdated = False
            self.update_output() # Calculate technique, update output

    def _reset_params(self, event=None):
        """Reset all parameters to their default values."""
        defaults = {
            name: param.default 
            for name, param in self.param.objects('existing').items()
            if (
                not param.constant and 
                not param.readonly and
                name != 'input_image' # Don't remove input image
            )
        }
        self.param.update(**defaults)
        self.image_outdated = True # Need to apply to get new computation

    def _prepare_np_image(self, image):
        updated = image
        if len(updated.shape) >= 3 and updated.shape[2] > 3:
            updated = updated[:, :, :3] # Max 3 bands
        if updated.dtype != np.uint8:
            updated = (updated).astype(np.uint8)  # Scale to [0, 255]
        return updated

    def apply(self, image):
        """
        Performs technique on passed image. However, this does NOT
        assume argument is 'input_image', and does NOT update the 
        param's 'output_image'. 
        """
        if self.enabled:
            prep_image = self._prepare_np_image(image) # Get to standard np_array form
            return self.perform_technique(prep_image)
        else:
            return image # Pass along without updating


    @param.depends("input_image", "enabled", watch=True)
    def _passthrough_output(self):
        """
        We assume multiple techniques may be used in sequence.

        If 'input_image' is updated and technique is disabled, simply
        pass 'input_image' through to output.

        This allows later stages to have their inputs auto-updated if
        watching for updates to this stage's output_image.
        """
        if not self.enabled:
            self.output_image = self.input_image

    def update_output(self):
        """
        Performs technique on own 'input_image', and updates 'output_image'.

        This is the only method that computes and sets 'output_image' from
        the object's own 'input_image'.
        """
        if self.input_image is not None:
            self.output_image = self.apply(self.input_image)

    def view_outdated_warning(self):
        """Return the complete UI for this technique."""
        warning_message = (
            pn.pane.Markdown(
                "**Apply to update**"
            )
            if self.image_outdated
            else ""
        )
        return warning_message

    def view_image(self):
        if self.input_image is not None:
            try:
                # output = self.apply(self.input_image)
                # output_image = Image.fromarray(output)
                input_image = Image.fromarray(self.input_image)
                if self.output_image is not None:
                    output_image = Image.fromarray(self.output_image)
                else:
                    output_image = Image.fromarray(self.input_image)

                images_row = pn.Row(
                    pn.pane.Image(input_image, height=500, width=500),
                    pn.pane.Image(output_image, height=500, width=500)
                )
                return images_row 
            except Exception as e:
                return f"{self.name}: Error displaying image: {e}"
        else:
            return "No image uploaded."

    def view(self):
        panel_column = pn.Row(
            pn.Column(
                self.param,
                self._reset_button_widget,
                pn.Row(self._apply_button_widget, self.view_outdated_warning),
            ),
            self.view_image
        )
        return panel_column



class VegetationIndex(ProcessingTechnique):
    selected_vegetation_index = param.Selector(objects=["exg"])

    def perform_technique(self, image):
        exg = calculate_exg(*normalize_rgb(image))
        exg_normalized = (exg - np.min(exg)) / (np.max(exg) - np.min(exg))  # Normalize to [0, 1]
        exg_uint8 = (exg_normalized * 255).astype(np.uint8)
        return exg_uint8


class Smoothing(ProcessingTechnique):
    smoothing_diameter = param.Integer(default=9, bounds=(3, 20), doc="Diameter of each pixel neighborhood used during filtering.")
    smoothing_sigma_color = param.Number(default=50, bounds=(20,70), doc="Controls how much influence the color difference between pixels has on the filtering")
    smoothing_sigma_spatial = param.Number(default=15, bounds=(0,45), doc="Controls the influence of the spatial distance between pixels.")

    def perform_technique(self, image):
        bilateral_smoothed_img = cv2.bilateralFilter(
            image , d=self.smoothing_diameter, 
            sigmaColor=self.smoothing_sigma_color, 
            sigmaSpace=self.smoothing_sigma_spatial
        )
        # bilateral_smoothed_img = (bilateral_smoothed_img * 255).astype(np.uint8)
        # bilateral_smoothed_exg = bilateral_smoothed_exg / 255.0  # Scale back to [0, 1]
        return bilateral_smoothed_img
    

class ContrastEnhancement(ProcessingTechnique):
    contrast_clip_limit = param.Number(default=0.02, step=0.1, bounds=(0.0, 0.15), doc="Defines the maximum allowed height of the histogram bins in each tile")

    def perform_technique(self, image):
        # image = image / 255
        
        if len(image.shape) == 3 and image.shape[2] == 4:  # RGBA
            image = image[:, :, 1]
        elif len(image.shape) == 3:  # RGB
            image = image[:, :, 1]
        # else:  # Grayscale
        #     pil_image = Image.fromarray(image)
        equal = equalize_adapthist(image, clip_limit=self.contrast_clip_limit)
        equal_int8 = (equal).astype(np.uint8) # Needs conversion back to uint8
        return equal_int8


class MorphologicalRefinement(ProcessingTechnique):
    morphological_disk_size = param.Integer(default=7, bounds=(1, 20), doc="Radius of structuring element for contour adjustment")

    def perform_technique(self, image):
        selem = disk(7)  # Structuring element
        morph_img = closing(opening(image, selem), selem)
        return morph_img
    

class ManualThresholding(ProcessingTechnique):
    enabled = param.Boolean(default=True, readonly=True)
    threshold = param.Number(default=0.5, step=0.01, bounds=(0.0, 1.0))

    def perform_technique(self, image):
        scale_image = image / 255.0 # Scale to [0,1] range
        binary_mask = scale_image > self.threshold
        return binary_mask
    

```

```python
import param
import panel as pn      
from PIL import Image

class TargetSearch(param.Parameterized):
    input_image = param.Parameter(default=None, doc="Input orthophoto to search")
    techniques = param.List(default=[])
    sample_downscaling = param.Integer(default=4, bounds=(1,10), doc="Downscale ratio of image shown in intermediate steps")
    output_image = param.Parameter(default=None, doc="Final output image after running the pipeline")

    def __init__(self, **params):
        super().__init__(**params)

        self.sample_image = None
        self.output_image = None
        self._downsample_image()
        self._setup_reactivity()
        # self._chain_techniques()
        self.progress_bar = pn.widgets.Progress(name="Pipeline Progress", value=0, max=100)
        self._pipeline_button_widget = pn.widgets.Button(name="Run full pipeline", button_type="primary")
        self._pipeline_button_widget.on_click(self._handle_pipeline_button)

    @param.depends("input_image", "sample_downscaling", watch=True)
    def _downsample_image(self):
        if self.input_image is not None:
            ds = self.sample_downscaling # Ratio of pixels to ignore
            self.sample_image = self.input_image[::ds, ::ds]
        else:
            self.sample_image = None

    # def _chain_techniques(self):
    #     prev_output = self.input_image
        
    #     for technique in self.techniques:
    #         technique.input_image = prev_output
    #         output = technique.apply(prev_output)
    #         technique.output_image = output  # Store the output in the technique
    #         prev_output = output

    def _setup_reactivity(self):
        """
        Chain the child techniques together reactively.
        
        Each technique will react and update it's input in the event its predecessor's
        'output_image' is updated. 
        """
        for i, technique in enumerate(self.techniques):
            if i == 0: # First technique takes the main input_image as input
                technique.param.update(input_image=self.sample_image)
                # print(f"Linking {technique.__class__.__name__} input_image to TargetSearch input_image.")
                self.param.watch(lambda event, tech=technique: tech.param.update(input_image=event.new), "input_image")
            else: # Subsequent techniques depend on the output of the previous one
                prev_technique = self.techniques[i - 1]
                # print(f"Linking {technique.__class__.__name__} input_image to {prev_technique.__class__.__name__} output_image.")
                prev_technique.param.watch(
                    lambda event, tech=technique: tech.param.update(input_image=event.new),
                    "output_image"
                )

    def _handle_pipeline_button(self, event=None):
        # TODO: trigger full pipeline run event
        output = self.search_targets()
        self.output_image = output


    def update_output(self):
        return

    def search_image(self, image):
        """
        Performs the full search pipeline as configured on an arbitrary image.
        """
        prev_output = image
        output = prev_output # output starts with no changes
        for technique in self.techniques:
            output = technique.apply(prev_output)
            prev_output = output
        return output

    # @param.output()
    def search_targets(self):
        """
        Run the full pipeline and update the progress bar.
        
        """
        if self.input_image is None:
            return None # no image to process
        num_techniques = len(self.techniques)
        if num_techniques == 0:
            print("No techniques to run in the pipeline.")
            return None
        
        self.progress_bar.value = 0
        self.progress_bar.max = num_techniques

        prev_output = self.input_image
        output = prev_output # output starts with no changes
        for i, technique in enumerate(self.techniques):
            output = technique.apply(prev_output)
            prev_output = output
            self.progress_bar.value = i + 1
            
        self.progress_bar.value = self.progress_bar.max
        return output
    
        # for technique in self.techniques:
        #     technique.update_output()
        # return self.techniques[-1].output_image if self.techniques else None

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

    @param.depends("output_image", watch=False)
    def view_images(self):
        if self.input_image is not None:
            try:
                input_image = self._downscale_for_display(self.input_image)
                input_image_pane = pn.pane.Image(input_image, height=500, width=500)
            except Exception as e:
                input_image_pane = f"{self.name}: Error displaying input image: {e}"
        else:
            input_image_pane = "No image uploaded."
        
        if self.output_image is not None:
            try:
                output_image = self._downscale_for_display(self.output_image)
                output_image_pane = pn.pane.Image(output_image, height=500, width=500)
            except Exception as e:
                output_image_pane = f"{self.name}: Error displaying output image: {e}"
        else:
            output_image_pane = "Output not yet generated!"
            
        return pn.Row(input_image_pane, output_image_pane)

    @param.depends()
    def view(self):
        # panels = [technique.view() for technique in self.techniques]
        tabs = pn.Tabs(
            *[  (technique.__class__.__name__, technique.view())
                for technique in self.techniques
            ])

        target_panel = pn.Column(
            pn.Row("**Find targets from image**"),
            tabs,
            pn.layout.Divider(),
            pn.Row(self._pipeline_button_widget, self.progress_bar,),
            self.view_images,
        )
        return target_panel
    
    
```

```python
import param
import numpy as np

class StageSearch(param.Parameterized):
    input_image = param.Parameter(default=None, doc="Image to search for targets")

    def __init__(self, **params):
        super().__init__(**params)
        self._add_search_widgets()

    @param.output(binary_mask=param.Parameter())
    def output(self):
        return self.target_search.output_image
    
    def _add_search_widgets(self):
        veg_index = VegetationIndex()
        smoothing = Smoothing()
        contrast = ContrastEnhancement(enabled=False)
        morphological = MorphologicalRefinement(enabled=True)
        thresholding = ManualThresholding()
        
        image_array = np.array(self.input_image) # Needs to be numpy array
        self.target_search = TargetSearch(
            input_image=image_array,
            techniques=[veg_index, smoothing, contrast, morphological, thresholding]
        )

    def panel(self):
        return pn.Row(self.target_search.view())

```

```python
# # Manually run this stage
# from plant_search.load_image import load_image

# ds = 1 # downscale ratio
# image, transform, bounds, crs = load_image(region_image_path)
# if image is not None and ds > 1:
#     image_data = image[::ds, ::ds]
# else:
#     image_data = image

# veg_index = VegetationIndex()
# smoothing = Smoothing()
# contrast = ContrastEnhancement(enabled=False)
# morphological = MorphologicalRefinement(enabled=False)
# thresholding = ManualThresholding()

# search = TargetSearch(
#     input_image=image_data, 
#     techniques=[veg_index, smoothing, contrast, morphological, thresholding]
# )
# search.view().show()
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

## First Two Stages

```python
# pipeline.add_stage('Upload', StageUpload)
# pipeline.add_stage('Search', StageSearch)
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

pipeline.add_stage('Upload', StageUpload)
pipeline.add_stage('Search', StageSearch)
pipeline.add_stage('Audit', StageAudit)

pipeline.show()
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
