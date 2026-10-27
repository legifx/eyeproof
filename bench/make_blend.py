"""Builds bench/fixtures/scene.blend with planted problems (run: blender -b --python bench/make_blend.py).
Missing texture on the crate (renders magenta), a sphere without material, a pillar cut by the right frame edge."""
import math
import os

import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.frame_start, sc.frame_end = 1, 48

bpy.ops.mesh.primitive_plane_add(size=20)
ground = bpy.context.object
gm = bpy.data.materials.new("Ground"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.35, 0.4, 0.3, 1)
ground.data.materials.append(gm)

bpy.ops.mesh.primitive_cube_add(size=1.6, location=(0, 0, 0.8))
crate = bpy.context.object; crate.name = "Crate"
cm = bpy.data.materials.new("CrateWood"); cm.use_nodes = True
tex = cm.node_tree.nodes.new("ShaderNodeTexImage")
img = bpy.data.images.new("crate_diffuse", 8, 8); img.source = "FILE"; img.filepath = "//textures/crate_diffuse.png"
tex.image = img
cm.node_tree.links.new(tex.outputs["Color"], cm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
crate.data.materials.append(cm)
crate.location.x = -1.5
crate.keyframe_insert("location", frame=1)
crate.location.x = 1.5
crate.keyframe_insert("location", frame=48)

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(-3.2, 1.5, 0.6))
bpy.context.object.name = "Ball"

bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=4, location=(3.7, 0.5, 2))
bpy.context.object.name = "Pillar"
pm = bpy.data.materials.new("Stone"); pm.use_nodes = True
bpy.context.object.data.materials.append(pm)

bpy.ops.object.light_add(type="SUN", location=(4, -4, 8))
bpy.context.object.data.energy = 3
bpy.context.object.rotation_euler = (math.radians(40), 0, math.radians(30))
bpy.ops.object.camera_add(location=(0, -9, 3.2), rotation=(math.radians(78), 0, 0))
sc.camera = bpy.context.object
world = bpy.data.worlds.new("World"); world.use_nodes = True; sc.world = world
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=out)
print("saved", out)
