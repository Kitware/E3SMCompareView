import asyncio
import math

import numpy as np

import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
from paraview import simple
from paraview.modules.vtkPVVTKExtensionsInteractionStyle import (
    vtkPVInteractorStyle,
    vtkPVTrackballZoom,
    vtkTrackballPan,
)
from trame.app import TrameComponent, dataclass
from trame.decorators import controller
from trame.ui.html import DivLayout
from trame.widgets import client, html, rca
from trame.widgets import vuetify3 as v3
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkCamera,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from e3sm_compareview.components import view as tview
from e3sm_compareview.utils import format_color_range_endpoints
from e3sm_quickview.presets import COLOR_BLIND_SAFE
from e3sm_quickview.utils.color import COLORBAR_CACHE, lut_to_img
from e3sm_quickview.utils.math import compute_color_ticks, tick_contrast_color


def auto_size_to_col(size):
    if size == 1:
        return 12

    if size >= 8 and size % 2 == 0:
        return 3

    if size % 3 == 0:
        return 4

    if size % 2 == 0:
        return 6

    return auto_size_to_col(size + 1)


COL_SIZE_LOOKUP = {
    0: auto_size_to_col,
    1: 12,
    2: 6,
    3: 4,
    4: 3,
    6: 2,
    12: 1,
    "flow": None,
}


def lut_name(element):
    return element.get("name").lower()


class ViewConfiguration(dataclass.StateDataModel):
    variable: str = dataclass.Sync(str)
    base_variable: str = dataclass.Sync(str, "")
    label: str = dataclass.Sync(str, "")
    preset: str = dataclass.Sync(str, "BuGnYl")
    invert: bool = dataclass.Sync(bool, False)
    color_blind: bool = dataclass.Sync(bool, False)
    use_log_scale: str = dataclass.Sync(str, "linear")
    color_value_min: str = dataclass.Sync(str, "0")
    color_value_max: str = dataclass.Sync(str, "1")
    color_value_min_valid: bool = dataclass.Sync(bool, True)
    color_value_max_valid: bool = dataclass.Sync(bool, True)
    color_range: list[float] = dataclass.Sync(tuple[float, float], (0, 1))
    override_range: bool = dataclass.Sync(bool, False)
    order: int = dataclass.Sync(int, 0)
    size: int = dataclass.Sync(int, 4)
    offset: int = dataclass.Sync(int, 0)
    break_row: bool = dataclass.Sync(bool, False)
    menu: bool = dataclass.Sync(bool, False)
    swap_group: list[str] = dataclass.Sync(list[str], list)
    search: str | None = dataclass.Sync(str)
    n_colors: int = dataclass.Sync(int, 255)
    lut_img: str = dataclass.Sync(str)
    color_ticks: list = dataclass.Sync(list, list)
    effective_color_range: list[float] = dataclass.Sync(tuple[float, float], (0, 1))
    color_range_min_label: str = dataclass.Sync(str, "0")
    color_range_max_label: str = dataclass.Sync(str, "1")


class VariableView(TrameComponent):
    def __init__(self, server, source, view_spec, variable_type, camera):
        super().__init__(server)
        self.source = source
        self.view_spec = view_spec
        self.array_name = view_spec["array_name"]
        self.base_variable = view_spec["base_variable"]
        self.role = view_spec["role"]
        self.comparison_mode = view_spec.get("comparison_mode", "multi-sim")
        self.comparison_type = view_spec.get("comparison_type", "diff")
        self.display_label = view_spec["label"]
        self.variable_type = variable_type
        self.config = ViewConfiguration(server, variable=self.array_name)
        self.config.base_variable = self.base_variable
        self.config.label = self.display_label
        self.name = f"view_{self.array_name}"
        self._bounds_key = f"{self.name}_bounds"
        self._size = (0, 0)

        if self.role in ("control", "test", "source"):
            self.config.preset = "navia"
        elif self.role == "diff":
            self.config.preset = "Cool to Warm (Extended)"
        elif self.role in ("comp1", "comp2"):
            self.config.preset = "bam"
            self.config.invert = True

        self.disable_render = False

        self.renderer = vtkRenderer()
        self.renderer.SetActiveCamera(camera)
        self.renderer.SetBackground(1, 1, 1)
        self._camera = camera
        self.mapper = vtkPolyDataMapper()
        self.actor = vtkActor()
        self.actor.SetMapper(self.mapper)
        self.renderer.AddActor(self.actor)

        # Lookup table color management
        self.lut = simple.GetColorTransferFunction(self.array_name)
        self.lut.NanOpacity = 0.0

        self.mapper.SetScalarVisibility(1)
        self.mapper.SetScalarModeToUseCellFieldData()
        self.mapper.SelectColorArray(self.array_name)
        self.mapper.SetLookupTable(self.lut.GetClientSideObject())
        self._connect_pipeline_input()

        # Add shared annotation actors
        continents_actor = source.continent.actor
        if continents_actor is not None:
            self.renderer.AddActor(continents_actor)
        grid_lines_actor = source.grid_lines.actor
        if grid_lines_actor is not None:
            self.renderer.AddActor(grid_lines_actor)

        # Reactive behavior
        self.config.watch(
            ["color_value_min", "color_value_max"],
            self.color_range_str_to_float,
        )
        self.config.watch(
            ["override_range", "color_range"], self.update_color_range, eager=True
        )
        self.config.watch(
            ["preset", "invert", "use_log_scale", "n_colors"],
            self.update_color_preset,
            eager=True,
        )

        # GUI
        self._build_ui()

    def _connect_pipeline_input(self):
        atmosphere_data = self.source.data_reader.vtk_geometry
        if atmosphere_data is not None:
            self.mapper.SetInputConnection(atmosphere_data.output_port)

    def update_view_spec(self, view_spec):
        self.view_spec = view_spec
        self.base_variable = view_spec["base_variable"]
        self.role = view_spec["role"]
        self.comparison_mode = view_spec.get("comparison_mode", "multi-sim")
        self.comparison_type = view_spec.get("comparison_type", "diff")
        self.display_label = view_spec["label"]
        self.config.base_variable = self.base_variable
        self.config.label = self.display_label
        self._connect_pipeline_input()

    @property
    def bounds(self):
        return self.state[self._bounds_key]

    @bounds.setter
    def bounds(self, value):
        self.renderer.SetViewport(*value)
        with self.state as state:
            state[self._bounds_key] = value

    def update_size(self, size):
        new_size = (int(size["w"] * size["p"]), int(size["h"] * size["p"]))
        if self._size != new_size:
            self._size = new_size
            self.ctrl.size_update()

    @property
    def size(self):
        return self._size

    def render(self):
        if self.disable_render or not self.ctx.view:
            return
        self.ctx.view.update()

    @property
    def camera(self):
        return self._camera

    def reset_camera(self):
        self.renderer.ResetCameraScreenSpace(0.9)
        self.render()

    def update_color_preset(self, name, invert, log_scale, n_colors=255):
        if log_scale is True:
            scale_mode = "log"
        elif log_scale is False:
            scale_mode = "linear"
        else:
            scale_mode = log_scale

        if scale_mode not in {"linear", "log", "symlog"}:
            scale_mode = "linear"

        self.config.preset = name
        if self.config.use_log_scale != scale_mode:
            self.config.use_log_scale = scale_mode

        # ApplyPreset resets range to [0,1], so always apply the linear
        # preset first, rescale to the current range, then apply transforms
        self._apply_linear_to_lut(invert)
        self.lut.RescaleTransferFunction(*self.config.color_range)

        if n_colors is not None:
            self.lut.NumberOfTableValues = n_colors

        # Capture the colorbar image and tick marks from the LINEAR LUT
        # before any log/symlog transform so the bar always looks linear.
        self.config.lut_img = lut_to_img(self.lut)
        self._compute_ticks()

        if scale_mode == "log":
            self._apply_log_to_lut()
        elif scale_mode == "symlog":
            self._apply_symlog_to_lut()

        # Read the actual LUT range (may differ from color_range for log scale)
        ctf = self.lut.GetClientSideObject()
        self.config.effective_color_range = ctf.GetRange()

        # Force mapper to pick up LUT changes
        self.mapper.SetLookupTable(ctf)
        self.mapper.Modified()
        self.render()

    def _apply_linear_to_lut(self, invert=False):
        """Apply preset with linear scale."""
        self.lut.UseLogScale = 0
        self.lut.ApplyPreset(self.config.preset, True)
        if invert:
            self.lut.InvertTransferFunction()

    def _apply_log_to_lut(self):
        """Transform the already-prepared LUT to log scale.

        Log scale requires all positive values, so clamp the range if needed.
        """
        ctf = self.lut.GetClientSideObject()
        x_min, x_max = ctf.GetRange()
        if x_max <= 0:
            return
        if x_min <= 0:
            x_min = x_max * 1e-6
            self.lut.RescaleTransferFunction(x_min, x_max)
        self.lut.MapControlPointsToLogSpace()
        self.lut.UseLogScale = 1

    def _apply_symlog_to_lut(
        self, linthresh=None, linscale=1.0, base=10, n_samples=256
    ):
        """Transform the already-prepared LUT to symmetric log scale.

        Uses:
        - Linear for |x| <= linthresh
        - Logarithmic for |x| > linthresh
        with continuity at the boundary.

        Samples colors from the linear preset and redistributes them
        across the data range using symlog spacing.
        """
        # Get the current data range from the LUT
        ctf = self.lut.GetClientSideObject()
        x_min, x_max = ctf.GetRange()
        data_range = x_max - x_min
        if data_range == 0:
            return

        if linthresh is None:
            linthresh = max(abs(x_min), abs(x_max)) * 1e-2
            if linthresh == 0:
                linthresh = 1.0

        log_base = np.log(base)
        linscale_adj = linscale / (1.0 - base**-1)

        def symlog(x):
            abs_x = np.abs(x)
            # Clip to avoid log(0); values <= linthresh use linear branch anyway
            safe_abs = np.maximum(abs_x, linthresh)
            out = np.where(
                abs_x <= linthresh,
                x * linscale_adj,
                np.sign(x)
                * linthresh
                * (linscale_adj + np.log(safe_abs / linthresh) / log_base),
            )
            return out

        # Sample colors from the linear LUT at uniform positions
        rgb = [0.0, 0.0, 0.0]
        s_min = symlog(x_min)
        s_max = symlog(x_max)
        s_range = s_max - s_min
        if s_range == 0:
            return

        new_rgb_points = []
        for i in range(n_samples):
            # Uniform position in data space
            t = i / (n_samples - 1)
            x_data = x_min + t * data_range

            # Map x_data through symlog, normalize to [0,1], then look up
            # the color at the corresponding linear position
            s_val = symlog(x_data)
            s_t = (s_val - s_min) / s_range
            x_lookup = x_min + s_t * data_range
            ctf.GetColor(x_lookup, rgb)
            new_rgb_points.extend(
                [float(x_data), float(rgb[0]), float(rgb[1]), float(rgb[2])]
            )

        # Write back through the proxy so state stays in sync
        self.lut.RGBPoints = new_rgb_points

    def color_range_str_to_float(self, color_value_min, color_value_max):
        try:
            min_value = float(color_value_min)
            self.config.color_value_min_valid = not math.isnan(min_value)
        except ValueError:
            self.config.color_value_min_valid = False

        try:
            max_value = float(color_value_max)
            self.config.color_value_max_valid = not math.isnan(max_value)
        except ValueError:
            self.config.color_value_max_valid = False

        if self.config.color_value_min_valid and self.config.color_value_max_valid:
            self.config.color_range = (min_value, max_value)

    @staticmethod
    def _is_finite_range(data_range):
        if data_range is None or len(data_range) < 2:
            return False
        return math.isfinite(data_range[0]) and math.isfinite(data_range[1])

    @staticmethod
    def _max_abs_from_ranges(ranges):
        max_abs = None
        for data_range in ranges:
            if data_range is None:
                continue
            candidate = max(abs(data_range[0]), abs(data_range[1]))
            max_abs = candidate if max_abs is None else max(max_abs, candidate)
        if max_abs is None:
            return None
        return (-max_abs, max_abs)

    def _get_data_array(self, array_name):
        return self.source.data_reader.get_cell_data_array(array_name)

    def _get_data_array_range(self, array_name):
        data_array = self._get_data_array(array_name)
        if data_array is None:
            return None
        data_range = data_array.GetRange()
        if self._is_finite_range(data_range):
            return data_range
        return None

    def _get_multi_sim_default_range(self):
        data_range = self._get_data_array_range(self.array_name)
        if self.role in ("diff", "comp1", "comp2"):
            return self._max_abs_from_ranges([data_range])
        return data_range

    def _get_two_sim_default_range(self):
        two_sim_specs = self.source.data_reader.get_view_specs(
            self.base_variable,
            "two-sim",
            self.comparison_type,
            ["ctrl", "test", "diff", "comp1", "comp2"],
        )
        spec_by_role = {spec["role"]: spec for spec in two_sim_specs}

        if self.role in ("control", "test"):
            ctrl_spec = spec_by_role.get("control")
            test_spec = spec_by_role.get("test")
            if ctrl_spec and test_spec:
                ctrl_range = self._get_data_array_range(ctrl_spec["array_name"])
                test_range = self._get_data_array_range(test_spec["array_name"])
                if ctrl_range is not None and test_range is not None:
                    return (
                        min(ctrl_range[0], test_range[0]),
                        max(ctrl_range[1], test_range[1]),
                    )

        if self.role == "diff":
            diff_spec = spec_by_role.get("diff")
            if diff_spec:
                diff_range = self._get_data_array_range(diff_spec["array_name"])
                if diff_range is not None:
                    return self._max_abs_from_ranges([diff_range])

        if self.role in ("comp1", "comp2"):
            comp_ranges = []
            for role in ("comp1", "comp2"):
                comp_spec = spec_by_role.get(role)
                if not comp_spec:
                    continue
                comp_range = self._get_data_array_range(comp_spec["array_name"])
                if comp_range is not None:
                    comp_ranges.append(comp_range)

            centered = self._max_abs_from_ranges(comp_ranges)
            if centered is not None:
                return centered

        return self._get_data_array_range(self.array_name)

    def _get_default_range(self):
        if self.comparison_mode == "two-sim":
            return self._get_two_sim_default_range()
        return self._get_multi_sim_default_range()

    def update_color_range(self, *_):
        if self.config.override_range:
            skip_update = False
            if math.isnan(self.config.color_range[0]):
                skip_update = True
                self.config.color_value_min_valid = False

            if math.isnan(self.config.color_range[1]):
                skip_update = True
                self.config.color_value_max_valid = False

            if skip_update:
                return

            self.lut.RescaleTransferFunction(*self.config.color_range)
        else:
            data_range = self._get_default_range()
            if data_range is not None:
                self.config.color_range = data_range
                self.config.color_value_min = str(data_range[0])
                self.config.color_value_max = str(data_range[1])
                self.config.color_value_min_valid = True
                self.config.color_value_max_valid = True
                self.lut.RescaleTransferFunction(*data_range)
        self.update_color_preset(
            self.config.preset,
            self.config.invert,
            self.config.use_log_scale,
            self.config.n_colors,
        )

    def _compute_ticks(self):
        vmin, vmax = self.config.color_range
        (
            self.config.color_range_min_label,
            self.config.color_range_max_label,
        ) = format_color_range_endpoints(
            self.config.color_range, self.config.use_log_scale
        )
        ticks = compute_color_ticks(vmin, vmax, scale=self.config.use_log_scale, n=5)
        if not ticks:
            self.config.color_ticks = []
            return
        # The colorbar image is always rendered from the linear LUT, so
        # sample contrast colors using the linear color_range.
        ctf = self.lut.GetClientSideObject()
        rgb = [0.0, 0.0, 0.0]
        cr_min, cr_max = float(vmin), float(vmax)
        cr_range = cr_max - cr_min
        if cr_range == 0:
            self.config.color_ticks = []
            return
        for tick in ticks:
            t = tick["position"] / 100.0
            value = cr_min + t * cr_range
            ctf.GetColor(value, rgb)
            tick["color"] = tick_contrast_color(rgb[0], rgb[1], rgb[2])
        self.config.color_ticks = ticks

    def _build_ui(self):
        with DivLayout(
            self.server, template_name=self.name, connect_parent=False, classes="h-100"
        ) as self.ui:
            self.ui.root.classes = "h-100"
            with v3.VCard(
                variant="tonal",
                style=(
                    "active_layout !== 'auto_layout' ? `height: calc(100% - ${top_padding}px;` : 'overflow-hidden'",
                ),
                tile=("active_layout !== 'auto_layout'",),
            ):
                with v3.VRow(
                    dense=True,
                    classes="ma-0 pa-0 bg-white text-black d-flex align-center border-b-thin",
                    style="flex-wrap: nowrap;",
                ):
                    tview.create_size_menu(self.name, self.config)
                    with self.config.provide_as("config"):
                        with html.Div(
                            "{{ config.label }}",
                            classes="text-subtitle-2 pr-2 text-truncate",
                            style="user-select: none; min-width: 0;",
                            title=("config.label",),
                        ):
                            with v3.VMenu(activator="parent"):
                                with v3.VList(
                                    density="compact", style="max-height: 40vh;"
                                ):
                                    with self.config.provide_as("config"):
                                        v3.VListItem(
                                            subtitle=("name",),
                                            v_for="name, idx in config.swap_group",
                                            key="name",
                                            click=(
                                                self.ctrl.swap_variables,
                                                "[config.variable, name]",
                                            ),
                                        )

                    v3.VIcon(
                        "mdi-lock-outline",
                        size="x-small",
                        v_show=("lock_views", False),
                        style="transform: scale(0.75);",
                    )

                    v3.VSpacer()
                    html.Div(
                        "t = {{ time_idx }}",
                        classes="text-caption px-1 text-no-wrap",
                        v_if="timestamps.length > 1",
                    )
                    if self.variable_type == "m":
                        html.Div(
                            "[k = {{ midpoint_idx }}]",
                            classes="text-caption px-1 text-no-wrap",
                            v_if="midpoints.length > 1",
                        )
                    if self.variable_type == "i":
                        html.Div(
                            "[k = {{ interface_idx }}]",
                            classes="text-caption px-1 text-no-wrap",
                            v_if="interfaces.length > 1",
                        )
                    v3.VSpacer()
                    with self.config.provide_as("config"):
                        html.Div(
                            "avg = {{"
                            "fields_avgs[config.variable]?.toExponential(2)"
                            " || fields_avgs[config.base_variable]?.toExponential(2)"
                            " || 'N/A'"
                            "}}",
                            classes="text-caption px-1 text-no-wrap",
                        )

                with html.Div(
                    style=(
                        """
                        {
                            aspectRatio: active_layout === 'auto_layout' ? aspect_ratio : null,
                            height: active_layout !== 'auto_layout' ? 'calc(100% - 2.4rem)' : null,
                            pointerEvents: lock_views ? 'none': null,
                        }
                        """,
                    ),
                ):
                    rca.ImageRegion(
                        enable_interaction=True,
                        bounds=(self._bounds_key, (0, 0, 1, 1)),
                        size=(self.update_size, "[$event]"),
                    )

                tview.create_bottom_bar(self.config, self.update_color_preset)


class ViewManager(TrameComponent):
    def __init__(self, server, source):
        super().__init__(server)
        self.use_image_stream = True
        self._camera = vtkCamera(parallel_projection=1)
        self._render_window = vtkRenderWindow()
        self._render_window.OffScreenRenderingOn()
        self._style = vtkPVInteractorStyle()
        self._style.AddManipulator(
            vtkPVTrackballZoom(
                button=3,
                shift=0,
                control=0,
            )
        )
        self._style.AddManipulator(
            vtkPVTrackballZoom(
                button=1,
                shift=1,
                control=0,
            )
        )
        self._style.AddManipulator(
            vtkTrackballPan(
                button=1,
                shift=0,
                control=0,
            )
        )
        self._render_window_interactor = vtkRenderWindowInteractor(
            interactor_style=self._style
        )
        self._render_window_interactor.SetRenderWindow(self._render_window)

        self.loop = asyncio.get_event_loop()
        self.layout_dirty = True
        self.pending_reset_camera = 1
        self.pending_render = False
        self.source = source
        self._var2view = {}
        self._camera_sync_in_progress = False
        self._last_vars = {}
        self._active_configs = {}

        rca.initialize(self.server)

        self.state.luts_normal = [
            {"name": k, "url": v["normal"], "safe": k in COLOR_BLIND_SAFE}
            for k, v in COLORBAR_CACHE.items()
        ]
        self.state.luts_inverted = [
            {"name": k, "url": v["inverted"], "safe": k in COLOR_BLIND_SAFE}
            for k, v in COLORBAR_CACHE.items()
        ]

        # Sort lists
        self.state.luts_normal.sort(key=lut_name)
        self.state.luts_inverted.sort(key=lut_name)

    def refresh_ui(self, **_):
        for view in self._var2view.values():
            view._build_ui()

    def _active_views(self):
        if self._active_configs:
            return [self._var2view[name] for name in self._active_configs]
        return list(self._var2view.values())

    def _resolve_view_spec(self, view_spec):
        if not isinstance(view_spec, str):
            return view_spec

        return (
            self.source.data_reader.get_array_metadata(view_spec)
            or next(
                iter(
                    self.source.data_reader.get_view_specs(
                        view_spec,
                        self.state.comparison_mode,
                        self.state.comparison_type,
                        self.state.selected_columns,
                    )
                ),
                None,
            )
            or {
                "array_name": view_spec,
                "base_variable": view_spec,
                "role": "control",
                "label": view_spec,
                "comparison_mode": self.state.comparison_mode,
            }
        )

    def reset_camera(self, render=True):
        if self.layout_dirty or not self._last_vars:
            self.pending_reset_camera = 1
            return

        view_to_reset = None

        active_layout = self.state.active_layout or ""
        if active_layout.startswith("view_"):
            for view in self._var2view.values():
                if view.name == active_layout:
                    view_to_reset = view
                    break

        if not view_to_reset:
            for var_type, var_names in self._last_vars.items():
                for var_name in var_names:
                    for view_spec in self.get_view_specs(var_name):
                        view_to_reset = self.get_view(view_spec, var_type)
                        if view_to_reset:
                            break
                    if view_to_reset:
                        break

                if view_to_reset:
                    break

        if view_to_reset:
            view_to_reset.reset_camera()
            self.pending_reset_camera = 0
        else:
            self.pending_reset_camera = 1

        if render and view_to_reset:
            self.render()

    def get_active_camera(self):
        if not self._var2view:
            return None
        camera = self._camera
        return {
            "position": camera.GetPosition(),
            "focal_point": camera.GetFocalPoint(),
            "view_up": camera.GetViewUp(),
            "parallel_projection": camera.GetParallelProjection(),
            "parallel_scale": camera.GetParallelScale(),
            "view_angle": camera.GetViewAngle(),
            "clipping_range": camera.GetClippingRange(),
        }

    def sync_active_views_to_camera(self, camera_state):
        if not camera_state:
            return
        if self._camera_sync_in_progress:
            return
        self._camera_sync_in_progress = True

        try:
            self._camera.SetPosition(*camera_state["position"])
            self._camera.SetFocalPoint(*camera_state["focal_point"])
            self._camera.SetViewUp(*camera_state["view_up"])
            self._camera.SetParallelProjection(camera_state["parallel_projection"])
            self._camera.SetParallelScale(camera_state["parallel_scale"])
            self._camera.SetViewAngle(camera_state["view_angle"])
            self._camera.SetClippingRange(*camera_state["clipping_range"])
            self.render()
        finally:
            self._camera_sync_in_progress = False

    @controller.set("size_update")
    def on_size_update(self):
        if not self.layout_dirty or not self.pending_render:
            self.pending_render = True
            self.loop.call_later(0.1, self.render)
        self.layout_dirty = True

    def render(self):
        if self.layout_dirty:
            self.compute_layout()

        if self.pending_reset_camera:
            self.reset_camera(False)

        if self.ctx.view:
            self.ctx.view.update()
            self.pending_render = False

    def update_color_range(self):
        for view in self._active_views():
            view.update_color_range()
        self.render()

    def refresh_pipeline_inputs(self):
        for view in self._var2view.values():
            view._connect_pipeline_input()

    def refresh_view_specs(self, variables=None):
        if variables is None:
            variables = self._last_vars

        for var_type, var_names in variables.items():
            for var_name in var_names:
                for view_spec in self.get_view_specs(var_name):
                    view = self._var2view.get(view_spec["array_name"])
                    if view is not None:
                        view.update_view_spec(view_spec)

    def reset_view_orders(self, variables=None):
        if variables is None:
            variables = self._last_vars
        if not variables:
            return

        for _, var_names in variables.items():
            for var_name in var_names:
                for view_spec in self.get_view_specs(var_name):
                    view = self._var2view.get(view_spec["array_name"])
                    if view is not None:
                        view.config.order = 0

    def get_view(self, view_spec, variable_type):
        view_spec = self._resolve_view_spec(view_spec)
        array_name = view_spec["array_name"]
        view = self._var2view.get(array_name)
        if view is None:
            view = self._var2view.setdefault(
                array_name,
                VariableView(
                    self.server,
                    self.source,
                    view_spec,
                    variable_type,
                    self._camera,
                ),
            )
        else:
            view.update_view_spec(view_spec)

        return view

    def get_view_specs(self, variable_name):
        return self.source.data_reader.get_view_specs(
            variable_name,
            self.state.comparison_mode,
            self.state.comparison_type,
            self.state.selected_columns,
        )

    def compute_layout(self, variables=None):
        if variables is None:
            variables = self._last_vars

        if not variables:
            return

        self.layout_dirty = False

        views = []
        view_size = [0, 0]
        fullscreen_view = None
        fullscreen_view_name = self.state.active_layout or ""

        for var_type, var_names in variables.items():
            for var_name in var_names:
                for view_spec in self.get_view_specs(var_name):
                    view = self.get_view(view_spec, var_type)

                    if view.name == fullscreen_view_name:
                        fullscreen_view = view
                        break
                    if view.size[1]:
                        views.append(view)
                        view_size[0] = max(view_size[0], view.size[0])
                        view_size[1] = max(view_size[1], view.size[1])
                    else:
                        self.layout_dirty = True

                if fullscreen_view:
                    break

            if fullscreen_view:
                break

        if fullscreen_view:
            view_size = fullscreen_view.size
            views = [fullscreen_view]
        else:
            views = [
                view
                for index, view in sorted(
                    enumerate(views),
                    key=lambda item: (
                        item[1].config.order or len(views) + item[0],
                        item[0],
                    ),
                )
            ]

        size = len(views)
        if size == 0:
            return

        width_count = math.ceil(math.sqrt(size))
        height_count = math.ceil(size / width_count)
        full_size = [
            view_size[0] * width_count,
            view_size[1] * height_count,
        ]

        self._render_window.SetSize(*full_size)
        renderers = list(self._render_window.GetRenderers())
        for renderer in renderers:
            self._render_window.RemoveRenderer(renderer)

        dx = 1.0 / width_count
        dy = 1.0 / height_count
        for index, view in enumerate(views):
            x_index = index % width_count
            y_index = int(index / width_count)
            bounds = (
                x_index * dx,
                y_index * dy,
                (x_index + 1) * dx,
                (y_index + 1) * dy,
            )
            view.bounds = bounds
            self._render_window.AddRenderer(view.renderer)

    @controller.set("swap_variables")
    def swap_variable(self, variable_a, variable_b):
        config_a = self._active_configs[variable_a]
        config_b = self._active_configs[variable_b]
        config_a.order, config_b.order = config_b.order, config_a.order
        config_a.size, config_b.size = config_b.size, config_a.size
        config_a.offset, config_b.offset = config_b.offset, config_a.offset
        config_a.break_row, config_b.break_row = config_b.break_row, config_a.break_row

    def apply_size(self, n_cols):
        if not self._last_vars:
            return

        if n_cols == 0:
            # Auto size views based on the number of comparison panels being shown.
            if self.state.layout_grouped:
                for var_type, var_names in self._last_vars.items():
                    for var_name in var_names:
                        view_specs = self.get_view_specs(var_name)
                        if not view_specs:
                            continue
                        size = auto_size_to_col(len(view_specs))
                        for view_spec in view_specs:
                            self.get_view(view_spec, var_type).config.size = size
            else:
                size = auto_size_to_col(len(self._active_configs))
                for config in self._active_configs.values():
                    config.size = size
        else:
            # Apply a uniform size to all active views.
            for config in self._active_configs.values():
                config.size = COL_SIZE_LOOKUP[n_cols]

    def build_auto_layout(self, variables=None):
        if variables is None:
            variables = self._last_vars

        self._last_vars = variables
        self.compute_layout()

        # Create UI based on the selected variables.
        self.state.swap_groups = {}
        # Build a lookup from variable type to the matching group border color.
        type_to_color = {vt["name"]: vt["color"] for vt in self.state.variable_types}
        with DivLayout(self.server, template_name="auto_layout") as self.ui:
            if self.state.layout_grouped:
                with v3.VCol(classes="pa-1"):
                    for var_type, var_names in variables.items():
                        for var_name in var_names:
                            view_specs = self.get_view_specs(var_name)
                            if not view_specs:
                                continue

                            type_name = (
                                ", ".join(var_type)
                                if isinstance(var_type, (list, tuple))
                                else str(var_type)
                            )
                            border_color = type_to_color.get(type_name, "primary")
                            with v3.VAlert(
                                border="start",
                                classes="pr-1 py-1 pl-3 mb-6",
                                variant="flat",
                                border_color=border_color,
                            ):
                                html.Div(
                                    var_name,
                                    classes="text-subtitle-2 font-weight-medium mb-1",
                                )
                                with v3.VRow(dense=True):
                                    if self.state.comparison_mode == "multi-sim":
                                        views_per_row = min(len(view_specs), 3)
                                    else:
                                        views_per_row = max(1, len(view_specs))
                                    group_cols = max(1, math.floor(12 / views_per_row))
                                    group_names = [
                                        view_spec["array_name"]
                                        for view_spec in view_specs
                                    ]
                                    for view_spec in view_specs:
                                        view = self.get_view(view_spec, var_type)
                                        view.config.swap_group = sorted(
                                            [
                                                name
                                                for name in group_names
                                                if name != view_spec["array_name"]
                                            ]
                                        )
                                        with view.config.provide_as("config"):
                                            v3.VCol(
                                                v_if="config.break_row",
                                                cols=12,
                                                classes="pa-0",
                                                style=("`order: ${config.order};`",),
                                            )
                                            # For flow handling
                                            with v3.Template(v_if="!config.size"):
                                                v3.VCol(
                                                    v_for="i in config.offset",
                                                    key="i",
                                                    style=("{ order: config.order }",),
                                                )
                                            with v3.VCol(
                                                offset=("config.offset * config.size",),
                                                cols=group_cols,
                                                style=("`order: ${config.order};`",),
                                            ):
                                                client.ServerTemplate(name=view.name)
            else:
                all_names = []
                for var_name_list in variables.values():
                    for var_name in var_name_list:
                        all_names.extend(
                            [
                                view_spec["array_name"]
                                for view_spec in self.get_view_specs(var_name)
                            ]
                        )
                with v3.VRow(dense=True, classes="pa-2"):
                    for var_type, var_names in variables.items():
                        for name in var_names:
                            for view_spec in self.get_view_specs(name):
                                view = self.get_view(view_spec, var_type)
                                view.config.swap_group = sorted(
                                    [
                                        array_name
                                        for array_name in all_names
                                        if array_name != view_spec["array_name"]
                                    ]
                                )
                                with view.config.provide_as("config"):
                                    v3.VCol(
                                        v_if="config.break_row",
                                        cols=12,
                                        classes="pa-0",
                                        style=("`order: ${config.order};`",),
                                    )

                                    # For flow handling
                                    with v3.Template(v_if="!config.size"):
                                        v3.VCol(
                                            v_for="i in config.offset",
                                            key="i",
                                            style=("{ order: config.order }",),
                                        )
                                    with v3.VCol(
                                        offset=(
                                            "config.size ? config.offset * config.size : 0",
                                        ),
                                        cols=("config.size",),
                                        style=("`order: ${config.order};`",),
                                    ):
                                        client.ServerTemplate(name=view.name)

        # Assign any missing order.
        self._active_configs = {}
        existed_order = set()
        order_max = 0
        orders_to_update = []
        for var_type, var_names in variables.items():
            for var_name in var_names:
                for view_spec in self.get_view_specs(var_name):
                    config = self.get_view(view_spec, var_type).config
                    name = view_spec["array_name"]
                    self._active_configs[name] = config
                    if config.order:
                        if config.order in existed_order:
                            config.order = 0
                            orders_to_update.append(config)
                            continue
                        order_max = max(order_max, config.order)
                        existed_order.add(config.order)
                    else:
                        orders_to_update.append(config)

        next_order = order_max + 1
        for config in orders_to_update:
            config.order = next_order
            next_order += 1

        self.layout_dirty = True
        self.compute_layout()
