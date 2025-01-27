import geopandas as gpd
import param
import panel as pn
from PIL import Image
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

