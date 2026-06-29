from trame.widgets import html
from trame.widgets import vuetify3 as v3

from e3sm_compareview import __version__ as app_version
from e3sm_compareview.assets import ASSETS
from e3sm_quickview.components import css as qv_css
from e3sm_quickview.components import tools as qv_tools
from e3sm_quickview.utils import js


class AppLogo(v3.VTooltip):
    def __init__(self, compact="compact_drawer"):
        super().__init__(
            text=f"QuickCompare {app_version}",
            disabled=(f"!{compact}",),
        )
        with self:
            with v3.Template(v_slot_activator="{ props }"):
                with v3.VListItem(
                    v_bind="props",
                    click=f"{compact} = !{compact}",
                ):
                    with html.Div(classes="d-flex align-center flex-grow-1"):
                        html.Img(
                            src=ASSETS.icon,
                            v_if=compact,
                            style="width: 24px; height: 24px; object-fit: contain;",
                        )
                        html.Img(
                            src=ASSETS.logo,
                            v_else=True,
                            style="height: 28px; max-width: 160px; object-fit: contain;",
                        )
                    v3.VProgressCircular(
                        color="primary",
                        indeterminate=True,
                        v_show="trame__busy",
                        v_if=compact,
                        style="position: absolute !important;left: 50%;top: 50%; transform: translate(-50%, -50%);",
                    )
                    v3.VProgressLinear(
                        v_else=True,
                        color="primary",
                        indeterminate=True,
                        v_show="trame__busy",
                        absolute=True,
                        style="top:90%;width:100%;",
                    )


class FieldSelectionTool(v3.VTooltip):
    def __init__(self, click=None, compact="compact_drawer"):
        super().__init__(
            text="Variable selection",
            disabled=(f"!{compact}",),
        )
        with self:
            with v3.Template(v_slot_activator="{ props }"):
                with v3.VListItem(
                    v_bind="props",
                    active=(js.is_active("select-fields"),),
                    active_class="border-primary border-md border-primary border-opacity-100",
                    prepend_icon="mdi-list-status",
                    title=(f"{compact} ? null : 'Variable selection'",),
                    click=click,
                    disabled=("variables_listing.length === 0",),
                ):
                    with v3.Template(v_slot_append=True):
                        v3.VHotkey(
                            keys="v",
                            variant="contained",
                            inline=True,
                            classes="mt-n2",
                        )


class Tools(v3.VNavigationDrawer):
    def __init__(self, reset_camera=None, toggle_toolbar=None):
        super().__init__(
            permanent=True,
            rail=("compact_drawer", True),
            width=253,
            style="transform: none;",
        )

        with self:
            with html.Div(style=qv_css.NAV_BAR_TOP):
                with v3.VList(
                    density="compact",
                    nav=True,
                    select_strategy="independent",
                    v_model_selected=(
                        "active_tools",
                        [
                            "load-data",
                            "select-fields",
                            "adjust-layout",
                            "select-slice-time",
                            "simulation-controls",
                        ],
                    ),
                ):
                    AppLogo()
                    qv_tools.ResetCamera(click=reset_camera)

                    v3.VDivider(classes="my-1")

                    qv_tools.StateImportExport()
                    qv_tools.OpenFile()

                    v3.VDivider(classes="my-1")

                    FieldSelectionTool(click=(toggle_toolbar, "['select-fields']"))
                    qv_tools.DataSelection()
                    qv_tools.Animation()
                    qv_tools.ToggleButton(
                        compact="compact_drawer",
                        title="Comparison",
                        icon="mdi-database-cog-outline",
                        value="simulation-controls",
                    )

                    v3.VDivider(classes="my-1")

                    qv_tools.LayoutManagement()
                    qv_tools.MapProjection()
                    qv_tools.Cropping()

                    v3.VDivider(classes="my-1")

                    qv_tools.CaptureFullPanel(click="utils.quickview.capturePanel()")

                    if self.server.hot_reload:
                        v3.VDivider(classes="my-1")
                        qv_tools.ActionButton(
                            compact="compact_drawer",
                            title="Refresh UI",
                            icon="mdi-database-refresh-outline",
                            click=self.ctrl.on_server_reload,
                        )

            with html.Div(style=qv_css.NAV_BAR_BOTTOM):
                v3.VDivider()
                v3.VLabel(
                    f"{app_version}",
                    classes="text-center text-caption d-block text-wrap",
                )
