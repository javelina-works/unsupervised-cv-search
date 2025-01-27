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
# from panel_app.pipeline import StageUpload

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
# from panel_app.pipeline import StageSearch
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
# from PIL import Image
# import numpy as np
# from panel_app.pipeline import StageAcquireTargets


# # Run stage manually
# pn.extension()

# binary_mask_image = Image.open(binary_mask_filename)
# binary_mask_array = np.array(binary_mask_image)

# stage3 = StageAcquireTargets(
#     binary_mask=binary_mask_array,
#     region_geotiff_path=region_image_path,
# )
# # stage3.panel() # In notebook
# stage3.panel().show() # In browser
# # stage3.param.outputs()
```

## First Three Stages

```python
from panel_app.pipeline import (
    StageUpload, StageSearch, StageAcquireTargets
)

pipeline.add_stage('Upload', StageUpload)
pipeline.add_stage('Search', StageSearch)
pipeline.add_stage('Acquire Targets', StageAcquireTargets)
pipeline.show()
```

## Audit Targets
- Manually deselect targets missed by the algorithm

```python
# import geopandas as gpd
# import json
# import panel as pn
# from panel_app.pipeline import StageAudit

# # Run audit stage manually
# pn.extension()

# # Convert from file to correct stage input type (gdf)
# targets_gdf = gpd.read_file(targets_plants_filename)

# with open(region_contour_geojson, "r") as f:
#     region_data = json.load(f)

# audit_stage = StageAudit(
#     targets_gdf=targets_gdf,
#     region_geojson=region_data
# )

# audit_stage.panel().show()

```

## Complete Pipeline Setup
Add our initialized stages to the pipeline.

```python
# from panel_app.pipeline import (
#     StageUpload, StageSearch, StageAcquireTargets, StageAudit
# )

# pipeline.add_stage('Upload', StageUpload)
# pipeline.add_stage('Search', StageSearch)
# pipeline.add_stage('Targeting', StageAcquireTargets)
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
