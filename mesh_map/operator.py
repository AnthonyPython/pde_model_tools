# mesh_map\operator.py
import math
import os

import bpy

from . import utils


# Operator definition
class ImportMeshMapClass(bpy.types.Operator):
    """Import a .mesh file"""

    bl_idname = "import.mesh_map"
    bl_label = "Import .mesh map model"
    bl_options = {"REGISTER", "UNDO"}
    # File path property
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="")  # type: ignore
    # Extension filter
    filename_ext = ".mesh"
    filter_glob: bpy.props.StringProperty(default="*.mesh", options={"HIDDEN"})  # type: ignore

    def execute(self, context):
        # Remove objects from the scene
        # bpy.ops.object.select_all(action="SELECT")
        # bpy.ops.object.delete()

        try:
            # Path to data file
            file_path = self.filepath
            # Verify the file exists
            if not os.path.exists(file_path):
                self.report({"ERROR"}, "File does not exist. Check the path")
                return {"CANCELLED"}

            # Read binary file
            data = None
            with open(file_path, "rb") as file:
                data = file.read()

            # File name without extension
            mesh_name = os.path.splitext(os.path.basename(file_path))[0]

            # Split mesh data
            mesh_obj = utils.split_mesh(self, data)

            # Loop index
            idx = 0
            # Read data blocks
            for this_obj in mesh_obj:
                # Vertex data
                vertices = this_obj["vertices"]["data"]
                # Face data
                faces = this_obj["faces"]["data"]
                # Normal data
                normals = this_obj["normals"]
                # UV coordinates
                uvs = this_obj["uvs"]

                # Create new mesh
                new_mesh = bpy.data.meshes.new(f"{mesh_name}_{idx}")
                new_obj = bpy.data.objects.new(f"{mesh_name}_{idx}", new_mesh)

                # Link object to scene
                context.collection.objects.link(new_obj)

                # Create vertices and faces
                new_mesh.from_pydata(vertices, [], faces)

                # Create UV layer
                uv_layer = new_mesh.uv_layers.new(name="UVMap")

                # Set UV for each loop
                for face in new_mesh.polygons:
                    for loop_idx in face.loop_indices:
                        # Vertex index
                        vertex_idx = new_mesh.loops[loop_idx].vertex_index
                        # Set UV
                        uv_layer.data[loop_idx].uv = uvs[vertex_idx]

                # Enable smooth shading
                new_mesh.shade_smooth()

                # Prepare normals
                loop_normals = []
                for poly in new_mesh.polygons:
                    for vertex_idx in poly.vertices:
                        loop_normals.append(normals[vertex_idx])

                # Set custom normals
                new_mesh.normals_split_custom_set(loop_normals)

                # Update mesh
                new_mesh.update()

                # Set object location
                new_obj.location = (0, 0, 0)
                # Use Euler rotation mode
                new_obj.rotation_mode = "XYZ"
                # Rotate X by 90 degrees (radians)
                new_obj.rotation_euler = (math.radians(90), 0, 0)

                # Increment index
                idx += 1

            self.report({"INFO"}, "Model loaded successfully")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to load map model: {e}")
            utils.traceback.print_exc()
            return {"CANCELLED"}

    # Display file selector
    def invoke(self, context, event):
        # Invoke file selector
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
