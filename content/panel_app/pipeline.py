import param
import panel as pn

from panel_app.upload_stage import UploadRegionFiles
from panel_app.search_stage import *
from panel_app.search_techniques import (
    VegetationIndex, Smoothing, ContrastEnhancement, MorphologicalRefinement, ManualThresholding
)
from panel_app.utils import DownloadGeoJSON
from panel_app.targets_stage import AcquireTargetsWidget
from panel_app.stage_audit import MapView


class StageUpload(param.Parameterized):
    def __init__(self, **params):
        super().__init__(**params)
        self._add_upload_widgets()

    @param.output(
        input_image=param.Parameter, 
        region_geojson=param.Parameter
    )
    def output(self):
        region_orthophoto = self.upload_widgets.get_region_image()
        region_geojson = self.upload_widgets.get_region_geojson()
        return region_orthophoto, region_geojson
    
    def _add_upload_widgets(self):
        self.upload_widgets = UploadRegionFiles()

    def panel(self):
        return pn.Row(self.upload_widgets.view())
    


class StageSearch(param.Parameterized):
    input_image = param.Parameter(default=None, doc="Image to search for targets")
    region_geojson = param.Parameter(default=None, doc="Uploaded geoJSON of work region outline")

    def __init__(self, **params):
        super().__init__(**params)
        if self.input_image is not None:
            self.image_array = np.array(self.input_image) # Needs to be numpy array
        else:
            self.image_array = None # Don't pass empty array
        self._add_search_widgets()

    @param.output(
        binary_mask=param.Parameter,
        region_geojson=param.Parameter
    )
    def output(self):
        return self.target_search.output_image, self.region_geojson
    
    def _add_search_widgets(self):
        veg_index = VegetationIndex()
        smoothing = Smoothing()
        contrast = ContrastEnhancement(enabled=False)
        morphological = MorphologicalRefinement(enabled=True)
        thresholding = ManualThresholding()
        
        self.target_search = TargetSearch(
            input_image=self.image_array,
            techniques=[veg_index, smoothing, contrast, morphological, thresholding]
        )

    def panel(self):
        return pn.Row(self.target_search.view())
    


class StageAcquireTargets(param.Parameterized):
    binary_mask = param.Parameter(default=None, doc="2D np.array of binary mask")
    region_geotiff_path = param.String(default=None, doc="Path to OG geotiff")
    region_geojson = param.Parameter(default=None, doc="Uploaded geoJSON of work region outline")


    def __init__(self, **params):
        super().__init__(**params)
        self._add_aquire_targets_widgets()

        self.download_targets = DownloadGeoJSON(
            source_gdf=self.acquire_targets.targets_gdf,
            filename="targets.geojson",
            button_type="primary",
            name="Download Targets"
        )

    @param.output(
        targets_gdf=param.Parameter,
        region_geojson=param.Parameter
    )
    def output(self):
        return self.acquire_targets.targets_gdf, self.region_geojson
    
    def _add_aquire_targets_widgets(self):
        self.acquire_targets = AcquireTargetsWidget(
            binary_mask=self.binary_mask,
            region_geotiff_path=self.region_geotiff_path
        )

    def panel(self):
        return pn.Row(
            self.acquire_targets.view(),
            self.download_targets.download_widget,
            pn.pane.JSON(self.region_geojson, depth=2, name="Uploaded GeoJSON")
        )



class StageAudit(param.Parameterized):
    region_geojson = param.Dict(allow_None=False, doc="Open GeoJSON file defining the work region outline")
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
            region_geojson = self.region_geojson,
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
    