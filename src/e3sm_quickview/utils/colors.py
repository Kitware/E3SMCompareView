TYPE_COLORS = [
    "success",
    "info",
    "warning",
    "error",
    "purple",
    "cyan",
    "teal",
    "indigo",
    "pink",
    "amber",
    "lime",
    "deep-purple",
]


def get_type_color(index: int) -> str:
    return TYPE_COLORS[index % len(TYPE_COLORS)]
