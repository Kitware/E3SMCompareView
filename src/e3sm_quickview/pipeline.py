import fnmatch
import json
import os


from paraview.simple import (
    FindSource,
    LoadPlugin,
    OutputPort,
    Contour,
    LegacyVTKReader,
)

from vtkmodules.vtkCommonCore import vtkLogger

from collections import defaultdict


# Define a VTK error observer
class ErrorObserver:
    def __init__(self):
        self.error_occurred = False
        self.error_message = ""

    def __call__(self, obj, event):
        self.error_occurred = True

    def clear(self):
        self.error_occurred = False


class EAMVisSource:
    def __init__(self):
        # flag to check if the pipeline is valid
        # this is set to true when the pipeline is updated
        # and the data is available
        self.valid = False

        self.data_file = None
        self.conn_file = None

        # List of all available variables
        self.varmeta = None
        self.dimmeta = None
        self.slicing = defaultdict(int)

        self.data = None
        self.globe = None
        self.projection = "Cyl. Equidistant"
        self.timestamps = []
        self.center = 0.0

        self.extents = [-180.0, 180.0, -90.0, 90.0]
        self.moveextents = [-180.0, 180.0, -90.0, 90.0]

        self.views = {}
        self.vars = {"surface": [], "midpoint": [], "interface": []}

        self.observer = ErrorObserver()
        try:
            plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
            plugins = fnmatch.filter(os.listdir(path=plugin_dir), "*.py")
            for plugin in plugins:
                print("Loading plugin : ", plugin)
                plugpath = os.path.abspath(os.path.join(plugin_dir, plugin))
                if os.path.isfile(plugpath):
                    LoadPlugin(plugpath, ns=globals())

            vtkLogger.SetStderrVerbosity(vtkLogger.VERBOSITY_OFF)
        except Exception as e:
            print("Error loading plugin :", e)

    def ApplyClipping(self, cliplong, cliplat):
        if not self.valid:
            return

        atmos_extract = FindSource("AtmosExtract")
        atmos_extract.LongitudeRange = cliplong
        atmos_extract.LatitudeRange = cliplat

        cont_extract = FindSource("ContExtract")
        cont_extract.LongitudeRange = cliplong
        cont_extract.LatitudeRange = cliplat

    def UpdateCenter(self, center):
        """
        if self.center != int(center):
            self.center = int(center)

            meridian = FindSource("CenterMeridian")
            meridian.CenterMeridian = self.center

            gmeridian = FindSource("GCMeridian")
            gmeridian.CenterMeridian = self.center
        """
        pass

    def UpdateProjection(self, proj):
        if not self.valid:
            return

        atmos_proj = FindSource("AtmosProj")
        cont_proj = FindSource("ContProj")
        grid_proj = FindSource("GridProj")
        if self.projection != proj:
            self.projection = proj
            atmos_proj.Projection = proj
            cont_proj.Projection = proj
            grid_proj.Projection = proj

    def UpdateTimeStep(self, t_index):
        if not self.valid:
            return

    def UpdatePipeline(self, time=0.0):
        if not self.valid:
            return

        atmos_proj = FindSource("AtmosProj")
        if atmos_proj:
            atmos_proj.UpdatePipeline(time)
        self.moveextents = atmos_proj.GetDataInformation().GetBounds()

        cont_proj = FindSource("ContProj")
        if cont_proj:
            cont_proj.UpdatePipeline(time)

        atmos_extract = FindSource("AtmosExtract")
        bounds = atmos_extract.GetDataInformation().GetBounds()

        grid_gen = FindSource("GridGen")
        if grid_gen:
            grid_gen.LongitudeRange = [bounds[0], bounds[1]]
            grid_gen.LatitudeRange = [bounds[2], bounds[3]]
        grid_proj = FindSource("GridProj")
        if grid_proj:
            grid_proj.UpdatePipeline(time)

        self.views["atmosphere_data"] = OutputPort(atmos_proj, 0)
        self.views["continents"] = OutputPort(cont_proj, 0)
        self.views["grid_lines"] = OutputPort(grid_proj, 0)

    def UpdateSlicing(self, dimension, slice):
        if self.slicing.get(dimension) == slice:
            return
        else:
            self.slicing[dimension] = slice
            if self.data is not None:
                x = json.dumps(self.slicing)
                self.data.Slicing = x

    def Update(self, data_file, conn_file, force_reload=False):
        # Check if we need to reload
        if (
            not force_reload
            and self.data_file == data_file
            and self.conn_file == conn_file
        ):
            return self.valid

        self.data_file = data_file
        self.conn_file = conn_file

        if self.data is None:
            data = EAMSliceDataReader(  # noqa: F821
                registrationName="AtmosReader",
                ConnectivityFile=conn_file,
                DataFile=data_file,
            )
            self.data = data
            vtk_obj = data.GetClientSideObject()
            vtk_obj.AddObserver("ErrorEvent", self.observer)
            vtk_obj.GetExecutive().AddObserver("ErrorEvent", self.observer)
            self.varmeta = vtk_obj.GetVariables()
            self.dimmeta = vtk_obj.GetDimensions()

            for dim in self.dimmeta.keys():
                self.slicing[dim] = 0

            self.observer.clear()
        else:
            self.data.DataFile = data_file
            self.data.ConnectivityFile = conn_file
            self.observer.clear()

        try:
            # Update pipeline and force view refresh
            self.data.UpdatePipeline(time=0.0)
            if self.observer.error_occurred:
                raise RuntimeError(
                    "Error occurred in UpdatePipeline. "
                    "Please check if the data and connectivity files exist "
                    "and are compatible"
                )

            # Ensure TimestepValues is always a list
            timestep_values = self.data.TimestepValues
            if isinstance(timestep_values, (list, tuple)):
                self.timestamps = list(timestep_values)
            elif hasattr(timestep_values, "__iter__") and not isinstance(
                timestep_values, str
            ):
                # Handle numpy arrays or other iterables
                self.timestamps = list(timestep_values)
            else:
                # Single value - wrap in a list
                self.timestamps = (
                    [timestep_values] if timestep_values is not None else []
                )

            # Step 1: Extract and transform atmospheric data
            atmos_extract = EAMTransformAndExtract(  # noqa: F821
                registrationName="AtmosExtract", Input=self.data
            )
            atmos_extract.LongitudeRange = [-180.0, 180.0]
            atmos_extract.LatitudeRange = [-90.0, 90.0]
            atmos_extract.UpdatePipeline()
            self.extents = atmos_extract.GetDataInformation().GetBounds()

            # Step 2: Apply map projection to atmospheric data
            atmos_proj = EAMProject(  # noqa: F821
                registrationName="AtmosProj", Input=OutputPort(atmos_extract, 0)
            )
            atmos_proj.Projection = self.projection
            atmos_proj.Translate = 0
            atmos_proj.UpdatePipeline()
            self.moveextents = atmos_proj.GetDataInformation().GetBounds()

            # Step 3: Load and process continent outlines
            if self.globe is None:
                globe_file = os.path.join(
                    os.path.dirname(__file__), "data", "globe.vtk"
                )
                globe_reader = LegacyVTKReader(
                    registrationName="ContReader", FileNames=[globe_file]
                )
                cont_contour = Contour(
                    registrationName="ContContour", Input=globe_reader
                )
                cont_contour.ContourBy = ["POINTS", "cstar"]
                cont_contour.Isosurfaces = [0.5]
                cont_contour.PointMergeMethod = "Uniform Binning"
                self.globe = cont_contour

            # Step 4: Extract and transform continent data
            cont_extract = EAMTransformAndExtract(  # noqa: F821
                registrationName="ContExtract", Input=self.globe
            )
            cont_extract.LongitudeRange = [-180.0, 180.0]
            cont_extract.LatitudeRange = [-90.0, 90.0]

            # Step 5: Apply map projection to continents
            cont_proj = EAMProject(  # noqa: F821
                registrationName="ContProj", Input=OutputPort(cont_extract, 0)
            )
            cont_proj.Projection = self.projection
            cont_proj.Translate = 0
            cont_proj.UpdatePipeline()

            # Step 6: Generate lat/lon grid lines
            grid_gen = EAMGridLines(registrationName="GridGen")  # noqa: F821
            grid_gen.UpdatePipeline()

            # Step 7: Apply map projection to grid lines
            grid_proj = EAMProject(  # noqa: F821
                registrationName="GridProj", Input=OutputPort(grid_gen, 0)
            )
            grid_proj.Projection = self.projection
            grid_proj.Translate = 0
            grid_proj.UpdatePipeline()

            # Step 8: Cache all projected views for rendering
            self.views["atmosphere_data"] = OutputPort(atmos_proj, 0)
            self.views["continents"] = OutputPort(cont_proj, 0)
            self.views["grid_lines"] = OutputPort(grid_proj, 0)

            self.valid = True
            self.observer.clear()
        except Exception as e:
            # print("Error in UpdatePipeline :", e)
            # traceback.print_stack()
            print(e)
            self.valid = False

        return self.valid

    def LoadVariables(self, vars):
        if not self.valid:
            return
        self.data.Variables = vars


if __name__ == "__main__":
    e = EAMVisSource()
