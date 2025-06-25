@echo off
setlocal enabledelayedexpansion

REM iterate over all .zip files in the current directory
for %%f in (*.zip) do (
    echo Found zip file: %%f
    "D:\Apps\Blender\Blender 4.2.3\blender.exe" --command extension validate "%%f"
)

pause