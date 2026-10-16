"""Save editable models without the author's file-browser home directory."""
import bpy


def save_source(path):
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == 'FILE_BROWSER' and space.params:
                    # Blender's fixed-size directory buffer retains bytes past the terminator.
                    space.params.directory = b'/' * 1023
                    space.params.directory = b'//'
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
