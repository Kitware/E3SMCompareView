import math

import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
from e3sm_quickview.components.view import create_size_menu
from trame.app import TrameComponent, dataclass
from trame.dataclasses.colormaps import ColormapConfig
from trame.ui.html import DivLayout
from trame.widgets import colormaps, html, rca
from trame.widgets import vuetify3 as v3
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
)


class ViewConfiguration(dataclass.StateDataModel):
    variable: str = dataclass.Sync(str)
    base_variable: str = dataclass.Sync(str, "")
    label: str = dataclass.Sync(str, "")
    order: int = dataclass.Sync(int, 0)
    size: int = dataclass.Sync(int, 4)
    offset: int = dataclass.Sync(int, 0)
    break_row: bool = dataclass.Sync(bool, False)
    swap_group: list[dict[str, str]] = dataclass.Sync(list[dict[str, str]], list)


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
        self.colormap = ColormapConfig(
            server,
            mapper=self.mapper,
            data_array_fn=lambda: self._get_data_array(self.array_name),
        ).set_data_array(
            self.array_name, lambda: self._get_data_array(self.array_name), "cell"
        )
        self.colormap.watch(["mapper_change"], lambda *_: self.render())

        if self.role in ("diff", "comp1", "comp2"):
            self.colormap.diverging = True

        self._connect_pipeline_input()

        # Add shared annotation actors
        continents_actor = source.continent.actor
        if continents_actor is not None:
            self.renderer.AddActor(continents_actor)
        grid_lines_actor = source.grid_lines.actor
        if grid_lines_actor is not None:
            self.renderer.AddActor(grid_lines_actor)

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

    def _build_ui(self):
        with DivLayout(
            self.server, template_name=self.name, connect_parent=False, classes="h-100"
        ) as self.ui:
            self.ui.root.classes = "h-100"
            with v3.VCard(
                variant="tonal",
                style=(
                    "active_layout !== 'auto_layout' ? `height: calc(100% - ${toolbar_size?.size?.height || 0}px;` : 'overflow-hidden'",
                ),
                tile=("active_layout !== 'auto_layout'",),
            ):
                with v3.VRow(
                    dense=True,
                    classes="ma-0 pa-0 bg-white text-black d-flex align-center border-b-thin",
                    style="flex-wrap: nowrap;",
                ):
                    create_size_menu(self.name, self.config)
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
                                            title=("swap.label || swap.name",),
                                            v_for="swap, idx in config.swap_group",
                                            key="swap.name",
                                            click=(
                                                self.ctrl.swap_variables,
                                                "[config.variable, swap.name]",
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
                            aspectRatio: active_layout === 'auto_layout' ? 1/aspect_ratio : null,
                            height: active_layout !== 'auto_layout' ? 'calc(100% - 2.4rem)' : null,
                            pointerEvents: lock_views ? 'none': null,
                        }
                        """,
                    ),
                ):
                    rca.ImageRegion(
                        enable_interaction=False,
                        bounds=(self._bounds_key, (0, 0, 1, 1)),
                        size=(self.update_size, "[$event]"),
                    )

                with self.colormap.provide_as(self.name):
                    colormaps.HorizontalScalarBar(self.name, popup_location="top")
