"""Runs INSIDE Blender (blender -b … --python this). Measures the scene and renders chosen frames.

Arguments come as JSON in $EYEPROOF_ARGS (not argv, so a build script before us keeps its own `-- …` args):
  {"out": dir, "frames": [1, 60], "scale": 50, "samples": 8, "engine": "eevee", "camera": null, "render": true}
Writes <out>/blend.json and <out>/frame_####.png.
"""
import json
import os
import time

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

A = json.loads(os.environ.get("EYEPROOF_ARGS", "{}"))
OUT = A["out"]
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
r = sc.render
rep = {"blender": bpy.app.version_string, "file": bpy.data.filepath or "(built by script)", "facts": [], "frames": {}}

ENGINES = {"eevee": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"], "cycles": ["CYCLES"], "workbench": ["BLENDER_WORKBENCH"]}
if A.get("engine"):
    for e in ENGINES[A["engine"]]:
        try:
            r.engine = e
            break
        except TypeError:
            continue
if A.get("camera"):
    sc.camera = bpy.data.objects[A["camera"]]
if A.get("scale"):
    r.resolution_percentage = int(A["scale"])
if A.get("samples"):
    if r.engine == "CYCLES":
        sc.cycles.samples = int(A["samples"])
    elif hasattr(sc, "eevee"):
        sc.eevee.taa_render_samples = int(A["samples"])

rep["render"] = {"engine": r.engine, "resolution": [r.resolution_x, r.resolution_y], "percent": r.resolution_percentage,
                 "fps": r.fps / r.fps_base, "frames": [sc.frame_start, sc.frame_end],
                 "camera": sc.camera.name if sc.camera else None}
F = rep["facts"]

if not sc.camera:
    F.append("scene has no camera: nothing can render")

# assets that silently render magenta or black
for img in bpy.data.images:
    if img.source in {"FILE", "SEQUENCE", "MOVIE"} and not img.packed_file:
        path = bpy.path.abspath(img.filepath)
        if path and not os.path.exists(path):
            F.append(f"missing image file: {img.name} → {path} (renders magenta)")
meshes = [o for o in sc.objects if o.type == "MESH" and not o.hide_render]
no_mat = [o.name for o in meshes if not any(s.material for s in o.material_slots)]
if no_mat:
    F.append(f"{len(no_mat)} mesh(es) without material (render plain grey): {', '.join(no_mat[:8])}")
for m in bpy.data.materials:
    if m.users and getattr(m, "node_tree", None) and not any(n.type == "OUTPUT_MATERIAL" and n.inputs[0].links
                                                           for n in m.node_tree.nodes):
        F.append(f"material {m.name}: nothing connected to Material Output (renders black)")
lights = [o for o in sc.objects if o.type == "LIGHT" and not o.hide_render]
world_strength = 0.0
if sc.world and getattr(sc.world, "node_tree", None):
    for n in sc.world.node_tree.nodes:
        if n.type == "BACKGROUND":
            world_strength = max(world_strength, float(n.inputs["Strength"].default_value))
emissive = any(m.users and getattr(m, "node_tree", None) and any(n.type == "EMISSION" or (n.type == "BSDF_PRINCIPLED" and
               n.inputs["Emission Strength"].default_value > 0) for n in m.node_tree.nodes) for m in bpy.data.materials)
rep["light"] = {"lights": len(lights), "world_strength": world_strength, "emission": emissive}
if not lights and world_strength < 0.05 and not emissive:
    F.append("no lights, dark world, no emission: render will be black")


def framing(f):
    """Which objects the camera sees at frame f and how much of the picture each takes."""
    sc.frame_set(f)
    cam = sc.camera
    seen, notes = [], []
    if not cam:
        return seen, notes
    deps = bpy.context.evaluated_depsgraph_get()
    cam_loc = cam.matrix_world.translation
    for o in meshes:
        oe = o.evaluated_get(deps)
        corners = [oe.matrix_world @ Vector(c) for c in oe.bound_box]
        mn = Vector([min(c[i] for c in corners) for i in range(3)])
        mx = Vector([max(c[i] for c in corners) for i in range(3)])
        if all(mn[i] - 0.01 <= cam_loc[i] <= mx[i] + 0.01 for i in range(3)) and (mx - mn).length < 50:
            notes.append(f"camera is inside the bounds of {o.name}")
        ndc = [world_to_camera_view(sc, cam, c) for c in corners]
        if all(p.z < 0 for p in ndc):
            continue
        xs = [p.x for p in ndc if p.z > 0]
        ys = [p.y for p in ndc if p.z > 0]
        x0, x1, y0, y1 = max(min(xs), 0), min(max(xs), 1), max(min(ys), 0), min(max(ys), 1)
        if x1 <= x0 or y1 <= y0:
            continue
        area = (x1 - x0) * (y1 - y0)
        cut = [n for n, hit in (("left", min(xs) < 0), ("right", max(xs) > 1), ("bottom", min(ys) < 0),
                                ("top", max(ys) > 1)) if hit]
        seen.append({"object": o.name, "area": round(area, 3), "cut": cut})
    seen.sort(key=lambda s: -s["area"])
    return seen[:12], notes


frames = A.get("frames") or [sc.frame_current]
for f in frames:
    seen, notes = framing(f)
    entry = {"in_view": seen, "notes": notes}
    if A.get("render", True) and sc.camera:
        r.filepath = os.path.join(OUT, f"frame_{f:04d}.png")
        r.image_settings.file_format = "PNG"
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        entry.update(file=r.filepath, seconds=round(time.time() - t0, 2))
    rep["frames"][str(f)] = entry

with open(os.path.join(OUT, "blend.json"), "w") as fh:
    json.dump(rep, fh, indent=2)
print("EYEPROOF_DONE", os.path.join(OUT, "blend.json"))
