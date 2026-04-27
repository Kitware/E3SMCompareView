import math


def format_color_range_endpoint(value, scale="linear", range_min=None, range_max=None):
    if value is None:
        return "Auto"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "Auto"

    if math.isnan(value):
        return "Auto"

    if scale == "log" and value > 0:
        return f"10^({math.log10(value):.1f})"

    if scale == "symlog":
        if value == 0:
            return "0"
        range_min = 0 if range_min is None else float(range_min)
        range_max = 0 if range_max is None else float(range_max)
        linthresh = max(abs(range_min), abs(range_max)) * 1e-2 or 1.0
        abs_value = abs(value)
        if abs_value <= linthresh:
            return f"{value:.1e}"
        sign = "-" if value < 0 else ""
        return f"{sign}10^({math.log10(abs_value):.1f})"

    if value == 0:
        return "0"
    return f"{value:.4g}"


def format_color_range_endpoints(color_range, scale="linear"):
    range_min, range_max = color_range
    return [
        format_color_range_endpoint(range_min, scale, range_min, range_max),
        format_color_range_endpoint(range_max, scale, range_min, range_max),
    ]
