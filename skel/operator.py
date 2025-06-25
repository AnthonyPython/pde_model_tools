# skel\operator.py
import os
import struct

import bpy

from . import utils
from ..log import log


class ImportSkelClass(bpy.types.Operator):
    """Import custom skeleton files."""

    bl_idname = "import.skel"
    bl_label = "Import skeleton .skel"
    bl_options = {"REGISTER", "UNDO"}

    # File path property
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH",
        default="",
    )  # type: ignore
    # Extension filter
    filename_ext = ".skel"
    filter_glob: bpy.props.StringProperty(default="*.skel", options={"HIDDEN"})  # type: ignore

    def invoke(self, context, event):
        # Filter for .skel files
        self.filter_glob = "*.skel;"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        """Import skeleton data"""
        try:
            # File path
            file_path = self.filepath

            # Extract file name
            file_name = os.path.splitext(os.path.basename(file_path))[0]

            # Bone names and hierarchy
            bones = []
            # Bone transform data
            transforms = []

            # Read skeleton info
            with open(file_path, "rb") as file:
                # Validate the file
                if not utils.validate_file(file):
                    log.debug("Invalid file format")
                    return {"CANCELLED"}

                # Read bone names and hierarchy
                log.debug("Reading bone names and hierarchy")
                while True:
                    # Get current file position
                    current_position = file.tell()
                    # Read bone info
                    bone_info = utils.read_bone_info(file)

                    # Break if read fails
                    if bone_info is None:
                        log.debug("Failed to read bone info")
                        break

                    # Append bone info
                    name, level = bone_info
                    bones.append((name, level))

                    # Check for end of name section
                    # Get current file position
                    current_position = file.tell()
                    # Read next bone name length
                    next_name_length = struct.unpack("<I", file.read(4))[0]
                    # Skip 23 bytes (+4 previous) each block is 28 bytes
                    file.seek(23, 1)
                    # Read end tag
                    end_tag = file.read(1).hex()
                    # Restore file position
                    file.seek(current_position)

                    log.debug("Next name length: %s end tag: %s", next_name_length, end_tag)

                    # Check if end of name section reached
                    if next_name_length <= 0 and end_tag == "3f":
                        log.debug("Finished reading bone info: %s", len(bones))
                        break

                log.debug("Reading bone transforms")
                log.debug("Current file offset: %s", current_position)
                # Read bone transform data
                bones_len = len(bones)
                # Iterate to read transform data
                for i in range(bones_len):
                    log.debug(
                        "%s reading transform for %s level %s",
                        i + 1 ,bones[i][0],bones[i][1]
                    )

                    # Read transform
                    transform = utils.read_bone_transform(file)
                    # Stop loop on failure
                    if transform is None:
                        break
                    # Append transform
                    transforms.append(transform)

                log.debug("Finished reading bone transforms: %s", len(transforms))
                # Print bone hierarchy
                utils.print_hierarchy(bones)

            # Create armature
            log.debug("Creating armature")
            # Create armature object
            armature = bpy.data.armatures.new(file_name)
            armature_obj = bpy.data.objects.new(file_name, armature)

            # Show names
            armature.show_names = True
            # Show axes
            armature.show_axes = True
            # armature.display_type = 'STICK'

            # Set object transforms
            # armature_obj.scale = (scale, scale, scale)

            # Link armature object
            context.collection.objects.link(armature_obj)
            # Activate armature object
            context.view_layer.objects.active = armature_obj

            # Enter edit mode
            bpy.ops.object.mode_set(mode="EDIT")

            # Create bones
            utils.create_bone_chain(armature.edit_bones, bones, transforms)

            # Add bone constraints
            bpy.ops.object.mode_set(mode="POSE")
            log.debug("Adding bone constraints")
            utils.add_bone_constraints(armature_obj)

            # Adjust view
            bpy.ops.object.mode_set(mode="OBJECT")
            # Select armature object
            bpy.ops.object.select_all(action="DESELECT")
            armature_obj.select_set(True)
            context.view_layer.objects.active = armature_obj

            log.debug("Successfully imported %s bones", len(bones))
            return {"FINISHED"}

        except Exception as e:
            log.debug("Error during import: %s", str(e))
            return {"CANCELLED"}
