# Code repo of QuickCompare

[![Test](https://github.com/Kitware/E3SMQuickCompare/actions/workflows/test.yml/badge.svg)](https://github.com/Kitware/E3SMQuickCompare/actions/workflows/test.yml)
[![Release](https://github.com/Kitware/E3SMQuickCompare/actions/workflows/release.yml/badge.svg)](https://github.com/Kitware/E3SMQuickCompare/actions/workflows/release.yml)
[![Package](https://github.com/Kitware/E3SMQuickCompare/actions/workflows/package.yml/badge.svg)](https://github.com/Kitware/E3SMQuickCompare/actions/workflows/package.yml)
![PyPI](https://img.shields.io/pypi/v/e3sm-compareview?label=pypi%20package)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/e3sm_compareview.svg)](https://anaconda.org/conda-forge/e3sm_compareview)

**QuickCompare**
is an offshoot of [QuickView](https://kitware.github.io/QuickView/guides/quickview/),
an interactive tool for inspecting data files produced by Earth system simulations.
Instead of presenting a single simulation,
QuickCompare contrasts two or more simulations that
use the same horizontal mesh (and hence the same connectivity information).
Plots can be shown for the user-selected physical quantities themselves
as well as differences and relative differences between simulations.
Like QuickView,
QuickCompare is designed to present multiple variables simultaneously
to help identify potential relationships.

![Screenshot](https://raw.githubusercontent.com/Kitware/QuickView/master/docs/guides/quickcompare/screenshots/quickcompare_ui.png)

## Key Features

- Intuitive, minimalist interface tailored for Earth system modeling.
- Physical quantities displayed together with differences and/or relative differences between simulations.
- Multi-variable visualization.
- Persistent sessions—pick up where you left off.
- Support for EAM v2, v3, and upcoming v4 output formats
  as well as the E3SM land model ELM's input and output files
  on ne*pg2 grids.

## Getting Started 

See [documentation page](https://kitware.github.io/QuickView/guides/quickcompare/getting_started.html).


## Project Background

QuickCompare is developed by [Kitware, Inc.](https://www.kitware.com/) in collaboration with
[Pacific Northwest National Laboratory](https://www.pnnl.gov/), supported by the
U.S. Department of Energy's
[ASCR](https://www.energy.gov/science/ascr/advanced-scientific-computing-research)
and
[BER](https://www.energy.gov/science/ber/biological-and-environmental-research)
programs via [SciDAC](https://www.scidac.gov/).

### Contributors

- **Lead Developer**: [Will Dunklin](https://www.kitware.com/will-dunklin/) (Kitware)
- **Key Contributors**: Sebastien Jourdain, Patrick O'Leary, Berk Geveci, Dan Lipsa (Kitware, Inc.); Hui Wan, Kai Zhang (PNNL)

## License

Apache Software License - see [LICENSE](LICENSE) file for details.

## Commit message convention

Semantic release rely on
[conventional commits](https://www.conventionalcommits.org/) to generate new
releases and changelog.
