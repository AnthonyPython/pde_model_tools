# __init__.py
import bpy

from . import ui,log
from .anim.operator import ImportAnimClass
from .mesh_map.operator import ImportMeshMapClass
from .mesh_prop.operator import ImportMeshPropClass
from .mesh_wcm.operator import ImportMeshWCMClass
from .skel.operator import ImportSkelClass

# 类表
classes = (
    ui.ImportPanel,
    ImportMeshPropClass,
    ImportMeshMapClass,
    ImportMeshWCMClass,
    ImportAnimClass,
    ImportSkelClass,
)


# 注册和注销函数
def register():
    """注册类"""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """注销类"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
