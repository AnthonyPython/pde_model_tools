# skel\utils.py
import math
import struct

from mathutils import Vector

from ..log import log


def read_bone_info(file):
    """Read bone names and hierarchy"""
    try:
        # Bone name length
        name_length = struct.unpack("<I", file.read(4))[0]
        log.debug("Bone name length: %s", name_length)
        # Bone name
        name = file.read(name_length).decode("ascii")
        log.debug("Bone name: %s", name)
        # Bone hierarchy level
        level = struct.unpack("<I", file.read(4))[0]

        log.debug("Bone info: %s %s", name, level)

        # Return bone name and level
        return name, level
    except struct.error as e:
        log.debug("Failed to read bone info: %s", e)
        return None


def read_bone_transform(file):
    """Read bone transform data"""
    try:
        # Head coordinates
        head = struct.unpack("<fff", file.read(12))
        # Tail coordinates
        tail = struct.unpack("<fff", file.read(12))
        # End tag?
        end_tag = struct.unpack("<f", file.read(4))[0]

        log.debug("Head: %s Tail: %s End tag: %s", head, tail, end_tag)

        return head, tail, end_tag
    except struct.error as e:
        log.debug("Failed to read bone transform: %s", e)
        return None


def validate_file(file):
    """Validate that the file is a skel file"""
    try:
        header = file.read(12)
        return header == b"\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00"
    except Exception as e:
        log.debug("File validation failed: %s", e)
        return False


def convert_coordinates(coords):
    """Convert coordinate system"""
    x, y, z = coords

    return x, z, y


def calculate_bone_roll(bone):
    """Calculate bone roll angle"""
    if "arm" in bone.name.lower():
        return math.radians(90)
    elif "leg" in bone.name.lower():
        return math.radians(-90)
    elif "hand" in bone.name.lower():
        return math.radians(180)
    return 0


def print_hierarchy(bones):
    """Print bone hierarchy"""
    log.debug("Bone hierarchy:")
    for name, level in bones:
        # indent = "  " * (level - 1)
        log.debug("%s %s", name, level)


def create_bone_chain(edit_bones, bones, transforms):
    """Create a bone chain"""
    bone_dict = {}

    # Create all bones
    for i, (name, level) in enumerate(bones):
        if i < len(transforms):
            bone = edit_bones.new(name)
            head, tail, end_tag = transforms[i]

            # Convert coordinates
            head = convert_coordinates(head)
            tail = convert_coordinates(tail)

            # Set bone position
            bone.head = Vector(head)
            bone.tail = Vector(tail)

            # Calculate bone orientation
            # bone.roll = calculate_bone_roll(bone)

            # Store bone info
            bone_dict[name] = {"bone": bone, "level": level}

    # Set parent-child relationships
    for name, data in bone_dict.items():
        bone = data["bone"]
        level = data["level"]

        if level > 1:
            # Find the nearest parent bone
            parent_level = level - 1
            potential_parents = [
                (n, d) for n, d in bone_dict.items() if d["level"] == parent_level
            ]

            if potential_parents:
                # Choose the nearest parent bone
                closest_parent = min(
                    potential_parents,
                    key=lambda x: (x[1]["bone"].head - bone.head).length,
                )
                bone.parent = closest_parent[1]["bone"]
                # Set parent bone tail to child bone head
                closest_parent[1]["bone"].tail = bone.head


def add_bone_constraints(armature_obj):
    """Add bone constraints"""
    pose = armature_obj.pose

    # Add IK constraints
    for bone_name in pose.bones:
        if "IK" in bone_name:
            target_name = bone_name.replace("IK", "")
            if target_name in pose.bones:
                constraint = pose.bones[target_name].constraints.new("IK")
                constraint.target = armature_obj
                constraint.subtarget = bone_name
