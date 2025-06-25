# ui.py
import bpy


class ImportPanel(bpy.types.Panel):
    """Import panel."""

    bl_label = "PDE Model Tools"
    bl_idname = "PDEIMPORT_PT_import_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PMT"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Import MESH")
        layout.operator("import.mesh_prop", text="Prop Model")
        layout.operator("import.mesh_map", text="Map Model")
        layout.operator("import.wcm_mesh", text="Weapon/Character Model")
        layout.label(text="Import ANIM")
        layout.operator("import.anim", text="Import Animation", icon="IMPORT")
        layout.label(text="Import SKEL")
        layout.operator("import.skel", text="Import Skeleton", icon="IMPORT")
