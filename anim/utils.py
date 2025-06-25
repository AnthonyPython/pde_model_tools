# anim\utils.py
"""Utility helpers for animation import."""

import re
from mathutils import Quaternion

from ..log import log


def quat_to_eul(quat):
    """Convert a quaternion to Euler angles in XYZ order."""
    quat_obj = Quaternion(quat)
    euler_obj = quat_obj.to_euler("XYZ")
    return euler_obj


def is_valid_group_name(name):
    """Validate that a vertex group name is Blender compatible."""
    if not name or not isinstance(name, str):
        log.warning("Group name is empty or not a string: %s", name)
        return False
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        return True
    log.warning(
        "Group name contains invalid characters or starts with a digit: %s",
        name,
    )
    return False
