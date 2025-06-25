# __init__.py
import bpy

from . import ui,log
from .anim.operator import ImportAnimClass
from .mesh_map.operator import ImportMeshMapClass
from .mesh_prop.operator import ImportMeshPropClass
from .mesh_wcm.operator import ImportMeshWCMClass
from .skel.operator import ImportSkelClass

# Class list
classes = (
    ui.ImportPanel,
    ImportMeshPropClass,
    ImportMeshMapClass,
    ImportMeshWCMClass,
    ImportAnimClass,
    ImportSkelClass,
)


# Registration helpers
def register():
    """Register classes."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister classes."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
