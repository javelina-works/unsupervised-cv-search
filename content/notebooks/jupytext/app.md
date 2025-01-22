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
import geopandas as gpd
import matplotlib.pyplot as plt
from io import BytesIO
import json

pn.extension('filedropper')


class TargetAuditApp(param.Parameterized):
    # Parameters for tracking uploaded files
    region_image = param.Parameter(default=None)
    region_geojson = param.Parameter(default=None)

    # FileDropper widgets

    # Accepted filetypes bug for this widget: https://github.com/holoviz/panel/issues/7153
    # accepted_filetypes=["allowed/geojson", ".geojson"],
    image_dropper = pn.widgets.FileDropper(height=100, max_file_size ="500MB")
    geojson_dropper = pn.widgets.FileDropper(height=100, max_file_size ="100MB")

    def __init__(self, **params):
        super().__init__(**params)

        # Link FileDropper outputs to parameters
        self.image_dropper.param.watch(self._update_region_image, "value")
        self.geojson_dropper.param.watch(self._update_region_geojson, "value")

    # Update methods for parameters
    def _update_region_image(self, event):
        if event.new:
            self.region_image = event.new[0]  # Use the first file uploaded

    def _update_region_geojson(self, event):
        if event.new:
            first_file_name = list(event.new.keys())[0] # Dict of file names:bytes
            file_bytes_string = event.new[first_file_name].decode("utf-8") # Bytes to string
            self.region_geojson = json.loads(file_bytes_string)  # String to JSON dict

    # A method to display the uploaded region image
    def view_image(self):
        if self.region_image:
            try:
                image_data = BytesIO(self.region_image["content"])
                fig, ax = plt.subplots(figsize=(8, 8))
                img = plt.imread(image_data)
                ax.imshow(img)
                ax.axis('off')
                return pn.pane.Matplotlib(fig)
            except Exception as e:
                return f"Error displaying image: {e}"
        else:
            return "No image uploaded."

    # A method to display the GeoJSON region outline
    def view_geojson(self):
        if self.region_geojson:
            try:
                return pn.pane.JSON(self.region_geojson, depth=2, name="Uploaded GeoJSON")
                return f"{self.region_geojson}"
                # region_contour_data = self.region_geojson.decode("utf-8")
                # return f"{region_contour_data}"
                geojson_data = BytesIO(self.region_geojson["content"])
                gdf = gpd.read_file(geojson_data)
                print(gdf)  # Print the GeoDataFrame to the console
                return f"GeoJSON loaded successfully. Number of features: {len(gdf)}"
            except Exception as e:
                return f"Error processing GeoJSON: {e}"
        else:
            return "No GeoJSON uploaded."

    # Panel layout combining file droppers and visualizations
    def panel(self):
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
target_audit_app = TargetAuditApp()
target_audit_app.panel().servable()

target_audit_app.panel()
```

```python
target_audit_app.geojson_dropper.value
```

```python
target_audit_app.region_geojson
type(target_audit_app.region_geojson)
```
