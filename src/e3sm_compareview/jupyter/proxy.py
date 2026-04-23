"""Server proxy configuration for QuickCompare in JupyterLab."""

from pathlib import Path


def setup_compareview():
    """Configure jupyter-server-proxy for QuickCompare."""
    return setup_quickcompare()


def setup_quickcompare():
    """Configure jupyter-server-proxy for QuickCompare."""
    icon_path = Path(__file__).with_name("icons") / "compareview.png"

    return {
        "command": [
            "quickcompare",
            "--server",
            "--port",
            "{port}",
            "--host",
            "127.0.0.1",
        ],
        "timeout": 30,
        "launcher_entry": {
            "enabled": True,
            "title": "E3SM QuickCompare",
            "icon_path": str(icon_path.resolve()),
            "category": "Other",
        },
        "new_browser_tab": False,
    }
