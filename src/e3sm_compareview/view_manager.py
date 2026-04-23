import math

import numpy as np

from trame.app import TrameComponent, dataclass
from trame.ui.html import DivLayout
from trame.widgets import paraview as pvw, vuetify3 as v3, client, html
from trame.decorators import controller

from paraview import simple

from e3sm_compareview.components import view as tview
from e3sm_quickview.presets import COLOR_BLIND_SAFE
from e3sm_quickview.utils.color import COLORBAR_CACHE, lut_to_img


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


def get_nice_ticks(vmin, vmax, n, scale="linear"):
    """Compute nicely spaced tick values for a given range and scale."""

    def snap(val):
        if np.isclose(val, 0, atol=1e-12):
            return 0.0
        sign = np.sign(val)
        val_abs = abs(val)
        mag = 10 ** np.floor(np.log10(val_abs))
        residual = val_abs / mag
        nice_steps = np.array([1.0, 2.0, 5.0, 10.0])
        best_step = nice_steps[np.abs(nice_steps - residual).argmin()]
        return sign * best_step * mag

    if scale == "linear":
        raw_ticks = np.linspace(vmin, vmax, n)
    elif scale == "log":
        safe_vmin = max(vmin, 1e-15)
        safe_vmax = max(vmax, 1e-14)
        start_exp = int(np.floor(np.log10(safe_vmin)))
        stop_exp = int(np.ceil(np.log10(safe_vmax)))
        powers = [
            10.0**e
            for e in range(start_exp, stop_exp + 1)
            if safe_vmin <= 10.0**e <= safe_vmax
        ]
        if len(powers) < 2:
            raw_ticks = np.geomspace(safe_vmin, safe_vmax, n)
        else:
            raw_ticks = np.array(powers)
    elif scale == "symlog":

        def transform(x, threshold):
            return np.sign(x) * np.log10(np.abs(x) / threshold + 1)

        def inverse(y, threshold):
            return np.sign(y) * threshold * (10 ** np.abs(y) - 1)

        linthresh = max(abs(vmin), abs(vmax)) * 1e-2
        if linthresh == 0:
            linthresh = 1.0
        t_min, t_max = transform(vmin, linthresh), transform(vmax, linthresh)
        t_ticks = np.linspace(t_min, t_max, n)
        raw_ticks = inverse(t_ticks, linthresh)
    else:
        raw_ticks = np.linspace(vmin, vmax, n)

    nice_ticks = np.array([snap(t) for t in raw_ticks])

    if vmin <= 0 <= vmax and scale != "log":
        idx = np.abs(nice_ticks).argmin()
        nice_ticks[idx] = 0.0

    return np.unique(np.sort(nice_ticks))


def format_tick(val):
    """Format a tick value for compact colorbar display."""
    if np.isclose(val, 0, atol=1e-12):
        return "0"

    val_abs = abs(val)
    log10 = np.log10(val_abs)

    if np.isclose(log10, np.round(log10), atol=1e-12):
        exponent = int(np.round(log10))
        sign = "-" if val < 0 else ""
        if exponent == 0:
            return f"{sign}1"
        if exponent == 1:
            return f"{sign}10"
        return f"{sign}10^{exponent}"

    if val_abs >= 1000 or val_abs <= 0.01:
        return f"{val:.1e}"
    return f"{int(val) if val == int(val) else val:.1f}"


def tick_contrast_color(r, g, b):
    """Return '#fff' or '#000' for best contrast against the given RGB color."""
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000" if luminance > 0.45 else "#fff"


def compute_color_ticks(vmin, vmax, scale="linear", n=5, min_gap=7, edge_margin=3):
    """Compute display ticks for the LUT preview colorbar."""
    if vmin >= vmax:
        return []

    raw_n = n if scale == "linear" else n * 2
    ticks = get_nice_ticks(vmin, vmax, raw_n, scale)
    data_range = vmax - vmin

    candidates = []
    has_zero = False
    for tick_value in ticks:
        val = float(tick_value)
        pos = (val - vmin) / data_range * 100
        if edge_margin <= pos <= (100 - edge_margin):
            is_zero = np.isclose(val, 0, atol=1e-12)
            if is_zero:
                has_zero = True
            candidates.append(
                {
                    "position": round(pos, 2),
                    "label": format_tick(val),
                    "priority": is_zero,
                }
            )

    if not has_zero and scale != "log":
        zero_pos = (0.0 - vmin) / data_range * 100
        if 0 <= zero_pos <= 100:
            tick = {"position": round(zero_pos, 2), "label": "0", "priority": True}
            inserted = False
            for i, candidate in enumerate(candidates):
                if tick["position"] <= candidate["position"]:
                    candidates.insert(i, tick)
                    inserted = True
                    break
            if not inserted:
                candidates.append(tick)

    result = []
    for tick in candidates:
        is_priority = tick.get("priority", False)
        if is_priority:
            if result and (tick["position"] - result[-1]["position"]) < min_gap:
                if not result[-1].get("priority", False):
                    result.pop()
            result.append(tick)
        elif not result or (tick["position"] - result[-1]["position"]) >= min_gap:
            result.append(tick)

    for tick in result:
        tick.pop("priority", None)
    return result


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


class VariableView(TrameComponent):
    def __init__(self, server, source, view_spec, variable_type):
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

        if self.role in ("control", "test", "source"):
            self.config.preset = "navia"
        elif self.role == "diff":
            self.config.preset = "Cool to Warm (Extended)"
        elif self.role in ("comp1", "comp2"):
            self.config.preset = "bam"
            self.config.invert = True

        self.view = simple.CreateRenderView()
        self.view.GetRenderWindow().SetOffScreenRendering(True)
        self.view.InteractionMode = "2D"
        self.view.OrientationAxesVisibility = 0
        self.view.UseColorPaletteForBackground = 0
        self.view.BackgroundColorMode = "Single Color"
        self.view.Background = [1, 1, 1]
        self.view.Background2 = [1, 1, 1]
        self.view.CameraParallelProjection = 1
        self.view.Size = 0  # make the interactive widget non responsive
        self.representation = simple.Show(
            proxy=source.views["atmosphere_data"],
            view=self.view,
        )

        # Lookup table color management
        simple.ColorBy(self.representation, ("CELLS", self.array_name))
        self.lut = simple.GetColorTransferFunction(self.array_name)
        self.lut.NanOpacity = 0.0

        self.view.ResetActiveCameraToNegativeZ()
        self.view.ResetCamera(True, 0.9)
        self.disable_render = False

        # Add annotations to the view
        # - continents
        globe = source.views["continents"]
        rep_globe = simple.Show(globe, self.view)
        simple.ColorBy(rep_globe, None)
        rep_globe.SetRepresentationType("Wireframe")
        rep_globe.RenderLinesAsTubes = 1
        rep_globe.LineWidth = 1.0
        rep_globe.AmbientColor = [0.67, 0.67, 0.67]
        rep_globe.DiffuseColor = [0.67, 0.67, 0.67]
        self.rep_globe = rep_globe

        # - gridlines
        grid_lines = source.views["grid_lines"]
        rep_grid = simple.Show(grid_lines, self.view)
        rep_grid.SetRepresentationType("Wireframe")
        rep_grid.AmbientColor = [0.67, 0.67, 0.67]
        rep_grid.DiffuseColor = [0.67, 0.67, 0.67]
        rep_grid.Opacity = 0.4
        self.rep_grid = rep_grid

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

    def update_view_spec(self, view_spec):
        self.view_spec = view_spec
        self.base_variable = view_spec["base_variable"]
        self.role = view_spec["role"]
        self.comparison_mode = view_spec.get("comparison_mode", "multi-sim")
        self.comparison_type = view_spec.get("comparison_type", "diff")
        self.display_label = view_spec["label"]
        self.config.base_variable = self.base_variable
        self.config.label = self.display_label

    def render(self):
        if self.disable_render or not self.ctx.has(self.name):
            return
        self.ctx[self.name].update()

    def set_camera_modified(self, fn):
        self._observer = self.camera.AddObserver("ModifiedEvent", fn)

    @property
    def camera(self):
        return self.view.GetActiveCamera()

    def reset_camera(self):
        self.view.InteractionMode = "2D"
        self.view.ResetActiveCameraToNegativeZ()
        self.view.ResetCamera(True, 0.9)
        self.ctx[self.name].update()

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

        # Apply linear first, then scale transform.
        self._apply_linear_to_lut(invert)
        self.lut.RescaleTransferFunction(*self.config.color_range)

        if scale_mode == "log":
            self._apply_log_to_lut()
        elif scale_mode == "symlog":
            self._apply_symlog_to_lut()

        if n_colors is not None:
            self.lut.NumberOfTableValues = n_colors

        ctf = self.lut.GetClientSideObject()
        self.config.effective_color_range = ctf.GetRange()
        self.config.lut_img = lut_to_img(self.lut)
        self._compute_ticks()

        self.render()

    def _apply_linear_to_lut(self, invert=False):
        self.lut.UseLogScale = 0
        self.lut.ApplyPreset(self.config.preset, True)
        if invert:
            self.lut.InvertTransferFunction()

    def _apply_log_to_lut(self):
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
            safe_abs = np.maximum(abs_x, linthresh)
            return np.where(
                abs_x <= linthresh,
                x * linscale_adj,
                np.sign(x)
                * linthresh
                * (linscale_adj + np.log(safe_abs / linthresh) / log_base),
            )

        rgb = [0.0, 0.0, 0.0]
        s_min = symlog(x_min)
        s_max = symlog(x_max)
        s_range = s_max - s_min
        if s_range == 0:
            return

        new_rgb_points = []
        for i in range(n_samples):
            t = i / (n_samples - 1)
            x_data = x_min + t * data_range
            s_val = symlog(x_data)
            s_t = (s_val - s_min) / s_range
            x_lookup = x_min + s_t * data_range
            ctf.GetColor(x_lookup, rgb)
            new_rgb_points.extend(
                [float(x_data), float(rgb[0]), float(rgb[1]), float(rgb[2])]
            )

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

    def _get_multi_sim_default_range(self):
        data_info = self.source.views["atmosphere_data"].GetCellDataInformation()
        if self.comparison_type == "source":
            ranges = []
            for view_spec in self.source.get_view_specs(
                self.base_variable,
                "multi-sim",
                "source",
            ):
                data_array = data_info.GetArray(view_spec["array_name"])
                if not data_array:
                    continue
                data_range = data_array.GetRange()
                if self._is_finite_range(data_range):
                    ranges.append(data_range)

            if ranges:
                return (
                    min(data_range[0] for data_range in ranges),
                    max(data_range[1] for data_range in ranges),
                )
            return None

        if self.role != "control":
            max_abs = None
            for view_spec in self.source.get_view_specs(
                self.base_variable,
                "multi-sim",
                self.comparison_type,
            ):
                if view_spec["role"] == "control":
                    continue
                data_array = data_info.GetArray(view_spec["array_name"])
                if not data_array:
                    continue
                data_range = data_array.GetRange()
                if not self._is_finite_range(data_range):
                    continue
                candidate = max(abs(data_range[0]), abs(data_range[1]))
                max_abs = candidate if max_abs is None else max(max_abs, candidate)
            if max_abs is not None:
                return (-max_abs, max_abs)
            return None

        data_array = data_info.GetArray(self.array_name)
        if not data_array:
            return None

        data_range = data_array.GetRange()
        if self._is_finite_range(data_range):
            return data_range
        return None

    def _get_two_sim_default_range(self):
        data_info = self.source.views["atmosphere_data"].GetCellDataInformation()
        two_sim_specs = self.source.get_view_specs(
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
                ctrl_array = data_info.GetArray(ctrl_spec["array_name"])
                test_array = data_info.GetArray(test_spec["array_name"])
                if ctrl_array and test_array:
                    ctrl_range = ctrl_array.GetRange()
                    test_range = test_array.GetRange()
                    if self._is_finite_range(ctrl_range) and self._is_finite_range(
                        test_range
                    ):
                        return (
                            min(ctrl_range[0], test_range[0]),
                            max(ctrl_range[1], test_range[1]),
                        )

        if self.role == "diff":
            diff_spec = spec_by_role.get("diff")
            if diff_spec:
                diff_array = data_info.GetArray(diff_spec["array_name"])
                if diff_array:
                    diff_range = diff_array.GetRange()
                    if self._is_finite_range(diff_range):
                        return self._max_abs_from_ranges([diff_range])

        if self.role in ("comp1", "comp2"):
            comp_ranges = []
            for role in ("comp1", "comp2"):
                comp_spec = spec_by_role.get(role)
                if not comp_spec:
                    continue
                comp_array = data_info.GetArray(comp_spec["array_name"])
                if not comp_array:
                    continue
                comp_range = comp_array.GetRange()
                if self._is_finite_range(comp_range):
                    comp_ranges.append(comp_range)

            centered = self._max_abs_from_ranges(comp_ranges)
            if centered is not None:
                return centered

        data_array = data_info.GetArray(self.array_name)
        if data_array:
            data_range = data_array.GetRange()
            if self._is_finite_range(data_range):
                return data_range

        return None

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
        vmin, vmax = self.config.effective_color_range
        ticks = compute_color_ticks(vmin, vmax, scale=self.config.use_log_scale, n=5)

        rgb_points = self.lut.RGBPoints
        if len(rgb_points) < 4:
            self.config.color_ticks = []
            return

        ctf = self.lut.GetClientSideObject()
        rgb = [0.0, 0.0, 0.0]
        img_min = rgb_points[0]
        img_max = rgb_points[-4]
        img_range = img_max - img_min
        if img_range == 0:
            self.config.color_ticks = []
            return

        for tick in ticks:
            t = tick["position"] / 100.0
            value = img_min + t * img_range
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
                    pvw.VtkRemoteView(
                        self.view, interactive_ratio=1, ctx_name=self.name
                    )

                tview.create_bottom_bar(self.config, self.update_color_preset)


class ViewManager(TrameComponent):
    def __init__(self, server, source):
        super().__init__(server)
        self.source = source
        self._var2view = {}
        self._camera_sync_in_progress = False
        self._last_vars = {}
        self._active_configs = {}

        pvw.initialize(self.server)

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
            self.source.get_array_metadata(view_spec)
            or next(
                iter(
                    self.source.get_view_specs(
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

    def reset_camera(self):
        views = self._active_views()
        for view in views:
            view.disable_render = True

        for view in views:
            view.reset_camera()

        for view in views:
            view.disable_render = False

    def get_active_camera(self):
        views = self._active_views()
        if not views:
            return None
        camera = views[0].camera
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
            for var_view in self._active_views():
                cam = var_view.camera
                cam.SetPosition(*camera_state["position"])
                cam.SetFocalPoint(*camera_state["focal_point"])
                cam.SetViewUp(*camera_state["view_up"])
                cam.SetParallelProjection(camera_state["parallel_projection"])
                cam.SetParallelScale(camera_state["parallel_scale"])
                cam.SetViewAngle(camera_state["view_angle"])
                cam.SetClippingRange(*camera_state["clipping_range"])
                var_view.render()
        finally:
            self._camera_sync_in_progress = False

    def render(self):
        for view in self._active_views():
            view.render()

    def update_color_range(self):
        for view in self._active_views():
            view.update_color_range()

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
                VariableView(self.server, self.source, view_spec, variable_type),
            )
            view.set_camera_modified(self.sync_camera)
        else:
            view.update_view_spec(view_spec)

        return view

    def get_view_specs(self, variable_name):
        return self.source.get_view_specs(
            variable_name,
            self.state.comparison_mode,
            self.state.comparison_type,
            self.state.selected_columns,
        )

    def sync_camera(self, camera, *_):
        if self._camera_sync_in_progress:
            return
        self._camera_sync_in_progress = True

        for var_view in self._active_views():
            cam = var_view.camera
            if cam is camera:
                continue
            cam.DeepCopy(camera)
            var_view.render()

        self._camera_sync_in_progress = False

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
