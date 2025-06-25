# anim\operator.py
import os
import struct

import bmesh
import bpy

from ..log import log
from .utils import is_valid_group_name, quat_to_eul


# Operator definition
class ImportAnimClass(bpy.types.Operator):
    """Import an game .anim file"""

    bl_idname = "import.anim"
    bl_label = "Import .anim"
    bl_options = {"REGISTER", "UNDO"}

    # File path property
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH",
        default="",
    )  # type: ignore
    # Extension filter
    filename_ext = ".anim"
    filter_glob: bpy.props.StringProperty(default="*.anim", options={"HIDDEN"})  # type: ignore

    # Show file selector
    def invoke(self, context, event):
        # Configure file dialog
        # selffilepath = bpy.props.StringProperty(
        #     subtype="FILE_PATH", default=self.filepath
        # )
        # Filter for .anim files
        self.filter_glob = "*.anim;"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    # run code
    def execute(self, context):
        # Path to the file
        file_path = self.filepath

        # Verify the file exists
        if not os.path.exists(file_path):
            self.report({"ERROR"}, "File does not exist. Check the path")
            return {"CANCELLED"}

        # Read the file
        with open(file_path, "rb") as file:
            data = file.read()

        # Extract file name without extension
        file_name = os.path.splitext(os.path.basename(file_path))[0]

        # Parse animation data
        vertex_groups = self.parse_anim_file(data, file_name)

        # Determine total frame count
        total_frames = max(len(group_data) for group_data in vertex_groups.values())
        log.debug("Total frames: %s", total_frames)

        # Set Blender scene frame range
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = total_frames

        # Create animation
        for group_name, group_data in vertex_groups.items():
            # Create a cube mesh
            mesh = bpy.data.meshes.new(name=group_name)
            # Create a cube object
            obj = bpy.data.objects.new(name=group_name, object_data=mesh)
            # Link to scene
            context.collection.objects.link(obj)

            # Make it active
            bpy.context.view_layer.objects.active = obj
            # Save current mode
            current_mode = bpy.context.object.mode
            # Ensure object mode
            bpy.ops.object.mode_set(mode="OBJECT")

            # Add cube data
            bm = bmesh.new()
            # Size 0.1
            bmesh.ops.create_cube(bm, size=0.1)
            bm.to_mesh(mesh)
            bm.free()

            # Restore mode
            bpy.ops.object.mode_set(mode=current_mode)
            # Update mesh
            mesh.update()

            # Insert location and rotation keyframes
            for frame, transform in enumerate(group_data):
                # Location keyframe
                obj.location = transform["location"]
                obj.keyframe_insert(data_path="location", frame=frame)

                # Rotation keyframe (Euler)
                obj.rotation_euler = transform["rotation"]
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)

        self.report({"INFO"}, f"{file_name} animation loaded")
        return {"FINISHED"}

    # Parse and retrieve frame data
    def parse_anim_file(self, data, file_name):
        log.debug("Processing %s", file_name)

        # All vertex group info
        all_group = []
        # End offset of current group
        group_eoffset = 0
        # First feature
        first_feature = 0
        # Current file size used as end position
        file_size = len(data)
        # Some files include their own name with unknown data following it.
        # Find it and adjust the end offset accordingly.
        possible_end_offset = data.find(file_name.encode("utf-8"), 0)
        if possible_end_offset != -1:
            # Jump before the name length
            file_size = possible_end_offset - 4

        # Find vertex groups
        log.debug("Begin searching vertex groups")
        while True:
            # File analysis https://www.cnblogs.com/letleon/p/18511408
            try:
                # Vertex group name length
                group_name_length = struct.unpack(
                    "I", data[group_eoffset: group_eoffset + 4]
                )[0]
                # Check length limit
                if group_name_length > 63:
                    log.debug(
                        "!Name length %s exceeds Blender limit of 63 %s", group_name_length
                    )
                    break
                log.debug("Group name length: %s", group_name_length)

                # Read group name
                group_name = data[
                             group_eoffset + 4: group_eoffset + 4 + group_name_length
                             ].decode("utf-8")
                # Validate name
                if not is_valid_group_name(group_name):
                    log.debug("!Invalid name: %s", group_name)
                    break
                log.debug("Group name: %s", group_name)

                # Number of frames in group -> end offset
                frames_number = struct.unpack(
                    "I",
                    data[
                    group_eoffset
                    + 4
                    + group_name_length: group_eoffset
                                         + 4
                                         + group_name_length
                                         + 4
                    ],
                )[0]
                if frames_number == 0:
                    log.debug("!Frame count is zero: %s", frames_number)
                    break
                log.debug("Frame count: %s", frames_number)

                # Read 8-byte feature
                this_feature = data[
                               group_eoffset
                               + 4
                               + group_name_length: group_eoffset
                                                    + 4
                                                    + group_name_length
                                                    + 8
                               ]  # feature is 8 bytes
                # Ensure it matches the first feature
                if first_feature == 0:
                    if this_feature == 0:
                        log.debug("!Feature cannot be zero: %s", this_feature.hex())
                        break
                    first_feature = this_feature
                elif this_feature != first_feature:
                    log.debug("!Feature mismatch: %s", this_feature.hex())
                    break
                log.debug("Feature: %s", this_feature.hex())

                # Calculate start offset of group data
                this_group_soffset = group_eoffset + 4 + group_name_length + 8
                log.debug("Group start offset: %s", this_group_soffset)

                # Calculate end position of group data
                group_eoffset = (
                        frames_number * 0x1C + group_eoffset + 4 + group_name_length + 8
                )
                if group_eoffset > file_size:
                    log.debug("!Group end offset out of range: %s", group_eoffset)
                    break
                log.debug("Group end offset: %s", group_eoffset)

                # Append to all_group
                log.debug("Adding to all_group")
                # Add the current vertex group
                all_group.append(
                    {
                        "name": group_name,
                        "soffset": this_group_soffset,
                        "eoffset": group_eoffset,
                    }
                )

                # Exit normally
                if group_eoffset == file_size:
                    log.debug("!Reached end while searching")
                    break
            except NameError:
                log.debug("!Data read error, stop searching")
                break

        log.debug("Finished finding %s vertex groups", len(all_group))

        # Vertex group frame data
        vertex_groups = {}
        # Retrieve all vertex group frames
        for now_group in all_group:
            # Name
            group_name = now_group["name"]
            log.debug("Name: %s", group_name)

            # Add to vertex_groups
            if group_name not in vertex_groups:
                vertex_groups[group_name] = []

            # Current group start offset
            soffset = now_group["soffset"]
            # Current group end offset
            eoffset = now_group["eoffset"]
            # log.debug("soffset: %s eoffset: %s",soffset,eoffset)
            # Read vertex group frame data
            while soffset < eoffset:
                # Ensure enough remaining data
                if eoffset - soffset < 28:
                    log.debug("!Data less than 28 bytes")
                    # Break if insufficient
                    break
                # Read 28-byte block
                frame_data = data[soffset: soffset + 28]
                # Location
                location = struct.unpack("3f", frame_data[0:12])
                # Quaternion -> will later convert to Euler
                rotation = struct.unpack("3f", frame_data[12:24])
                # Add to vertex_groups
                vertex_groups[group_name].append(
                    {"location": location, "rotation": rotation}
                )
                # Advance to next frame
                soffset += 28

        log.debug("Finished reading %s vertex group frames", len(vertex_groups))
        # Return vertex group frames
        return vertex_groups
