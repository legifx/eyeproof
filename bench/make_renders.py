"""Builds bench/fixtures/renders/<variant>.blend: one small 3D scene, each variant with one planted 3D defect.
Run: blender -b --python "$PWD/bench/make_renders.py"  (absolute path: the flatpak runs in /app/blender)"""
import math
import os

import bpy

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "renders")
os.makedirs(OUT, exist_ok=True)


def mat(name, rgb, image=None):
    m = bpy.data.materials.new(name)
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = 0.7
    if image:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        img = bpy.data.images.new(image, 8, 8)
        img.source, img.filepath = "FILE", f"//textures/{image}.png"
        tex.image = img
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def add(op, name, m, **kw):
    op(**kw)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    return o


def build(v):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    add(bpy.ops.mesh.primitive_plane_add, "Grass", mat("Grass", (0.25, 0.45, 0.18)), size=30)
    wall = add(bpy.ops.mesh.primitive_cube_add, "Wall", mat("Plaster", (0.82, 0.78, 0.7)), location=(0, 3, 1.5))
    wall.scale = (6, 0.15, 1.5)
    # table: top + four legs, standing on the grass unless it floats
    lift = 0.7 if v == "floating" else 0.0
    wood = mat("Wood", (0.45, 0.28, 0.15), image="oak_diffuse" if v == "magenta" else None)
    top = add(bpy.ops.mesh.primitive_cube_add, "TableTop", wood, location=(1.6, 0.6, 0.8 + lift))
    top.scale = (0.8, 0.5, 0.05)
    for i, (dx, dy) in enumerate(((-0.7, -0.4), (0.7, -0.4), (-0.7, 0.4), (0.7, 0.4))):
        leg = add(bpy.ops.mesh.primitive_cube_add, f"Leg{i}", wood, location=(1.6 + dx, 0.6 + dy, 0.38 + lift))
        leg.scale = (0.05, 0.05, 0.38)
    add(bpy.ops.mesh.primitive_cylinder_add, "Mug", mat("Ceramic", (0.9, 0.9, 0.92)),
        radius=0.08, depth=0.18, location=(1.4, 0.6, 0.94 + lift))
    # character: body + head; in "clipping" it stands inside the table, body through the table top
    cx, cy = (1.75, 0.6) if v == "clipping" else (-0.6, 0.3)
    skin, shirt = mat("Skin", (0.85, 0.62, 0.48)), mat("Shirt", (0.15, 0.3, 0.75))
    add(bpy.ops.mesh.primitive_cylinder_add, "Body", shirt, radius=0.32, depth=1.3, location=(cx, cy, 0.65))
    add(bpy.ops.mesh.primitive_uv_sphere_add, "Head", skin, radius=0.24, location=(cx, cy, 1.55))
    # tree: trunk + crown; in "upside_down" the crown cone points down
    add(bpy.ops.mesh.primitive_cylinder_add, "Trunk", mat("Bark", (0.3, 0.2, 0.12)), radius=0.12, depth=1.0,
        location=(-2.6, 1.2, 0.5))
    crown = add(bpy.ops.mesh.primitive_cone_add, "Crown", mat("Leaves", (0.12, 0.38, 0.12)), radius1=0.8, depth=1.5,
                location=(-2.6, 1.2, 1.75))
    if v == "upside_down":
        crown.rotation_euler = (math.pi, 0, 0)
    bpy.ops.object.light_add(type="SUN", location=(4, -4, 8))
    sun = bpy.context.object
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(45), 0, math.radians(35))
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.7, 0.9, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    # camera: full scene; in "cropped" it is pushed in and down so the character's head leaves the frame
    bpy.ops.object.empty_add(location=(-0.2, 0.5, 0.9 if v != "cropped" else 0.45))
    target = bpy.context.object
    loc = (0, -9.5, 2.3) if v != "cropped" else (-0.3, -3.6, 0.7)
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    c = cam.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.camera = cam
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{v}.blend"))


for variant in ("clean", "floating", "clipping", "cropped", "upside_down", "magenta"):
    build(variant)
    print("built", variant)
