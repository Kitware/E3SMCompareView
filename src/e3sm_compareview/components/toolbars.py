import asyncio

from trame.app import asynchronous
from trame.decorators import change
from trame.widgets import html
from trame.widgets import vuetify3 as v3

from e3sm_compareview.comparison import (
    COMPARISON_TYPES,
    MULTI_SIM_COMPARISON_LABELS,
    TWO_SIM_COLUMN_LABELS,
)
from e3sm_quickview.components.toolbars import DataSelection as DataSelection
from e3sm_quickview.components.toolbars import Layout as Layout
from e3sm_quickview.utils import js

DENSITY = {
    "adjust-layout": "compact",
    "simulation-controls": "compact",
    "adjust-databounds": "default",
    "select-slice-time": "default",
    "animation-controls": "compact",
}

DEFAULT_STYLES = {
    "color": "white",
    "classes": "border-b-thin",
}

def to_kwargs(value):
    return {
        "v_show": js.is_active(value),
        "density": DENSITY[value],
        **DEFAULT_STYLES,
    }


class Cropping(v3.VToolbar):
    def __init__(self):
        super().__init__(**to_kwargs("adjust-databounds"))

        with self:
            with v3.VTooltip(
                text=(
                    "crop_slider_edit ? 'Toggle to text edit' : 'Toggle to slider edit'",
                ),
            ):
                with v3.Template(v_slot_activator="{ props }"):
                    v3.VIcon(
                        "mdi-web",
                        v_bind="props",
                        classes="pl-6 opacity-50",
                        click="crop_slider_edit = !crop_slider_edit",
                    )
            with v3.VRow(
                classes="ma-0 px-2 align-center", v_if=("crop_slider_edit", True)
            ):
                with v3.VCol(cols=6):
                    with v3.VRow(classes="mx-2 my-0"):
                        v3.VLabel(
                            "Longitude",
                            classes="text-subtitle-2",
                        )
                        v3.VSpacer()
                        v3.VLabel(
                            "{{ crop_longitude }}",
                            classes="text-body-2",
                        )
                    v3.VRangeSlider(
                        v_model=("crop_longitude", [-180, 180]),
                        min=-180,
                        max=180,
                        step=1,
                        density="compact",
                        hide_details=True,
                    )
                with v3.VCol(cols=6):
                    with v3.VRow(classes="mx-2 my-0"):
                        v3.VLabel(
                            "Latitude",
                            classes="text-subtitle-2",
                        )
                        v3.VSpacer()
                        v3.VLabel(
                            "{{ crop_latitude }}",
                            classes="text-body-2",
                        )
                    v3.VRangeSlider(
                        v_model=("crop_latitude", [-90, 90]),
                        min=-90,
                        max=90,
                        step=1,
                        density="compact",
                        hide_details=True,
                    )
            with v3.VRow(classes="ma-0 pl-6 pr-2 align-center ga-4", v_else=True):
                v3.VNumberInput(
                    label="Longitude (min)",
                    v_model=("crop_longitude_min", -180),
                    min=[-180],
                    max=("crop_longitude_max", 180),
                    step=[1],
                    hide_details=True,
                    density="comfortable",
                    variant="plain",
                    flat=True,
                    control_variant="stacked",
                )
                v3.VNumberInput(
                    label="Longitude (max)",
                    v_model=("crop_longitude_max", 180),
                    min=("crop_longitude_min", -180),
                    max=[180],
                    step=[1],
                    hide_details=True,
                    density="comfortable",
                    variant="plain",
                    flat=True,
                    control_variant="stacked",
                    inset=True,
                )
                v3.VNumberInput(
                    label="Latitude (min)",
                    v_model=("crop_latitude_min", -90),
                    min=[-90],
                    max=("crop_latitude_max", 90),
                    step=[1],
                    hide_details=True,
                    density="comfortable",
                    variant="plain",
                    flat=True,
                    control_variant="stacked",
                    inset=True,
                )
                v3.VNumberInput(
                    label="Latitude (max)",
                    v_model=("crop_latitude_max", 90),
                    min=("crop_latitude_min", -90),
                    max=[90],
                    step=[1],
                    hide_details=True,
                    density="comfortable",
                    variant="plain",
                    flat=True,
                    control_variant="stacked",
                    inset=True,
                )

    @change("crop_longitude_min", "crop_longitude_max")
    def _on_crop_lon(self, crop_longitude_min, crop_longitude_max, **_):
        if crop_longitude_min is None or crop_longitude_max is None:
            return

        data_range = [float(crop_longitude_min), float(crop_longitude_max)]
        if data_range[0] < data_range[1]:
            self.state.crop_longitude = data_range

    @change("crop_latitude_min", "crop_latitude_max")
    def _on_crop_lat(self, crop_latitude_min, crop_latitude_max, **_):
        if crop_latitude_min is None or crop_latitude_max is None:
            return

        data_range = [float(crop_latitude_min), float(crop_latitude_max)]
        if data_range[0] < data_range[1]:
            self.state.crop_latitude = data_range

    @change("crop_longitude")
    def _sync_crop_lon_inputs(self, crop_longitude, **_):
        if not crop_longitude or len(crop_longitude) < 2:
            return

        self.state.crop_longitude_min = crop_longitude[0]
        self.state.crop_longitude_max = crop_longitude[1]

    @change("crop_latitude")
    def _sync_crop_lat_inputs(self, crop_latitude, **_):
        if not crop_latitude or len(crop_latitude) < 2:
            return

        self.state.crop_latitude_min = crop_latitude[0]
        self.state.crop_latitude_max = crop_latitude[1]


class SimulationControls(v3.VToolbar):
    def __init__(self):
        super().__init__(**to_kwargs("simulation-controls"))

        with self:
            v3.VIcon("mdi-database-cog-outline", classes="pl-6 opacity-50")
            with v3.VBtnGroup(classes="mx-3", density="compact"):
                v3.VBtn(
                    "Two Sim",
                    variant="outlined",
                    size="small",
                    color="default",
                    click="comparison_mode = 'two-sim'",
                    style=(
                        "`border-width: ${comparison_mode === 'two-sim' ? '2px' : '1px'}; "
                        "border-style: solid; "
                        "border-color: ${comparison_mode === 'two-sim' ? 'rgb(var(--v-theme-primary))' : 'rgba(var(--v-border-color), var(--v-border-opacity))'}; "
                        "background-color: white; "
                        "color: ${comparison_mode === 'two-sim' ? '#000000' : 'rgba(var(--v-theme-on-surface), 0.7)'};`",
                    ),
                    classes=(
                        "`text-none ${comparison_mode === 'two-sim' ? 'font-weight-bold' : 'text-medium-emphasis'}`",
                    ),
                )
                v3.VBtn(
                    "Multi Sim",
                    variant="outlined",
                    size="small",
                    color="default",
                    click="comparison_mode = 'multi-sim'",
                    style=(
                        "`border-width: ${comparison_mode === 'multi-sim' ? '2px' : '1px'}; "
                        "border-style: solid; "
                        "border-color: ${comparison_mode === 'multi-sim' ? 'rgb(var(--v-theme-primary))' : 'rgba(var(--v-border-color), var(--v-border-opacity))'}; "
                        "background-color: white; "
                        "color: ${comparison_mode === 'multi-sim' ? '#000000' : 'rgba(var(--v-theme-on-surface), 0.7)'};`",
                    ),
                    classes=(
                        "`text-none ${comparison_mode === 'multi-sim' ? 'font-weight-bold' : 'text-medium-emphasis'}`",
                    ),
                )

            v3.VDivider(vertical=True, classes="mx-2")
            with v3.VSelect(
                v_if="comparison_mode === 'multi-sim'",
                v_model=("comparison_type", "diff"),
                items=(
                    [
                        {
                            "title": MULTI_SIM_COMPARISON_LABELS[comparison_type],
                            "value": comparison_type,
                        }
                        for comparison_type in COMPARISON_TYPES
                    ],
                ),
                item_title="title",
                item_value="value",
                label="Comparison type",
                chips=True,
                density="compact",
                variant="solo",
                hide_details=True,
                classes="mx-1",
                style="min-width: 14rem; max-width: 18rem;",
            ):
                with v3.Template(v_slot_selection="{ item }"):
                    with html.Div(classes="d-flex align-center py-1"):
                        v3.VChip(
                            "{{ item.raw.title }}",
                            size="small",
                            color="primary",
                            variant="outlined",
                        )
            with v3.VSelect(
                v_else=True,
                v_model=("selected_columns", ["ctrl", "test", "diff", "comp1", "comp2"]),
                items=(
                    [
                        {
                            "title": TWO_SIM_COLUMN_LABELS[column],
                            "value": column,
                        }
                        for column in ["ctrl", "test", "diff", "comp1", "comp2"]
                    ],
                ),
                item_title="title",
                item_value="value",
                label="Comparison columns",
                multiple=True,
                density="compact",
                variant="solo",
                hide_details=True,
                classes="mx-1",
                style="min-width: 0; max-width: 19rem;",
            ):
                with v3.Template(v_slot_selection="{ item, index }"):
                    with html.Div(
                        v_if="index === 0",
                        classes="d-flex align-center flex-nowrap w-100 overflow-hidden pt-1",
                        style="max-width: 100%;",
                    ):
                        html.Div(
                            "{{ selected_columns.length === 1 ? item.raw.title : `${selected_columns.length} selected` }}",
                            classes="text-body-2 text-truncate",
                        )

            v3.VSpacer()

            with v3.VSelect(
                v_model=("control_simulation_file", ""),
                items=("simulation_configs", []),
                item_title="label",
                item_value="path",
                label="Choose ctrl",
                chips=True,
                density="compact",
                variant="solo",
                hide_details=True,
                disabled=("simulation_configs.length === 0",),
                classes="mx-1",
                style="min-width: 14rem; max-width: 18rem;",
            ):
                with v3.Template(v_slot_selection="{ item }"):
                    with html.Div(classes="d-flex align-center py-1"):
                        v3.VChip(
                            "{{ item.raw.label || item.raw.path.split('/').pop() }}",
                            size="small",
                            color="primary",
                            variant="outlined",
                        )
            with v3.VSelect(
                v_if="comparison_mode === 'two-sim'",
                v_model=("two_sim_test_simulation_file", ""),
                items=(
                    "simulation_configs.filter(sim => sim.path !== control_simulation_file)",
                ),
                item_title="label",
                item_value="path",
                label="Choose test",
                chips=True,
                density="compact",
                variant="solo",
                hide_details=True,
                disabled=(
                    "simulation_configs.filter(sim => sim.path !== control_simulation_file).length === 0",
                ),
                classes="mx-1",
                style="min-width: 14rem; max-width: 18rem;",
            ):
                with v3.Template(v_slot_selection="{ item }"):
                    with html.Div(classes="d-flex align-center py-1"):
                        v3.VChip(
                            "{{ item.raw.label || item.raw.path.split('/').pop() }}",
                            size="small",
                            color="primary",
                            variant="outlined",
                        )

            v3.VBtn(
                "Organize simulation collection",
                v_if="comparison_mode === 'multi-sim'",
                size="small",
                variant="outlined",
                classes="text-none mx-1 mr-4",
                prepend_icon="mdi-pencil",
                click="simulation_controls_dialog = true",
            )

            with v3.VDialog(
                v_if="comparison_mode === 'multi-sim'",
                v_model=("simulation_controls_dialog", False),
                max_width=720,
                scrollable=True,
            ):
                with v3.VCard(style="max-height: 88vh;"):
                    with v3.VToolbar(
                        color="white",
                        density="compact",
                        classes="border-b-thin",
                    ):
                        v3.VIcon("mdi-database-cog-outline", classes="ml-4 mr-2")
                        v3.VLabel("Simulation selection", classes="text-subtitle-2")
                        v3.VSpacer()
                        with v3.VTooltip():
                            with v3.Template(v_slot_activator="{ props }"):
                                html.Div(
                                    "{{ simulation_configs.length }} loaded",
                                    v_bind="props",
                                    classes="text-caption mr-4",
                                )
                            html.Div(
                                "{{ (() => { if (!simulation_configs.length) return 'Loaded simulations:\\nnone'; return `Loaded simulations:\\n${simulation_configs.map(sim => `${sim.label || sim.path.split('/').pop()}${sim.path === control_simulation_file ? ' (ctrl)' : ''}`).join('\\n')}`; })() }}",
                                style="white-space: pre-line;",
                            )
                        v3.VBtn(
                            icon="mdi-close",
                            variant="text",
                            size="small",
                            classes="mr-2",
                            click="simulation_controls_dialog = false",
                        )
                    with html.Div(
                        v_if="simulation_configs.length === 0", classes="pa-4"
                    ):
                        html.Div(
                            "Load simulation files first, then choose the control and comparison runs here.",
                            classes="text-body-2 text-medium-emphasis",
                        )

                    with html.Div(
                        v_else=True,
                        classes="pa-3",
                        style="max-height: calc(86vh - 64px); overflow-y: auto;",
                    ):
                        with html.Div(
                            v_for="(entry, idx) in simulation_configs",
                            key="`${entry.path}-card`",
                            classes="simulation-entry-row pb-2 d-flex align-center",
                        ):
                            with html.Div(
                                classes="d-flex flex-column align-center justify-center mr-2 ga-1",
                            ):
                                with v3.VTooltip(text="Move up"):
                                    with v3.Template(v_slot_activator="{ props }"):
                                        v3.VBtn(
                                            v_bind="props",
                                            icon="mdi-chevron-up",
                                            size="small",
                                            variant="outlined",
                                            density="comfortable",
                                            color="primary",
                                            style="min-width: 34px; width: 34px; height: 34px;",
                                            disabled=("idx === 0",),
                                            click="""
if (idx > 0) {
  const nextConfigs = [...simulation_configs];
  const [moved] = nextConfigs.splice(idx, 1);
  nextConfigs.splice(idx - 1, 0, moved);
  simulation_configs = nextConfigs;
}
""",
                                        )
                                with v3.VTooltip(text="Move down"):
                                    with v3.Template(v_slot_activator="{ props }"):
                                        v3.VBtn(
                                            v_bind="props",
                                            icon="mdi-chevron-down",
                                            size="small",
                                            variant="outlined",
                                            density="comfortable",
                                            color="primary",
                                            style="min-width: 34px; width: 34px; height: 34px;",
                                            disabled=(
                                                "idx >= simulation_configs.length - 1",
                                            ),
                                            click="""
if (idx < simulation_configs.length - 1) {
  const nextConfigs = [...simulation_configs];
  const [moved] = nextConfigs.splice(idx, 1);
  nextConfigs.splice(idx + 1, 0, moved);
  simulation_configs = nextConfigs;
}
""",
                                        )
                            with v3.VCard(
                                variant="outlined",
                                classes="flex-grow-1",
                            ):
                                with v3.VCardText(classes="pa-3"):
                                    with v3.VRow(dense=True, classes="align-center"):
                                        with v3.VCol(cols=12, md=6):
                                            v3.VTextField(
                                                model_value=("entry.label",),
                                                update_modelValue="""
simulation_configs = simulation_configs.map((sim) =>
  sim.path === entry.path ? ({ ...sim, label: $event }) : sim
);
""",
                                                label="Label",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                            )
                                        with v3.VCol(cols=6, md=3):
                                            with v3.VTooltip(
                                                text=(
                                                    "control_simulation_file === entry.path ? 'Current control simulation' : 'Set this simulation as control'",
                                                ),
                                            ):
                                                with v3.Template(
                                                    v_slot_activator="{ props }"
                                                ):
                                                    v3.VBtn(
                                                        v_bind="props",
                                                        text=(
                                                            "control_simulation_file === entry.path ? 'Control' : 'Set control'",
                                                        ),
                                                        variant="outlined",
                                                        color=(
                                                            "control_simulation_file === entry.path ? 'primary' : 'default'",
                                                        ),
                                                        classes=(
                                                            "`text-none w-100 ${control_simulation_file === entry.path ? '' : 'text-medium-emphasis'}`",
                                                        ),
                                                        style="min-width: 112px;",
                                                        size="small",
                                                        click=(
                                                            self._on_control_selected,
                                                            "[entry.path]",
                                                        ),
                                                    )
                                        with v3.VCol(cols=6, md=3):
                                            with v3.VTooltip(
                                                text="Toggle simulation inclusion",
                                            ):
                                                with v3.Template(
                                                    v_slot_activator="{ props }"
                                                ):
                                                    v3.VCheckbox(
                                                        v_bind="props",
                                                        model_value=(
                                                            "control_simulation_file === entry.path ? true : entry.include",
                                                        ),
                                                        update_modelValue="""
simulation_configs = simulation_configs.map((sim) =>
  sim.path === entry.path ? ({ ...sim, include: !!$event }) : sim
);
""",
                                                        label="Include",
                                                        density="compact",
                                                        hide_details=True,
                                                        disabled=(
                                                            "control_simulation_file === entry.path",
                                                        ),
                                                    )
                                    html.Div(
                                        "{{ entry.path }}",
                                        classes="text-caption text-medium-emphasis mt-2",
                                        style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; direction: rtl; text-align: left;",
                                        title=("entry.path",),
                                    )

    def _on_control_selected(self, control_path, **_):
        self.state.control_simulation_file = control_path


class Animation(v3.VToolbar):
    def __init__(self):
        super().__init__(**to_kwargs("animation-controls"))

        with self:
            v3.VIcon(
                "mdi-video",
                classes="px-6 opacity-50",
            )
            with v3.VRow(classes="ma-0 px-2 align-center"):
                v3.VSelect(
                    v_model=("animation_track", None),
                    items=("available_animation_tracks", []),
                    flat=True,
                    variant="plain",
                    hide_details=True,
                    density="compact",
                    style="max-width: 10rem;",
                )
                v3.VDivider(vertical=True, classes="mx-2")
                v3.VSlider(
                    v_model=("animation_step", 1),
                    min=0,
                    max=("animation_step_max", 0),
                    step=1,
                    hide_details=True,
                    density="compact",
                    classes="mx-4",
                )
                v3.VDivider(vertical=True, classes="mx-2")
                v3.VIconBtn(
                    v_tooltip_bottom="'First step'",
                    icon="mdi-page-first",
                    flat=True,
                    disabled=("animation_step === 0",),
                    click="animation_step = 0",
                )
                v3.VIconBtn(
                    v_tooltip_bottom="'Previous step'",
                    icon="mdi-chevron-left",
                    flat=True,
                    disabled=("animation_step === 0",),
                    click="animation_step = Math.max(0, animation_step - 1)",
                )
                v3.VIconBtn(
                    v_tooltip_bottom="'Next step'",
                    icon="mdi-chevron-right",
                    flat=True,
                    disabled=("animation_step === animation_step_max",),
                    click="animation_step = Math.min(animation_step_max, animation_step + 1)",
                )
                v3.VIconBtn(
                    v_tooltip_bottom="'Last step'",
                    icon="mdi-page-last",
                    disabled=("animation_step === animation_step_max",),
                    flat=True,
                    click="animation_step = animation_step_max",
                )
                v3.VDivider(vertical=True, classes="mx-2")
                v3.VIconBtn(
                    v_tooltip_bottom="'Play reverse'",
                    icon=(
                        "animation_play && animation_direction === 'reverse' ? 'mdi-stop' : 'mdi-play'",
                    ),
                    flat=True,
                    click="if (animation_play && animation_direction === 'reverse') { animation_play = false } else { animation_direction = 'reverse'; animation_play = true }",
                    disabled=("animation_play && animation_direction === 'forward'",),
                    style="transform: scaleX(-1);",
                )
                v3.VIconBtn(
                    v_tooltip_bottom="'Play forward'",
                    icon=(
                        "animation_play && animation_direction === 'forward' ? 'mdi-stop' : 'mdi-play'",
                    ),
                    flat=True,
                    click="if (animation_play && animation_direction === 'forward') { animation_play = false } else { animation_direction = 'forward'; animation_play = true }",
                    disabled=("animation_play && animation_direction === 'reverse'",),
                )
                v3.VDivider(vertical=True, classes="mx-2")

                with v3.VIconBtn(
                    classes="position-relative",
                    flat=True,
                    v_if=("animation_export", False),
                    click="animation_export = false",
                ):
                    v3.VIcon("mdi-download-multiple-outline")
                    v3.VProgressCircular(
                        color="error",
                        bg_color="white",
                        width=2,
                        size=28,
                        indeterminate=True,
                        classes="position-absolute",
                    )
                with v3.VMenu(
                    v_else=True,
                    close_on_content_click=False,
                    v_model=("show_animation_export_menu", False),
                ):
                    with v3.Template(v_slot_activator="{ props }"):
                        v3.VIconBtn(
                            v_bind="props",
                            v_tooltip_bottom="'Export animation (ZIP)'",
                            icon="mdi-download-multiple-outline",
                            flat=True,
                            loading=("animation_export", False),
                            disabled=(
                                "capture_recording || !animation_track || animation_play || animation_export",
                            ),
                        )
                    with v3.VList(
                        density="compact",
                        v_model_activated=("animation_export_fields", []),
                        activatable=True,
                        active_strategy="independent",
                    ):
                        v3.VListItem(title="Viewport", value=("false",))
                        v3.VDivider()
                        v3.VListItem(
                            v_for="item in animation_export_items",
                            key="item.value",
                            title=("item.title",),
                            value=("item.value",),
                        )
                        v3.VDivider()
                        v3.VListItem(
                            active=False,
                            title="Export animation",
                            value=("null",),
                            click="utils.quickview.captureAnimation(animation_export_fields)",
                        )

    @change("animation_track")
    def _on_animation_track_change(self, animation_track, **_):
        self.state.animation_step = 0
        self.state.animation_step_max = 0

        if animation_track:
            values = None
            try:
                values = self.state[animation_track]
            except Exception:
                values = None

            if values:
                self.state.animation_step_max = len(values) - 1

    @change("animation_step")
    def _on_animation_step(self, animation_track, animation_step, **_):
        if animation_track:
            self.state[f"{animation_track}_idx"] = animation_step

    @change("animation_play")
    def _on_animation_play(self, animation_play, **_):
        if animation_play:
            asynchronous.create_task(self._run_animation())

    async def _run_animation(self):
        with self.state as s:
            while s.animation_play:
                await asyncio.sleep(0.1)
                if s.animation_direction == "reverse":
                    if s.animation_step > 0:
                        with s:
                            s.animation_step -= 1
                        await self.server.network_completion
                    else:
                        with s:
                            s.animation_step = s.animation_step_max
                        await self.server.network_completion
                else:
                    if s.animation_step < s.animation_step_max:
                        with s:
                            s.animation_step += 1
                        await self.server.network_completion
                    else:
                        with s:
                            s.animation_step = 0
                        await self.server.network_completion
