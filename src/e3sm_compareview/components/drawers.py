from trame.decorators import change
from trame.widgets import client, html
from trame.widgets import vuetify3 as v3

from e3sm_compareview.components.drawer_utils import drawer_style
from e3sm_quickview.utils import constants, js


class FieldSelection(v3.VNavigationDrawer):
    def __init__(self, load_variables=None):
        super().__init__(
            model_value=(js.is_active("select-fields"),),
            width=500,
            permanent=True,
            style=(drawer_style("select-fields"),),
        )

        self.state.setdefault("loading_time", 0)
        self.state.setdefault(
            "visible_selection_icons",
            [
                "mdi-eye-outline",  # 0 => all
                "mdi-eye-check-outline",  # 1 => only-checked
                "mdi-eye-remove-outline",  # 2 => only-unchecked
            ],
        )
        self.state.setdefault("visible_selection_icon_idx", 0)

        with self:
            with html.Div(
                style="position:fixed;top:0;width: 500px;height:100vh;",
                classes="d-flex flex-column",
            ):
                with v3.VCardActions(classes="pb-0", style="min-height: 0;"):
                    v3.VBtn(
                        classes="text-none",
                        color="primary",
                        prepend_icon="mdi-database",
                        text=(
                            "`Load ${variables_selected.length} variable${variables_selected.length > 1 ? 's' :''} ${ loading_time ? ('(' + loading_time.toFixed(1) + ' s)') : ''}`",
                        ),
                        variant="flat",
                        disabled=(
                            "variables_selected.length === 0 || variables_loaded || loading",
                        ),
                        loading=("loading", False),
                        click=load_variables,
                        block=True,
                    )
                with v3.VCardActions(
                    key="variables_selected.length",
                    classes="flex-wrap py-1 flex-0-0 ga-1",
                    style="overflow-y: auto; max-height: 40vh; min-height: 64px;",
                ):
                    with v3.VChip(
                        "{{ vtype.name }}",
                        v_for="(vtype, idx) in variable_types",
                        key="idx",
                        color=("vtype.color",),
                        v_show=(
                            "variables_selected.filter(id => variables_listing.find(v => v.id === id)?.type === vtype.name).length",
                        ),
                        size="small",
                        closable=True,
                        click="variables_filter === vtype.name ? (variables_filter = '') : (variables_filter = vtype.name)",
                        click_close=(
                            "variables_selected = variables_selected.filter(id => variables_listing.find(v => v.id === id)?.type !== vtype.name)"
                        ),
                        classes="mx-1",
                    ):
                        with v3.Template(v_slot_prepend=True):
                            v3.VAvatar(
                                "{{ variables_selected.filter(id => variables_listing.find(v => v.id === id)?.type === vtype.name).length }}",
                                border=True,
                                classes="mr-1 ml-n1",
                                variant="plain",
                            )

                v3.VTextField(
                    v_model=("variables_filter", ""),
                    color="primary",
                    placeholder="Filter",
                    density="compact",
                    variant="outlined",
                    classes="mx-2 flex-0-0",
                    prepend_icon=[
                        "visible_selection_icons[visible_selection_icon_idx]"
                    ],
                    prepend_inner_icon="mdi-magnify",
                    clearable=True,
                    click_prepend=self.toggle_visible_selection,
                    messages=[
                        "['Show selected and unselected variables','Show only selected variables', 'Show only unselected variables'][visible_selection_icon_idx]"
                    ],
                )
                with html.Div(style="margin:1px;padding:1px;", classes="flex-fill"):
                    with client.SizeObserver("var_selection_size"):
                        # All
                        with v3.VDataTable(
                            v_if="visible_selection_icon_idx === 0",
                            v_model=("variables_selected", []),
                            show_select=True,
                            item_value="id",
                            density="compact",
                            fixed_header=True,
                            headers=(
                                "variables_headers",
                                constants.VAR_HEADERS,
                            ),
                            items=("variables_listing", []),
                            height=["var_selection_size?.size.height || '30vh'"],
                            style="user-select: none; cursor: pointer;top:0;left:0;",
                            classes="position-absolute show-scrollbar",
                            hover=True,
                            search=("variables_filter", ""),
                            custom_filter=(
                                "(utils && utils.quickview && utils.quickview.filter) ? utils.quickview.filter : null",
                            ),
                            items_per_page=-1,
                            hide_default_footer=True,
                        ):
                            with v3.Template(raw_attrs=['#item.name="{ value }"']):
                                html.Div(
                                    "{{ value }}",
                                    classes="text-break",
                                    title=["`${value}`"],
                                )
                            with v3.Template(raw_attrs=['#item.type="{ value }"']):
                                html.Div(
                                    "{{ value }}",
                                    classes="text-break text-caption",
                                )

                        # Checked only
                        with v3.VDataTable(
                            v_if="visible_selection_icon_idx === 1",
                            v_model=("variables_selected", []),
                            show_select=True,
                            item_value="id",
                            density="compact",
                            fixed_header=True,
                            headers=(
                                "variables_headers",
                                constants.VAR_HEADERS,
                            ),
                            items=(
                                "variables_listing.filter((v) => variables_selected.includes(v.id))",
                            ),
                            height=["var_selection_size?.size.height || '30vh'"],
                            style="user-select: none; cursor: pointer;top:0;left:0;",
                            classes="position-absolute show-scrollbar",
                            hover=True,
                            search=("variables_filter", ""),
                            items_per_page=-1,
                            hide_default_footer=True,
                        ):
                            with v3.Template(raw_attrs=['#item.name="{ value }"']):
                                html.Div(
                                    "{{ value }}",
                                    classes="text-break",
                                    title=["`${value}`"],
                                )
                            with v3.Template(raw_attrs=['#item.type="{ value }"']):
                                html.Div(
                                    "{{ value }}",
                                    classes="text-break text-caption",
                                )

                        # Unchecked only
                        with v3.VDataTable(
                            v_if="visible_selection_icon_idx === 2",
                            v_model=("variables_selected", []),
                            show_select=True,
                            item_value="id",
                            density="compact",
                            fixed_header=True,
                            headers=(
                                "variables_headers",
                                constants.VAR_HEADERS,
                            ),
                            items=(
                                "variables_listing.filter((v) => !variables_selected.includes(v.id))",
                            ),
                            height=["var_selection_size?.size.height || '30vh'"],
                            style="user-select: none; cursor: pointer;top:0;left:0;",
                            classes="position-absolute show-scrollbar",
                            hover=True,
                            search=("variables_filter", ""),
                            items_per_page=-1,
                            hide_default_footer=True,
                        ):
                            with v3.Template(raw_attrs=['#item.name="{ value }"']):
                                html.Div(
                                    "{{ value }}",
                                    classes="text-break",
                                    title=["`${value}`"],
                                )
                            with v3.Template(raw_attrs=['#item.type="{ value }"']):
                                html.Div(
                                    "{{ value }}",
                                    classes="text-break text-caption",
                                )

    @change("variables_selected")
    def _on_dirty_variable_selection(self, **_):
        self.state.variables_loaded = False

    def toggle_visible_selection(self):
        self.state.visible_selection_icon_idx += 1
        if self.state.visible_selection_icon_idx >= 3:
            self.state.visible_selection_icon_idx = 0
