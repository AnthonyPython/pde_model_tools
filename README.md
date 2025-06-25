# PDE Model Tools

PDE Model Tools is a Blender add-on for importing models used by PDE based games. It provides operators to load `.mesh`, `.anim` and `.skel` files directly into Blender and exposes them in a panel in the 3D Viewport sidebar.

## Installation

1. Build or download the add-on as a `.zip` archive.
   - You can run `Build.bat` on Windows to create a zip using Blender's extension build command.
2. In Blender, open **Edit > Preferences...** and switch to the **Add-ons** tab.
3. Click **Install...**, choose the zip file and enable the *PDE Model Tools* add-on.

## Basic Usage

After enabling the add-on a new **PMT** panel appears in the **3D Viewport &rarr; Sidebar**. Use the buttons inside this panel to import:

- `mesh_prop` files for props
- `mesh_map` files for map geometry
- `mesh_wcm` files for weapons/characters
- `.anim` animation files
- `.skel` skeleton files

Select a file when prompted and it will be loaded into the current scene.
