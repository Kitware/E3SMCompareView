from trame.widgets import html
from trame.widgets import vuetify3 as v3

from e3sm_compareview.assets import ASSETS
from e3sm_quickview.components.doc import (
    Bold,
    Link,
    Paragraph,
    Title,
    ToolAnimation,
    ToolCropping,
    ToolDataSelection,
    ToolFieldSelection,
    ToolFileLoading,
    ToolLayoutManagement,
    ToolMapProjection,
    ToolResetCamera,
    ToolStateImportExport,
)


class LandingPage(v3.VContainer):
    def __init__(self):
        super().__init__(classes="pa-6 pa-md-12")

        with self:
            html.P(
                "QuickCompare",
                classes="mt-2 text-h5 font-weight-bold text-sm-h4 text-medium-emphasis",
            )

            Paragraph(
                f"""
                {Bold("QuickCompare")} is an offshoot of {Link("QuickView", "https://github.com/Kitware/QuickView")}.
                Both tools are designed to help Earth system modelers take quick looks at
                a collection of physical quantities in their simulation files.
                While QuickView is designed for inspecting a single simulation,
                QuickCompare contrasts two or more simulations by displaying
                the physical quantities as well as their differences between simulations.
                A detailed {Bold("User's Guide")} can be found through
                {Link("this link","https://kitware.github.io/QuickView/guides/quickcompare/")}.
                {Bold("Bug reports and feature requests")} can be submitted through
                {Link("GitHub","https://github.com/Kitware/E3SMQuickCompare/issues")}.
            """
            )

#           v3.VImg(classes="rounded-lg", src=ASSETS.banner)

            Title("Toolbar Icons")

            with v3.VRow():
                with v3.VCol(cols=6):
                    ToolFileLoading()
                    ToolFieldSelection()
                    ToolMapProjection()
                    ToolResetCamera()

                with v3.VCol(cols=6):
                    ToolLayoutManagement()
                    ToolCropping()
                    ToolDataSelection()
                    ToolAnimation()
                    ToolStateImportExport()

            Title("Keyboard Shortcuts")

            with v3.VRow():
                with v3.VCol(cols=6):
                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Toggle help for main toolbar")
                        v3.VSpacer()
                        v3.VHotkey(keys="h", variant="contained", inline=True)

                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Auto zoom")
                        v3.VSpacer()
                        v3.VHotkey(keys="z", variant="contained", inline=True)

            #       with v3.VRow(classes="ma-0 pb-4"):
            #           v3.VLabel("Toggle view interaction lock")
            #           v3.VSpacer()
            #           v3.VHotkey(keys="space", variant="contained", inline=True)

                    v3.VDivider(classes="mb-4")

                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("File loading")
                        v3.VSpacer(classes="mt-2")
                        v3.VHotkey(keys="f", variant="contained", inline=True)

                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Export state")
                        v3.VSpacer(classes="mt-2")
                        v3.VHotkey(keys="e", variant="contained", inline=True)

                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Import state")
                        v3.VSpacer(classes="mt-2")
                        v3.VHotkey(keys="i", variant="contained", inline=True)

                    v3.VDivider(classes="mb-4")

                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Toggle viewport layout control panel")
                        v3.VSpacer(classes="mt-2")
                        v3.VHotkey(keys="p", variant="contained", inline=True)
                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Toggle lat/lon cropping panel")
                        v3.VSpacer()
                        v3.VHotkey(keys="l", variant="contained", inline=True)
                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Toggle slice selection panel")
                        v3.VSpacer()
                        v3.VHotkey(keys="s", variant="contained", inline=True)
                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Toggle animation control panel")
                        v3.VSpacer()
                        v3.VHotkey(keys="a", variant="contained", inline=True)

                    v3.VDivider(classes="mb-4")

                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Toggle grouped layout in viewport")
                        v3.VSpacer()
                        v3.VHotkey(keys="g", variant="contained", inline=True)

                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Toggle variable selection panel")
                        v3.VSpacer()
                        v3.VHotkey(keys="v", variant="contained", inline=True)

                    v3.VDivider(classes="mb-4")

                    with v3.VRow(classes="ma-0 pb-4"):
                        v3.VLabel("Disable all toolbars and control panels")
                        v3.VSpacer()
                        v3.VHotkey(keys="esc", variant="contained", inline=True)

                with v3.VCol(cols=6):
                    with v3.VRow(classes="ma-0 pb-2"):
                        v3.VLabel("Projections")

                    with v3.VList(density="compact", classes="pa-0 ma-0"):
                        with v3.VListItem(subtitle="Cylindrical Equidistant"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="c", variant="contained", inline=True)
                        with v3.VListItem(subtitle="Robinson"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="r", variant="contained", inline=True)
                        with v3.VListItem(subtitle="Mollweide"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="m", variant="contained", inline=True)

                    v3.VDivider(classes="my-4")

                    with v3.VRow(classes="ma-0 pb-2"):
                        v3.VLabel("Change column arrangement in viewport")

                    with v3.VList(density="compact", classes="pa-0 ma-0"):
                        with v3.VListItem(subtitle="Auto flow"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="=", variant="contained", inline=True)
                        with v3.VListItem(subtitle="Auto"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="0", variant="contained", inline=True)
                        with v3.VListItem(subtitle="1 column"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="1", variant="contained", inline=True)
                        with v3.VListItem(subtitle="2 columns"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="2", variant="contained", inline=True)
                        with v3.VListItem(subtitle="3 columns"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="3", variant="contained", inline=True)
                        with v3.VListItem(subtitle="4 columns"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="4", variant="contained", inline=True)
                        with v3.VListItem(subtitle="6 columns"):
                            with v3.Template(v_slot_append="True"):
                                v3.VHotkey(keys="6", variant="contained", inline=True)

            Title("Project Background")

            Paragraph(f"""
                QuickCompare is collaboratively developed by
                {Link("Kitware", "https://www.kitware.com")} and
                {Link("Pacific Northwest National Laboratory", "https://www.pnnl.gov/")}
                using funding from the U.S. Department of Energy's SciDAC program
                through a partnership between
                the {Link("Advanced Scientific Computing Reaserch (ASCR)",
                "https://www.energy.gov/science/ascr/advanced-scientific-computing-research")} program and
                the {Link("Biological and Environmental Research (BER)",
                "https://www.energy.gov/science/ber/biological-and-environmental-research")} program.
            """
            )

            Paragraph(f"""
                The development of QuickView used resources of the
                {Link("National Energy Research Scientific Computing Center (NERSC)","https://www.nersc.gov/")},
                a U.S. Department of Energy User Facility.
            """
            )
