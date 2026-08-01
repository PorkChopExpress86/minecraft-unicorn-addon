"""
Renders a 3/4-view PNG of the unicorn model for the README, using the exact
same bone/cube data as the addon itself (tools/unicorn_model.py) -- so the
preview image can never show a different model than what actually ships.

This is a from-scratch software rasterizer (no PIL, no OpenGL): project each
cube face to 2D with a simple camera rotation, cull backfaces, and scanline-
fill each quad against a per-pixel depth buffer (not the painter's algorithm --
overlapping geometry like the mane hugging the neck interpenetrates in depth,
which a simple sort-by-average-depth gets wrong).

Usage: python tools/render_preview.py
"""

import math
import os

from png_writer import write_png
from unicorn_model import (
    FACE_ORDER,
    FACE_SHADE,
    iter_cubes,
    model_max,
    model_min,
    shade,
    to_world,
)

OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "preview.png")

CANVAS_W = 900
CANVAS_H = 900
PADDING = 60

# The model's head is at -Z, tail at +Z. A camera yaw near 0 looks at the tail
# end (head recedes into the distance); near 180 looks at the head end. Offset
# from 180 for a 3/4 angle that still shows the face prominently.
CAMERA_YAW_DEG = 145
CAMERA_PITCH_DEG = 18    # tilt down slightly, like a 3/4 product shot

SKY_TOP = (238, 232, 250, 255)      # pale lavender
SKY_BOTTOM = (255, 255, 255, 255)   # white
GROUND = (222, 240, 210, 255)       # soft grass green
SHADOW = (40, 40, 55, 90)

# Per-face local corner offsets (as fractions of cube size), wound so the
# cross product of (corner1-corner0) x (corner2-corner0) points outward.
FACE_CORNERS = {
    "north": [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)],
    "south": [(1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 0, 1)],
    "east": [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
    "west": [(0, 0, 1), (0, 1, 1), (0, 1, 0), (0, 0, 0)],
    "up": [(0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)],
    "down": [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
}


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def normalize(v):
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    return (v[0] / length, v[1] / length, v[2] / length) if length > 1e-9 else v


def camera_rotate(v):
    """Pure rotation (no translation) -- valid for both points and normals."""
    x, y, z = v
    yaw = math.radians(CAMERA_YAW_DEG)
    x, z = x * math.cos(yaw) + z * math.sin(yaw), -x * math.sin(yaw) + z * math.cos(yaw)
    pitch = math.radians(CAMERA_PITCH_DEG)
    y, z = y * math.cos(pitch) - z * math.sin(pitch), y * math.sin(pitch) + z * math.cos(pitch)
    return (x, y, z)


def plane_from_points(p0, p1, p2):
    """Plane through 3 (x, y, z) points, as (a, b, c, d) for ax+by+cz+d=0."""
    v1 = sub(p1, p0)
    v2 = sub(p2, p0)
    a, b, c = cross(v1, v2)
    d = -(a * p0[0] + b * p0[1] + c * p0[2])
    return a, b, c, d


def plane_z_at(plane, x, y):
    a, b, c, d = plane
    if abs(c) < 1e-9:
        return None  # polygon is edge-on to the screen -- no visible area
    return -(a * x + b * y + d) / c


def fill_convex_polygon(pixels, depth_buffer, width, height, points_3d, color):
    """points_3d: [(screen_x, screen_y, camera_z), ...] for a planar quad.

    Depth-tested per pixel rather than sorted whole-polygon-at-a-time --
    painter's algorithm (sort-by-average-depth) breaks down whenever two
    polygons interpenetrate in depth instead of cleanly layering, which is
    exactly what happens where the mane hugs the neck. Larger camera_z means
    closer to the camera (see camera_rotate/backface cull convention).
    """
    points_2d = [(p[0], p[1]) for p in points_3d]
    plane = plane_from_points(*points_3d[:3])

    ys = [p[1] for p in points_2d]
    y_min = max(0, int(math.floor(min(ys))))
    y_max = min(height - 1, int(math.ceil(max(ys))))
    n = len(points_2d)
    r, g, b, _ = color
    for y in range(y_min, y_max + 1):
        sample = y + 0.5
        xs = []
        for i in range(n):
            x1, y1 = points_2d[i]
            x2, y2 = points_2d[(i + 1) % n]
            if y1 == y2:
                continue
            lo, hi = (y1, y2) if y1 < y2 else (y2, y1)
            if lo <= sample < hi:
                t = (sample - y1) / (y2 - y1)
                xs.append(x1 + t * (x2 - x1))
        if len(xs) < 2:
            continue
        # Extend the span by half a pixel on each side so mathematically-
        # adjacent (but not pixel-grid-aligned) polygons don't leave a seam.
        x_start = max(0, int(math.floor(min(xs) - 0.5)))
        x_end = min(width - 1, int(math.ceil(max(xs) + 0.5)))
        for x in range(x_start, x_end + 1):
            z = plane_z_at(plane, x + 0.5, sample)
            if z is None or z < depth_buffer[y][x]:
                continue
            depth_buffer[y][x] = z
            pixels[y][x] = (r, g, b, 255)


def fill_ellipse(pixels, width, height, cx, cy, rx, ry, color):
    y_min = max(0, int(cy - ry))
    y_max = min(height - 1, int(cy + ry))
    for y in range(y_min, y_max + 1):
        dy = (y - cy) / ry
        span = math.sqrt(max(0.0, 1 - dy * dy))
        x_min = max(0, int(cx - rx * span))
        x_max = min(width - 1, int(cx + rx * span))
        for x in range(x_min, x_max + 1):
            base = pixels[y][x]
            t = color[3] / 255.0
            pixels[y][x] = (
                int(color[0] * t + base[0] * (1 - t)),
                int(color[1] * t + base[1] * (1 - t)),
                int(color[2] * t + base[2] * (1 - t)),
                255,
            )


def main():
    # --- Gather every face as world-space corners + base color ---
    model_center = (
        (model_min[0] + model_max[0]) / 2,
        (model_min[1] + model_max[1]) / 2,
        (model_min[2] + model_max[2]) / 2,
    )

    faces = []
    for bone, cube in iter_cubes():
        ox, oy, oz = cube["origin"]
        sx, sy, sz = cube["size"]
        face_colors = cube.get("face_colors", {})
        for face_name in FACE_ORDER:
            local_corners = [
                (ox + fx * sx, oy + fy * sy, oz + fz * sz)
                for fx, fy, fz in FACE_CORNERS[face_name]
            ]
            world_corners = [to_world(c, bone["name"]) for c in local_corners]
            normal = normalize(cross(sub(world_corners[1], world_corners[0]), sub(world_corners[2], world_corners[0])))
            color = shade(face_colors.get(face_name, cube["color"]), FACE_SHADE[face_name])
            faces.append((world_corners, normal, color))

    # --- Camera transform + backface cull ---
    camera_faces = []
    for world_corners, normal, color in faces:
        centered = [sub(c, model_center) for c in world_corners]
        cam_corners = [camera_rotate(c) for c in centered]
        cam_normal = camera_rotate(normal)
        if cam_normal[2] <= 0:
            continue  # facing away from the camera
        camera_faces.append((cam_corners, color))

    # --- Fit projection to canvas ---
    xs = [c[0] for corners, _ in camera_faces for c in corners]
    ys = [c[1] for corners, _ in camera_faces for c in corners]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    scale = min((CANVAS_W - 2 * PADDING) / span_x, (CANVAS_H - 2 * PADDING - 40) / span_y)
    mid_x = (max(xs) + min(xs)) / 2
    mid_y = (max(ys) + min(ys)) / 2

    def project(c):
        sx = CANVAS_W / 2 + (c[0] - mid_x) * scale
        sy = CANVAS_H / 2 - (c[1] - mid_y) * scale - 20  # small upward shift for ground clearance
        return (sx, sy)

    ground_y = project((0, min(ys), 0))[1]

    # --- Paint background: sky gradient + ground band ---
    pixels = [[(0, 0, 0, 0)] * CANVAS_W for _ in range(CANVAS_H)]
    horizon = int(ground_y + 90)
    for y in range(CANVAS_H):
        if y < horizon:
            t = y / max(1, horizon)
            color = tuple(int(SKY_TOP[i] * (1 - t) + SKY_BOTTOM[i] * t) for i in range(3)) + (255,)
        else:
            color = GROUND
        for x in range(CANVAS_W):
            pixels[y][x] = color

    # Soft ground shadow under the unicorn.
    shadow_cx = CANVAS_W / 2
    fill_ellipse(pixels, CANVAS_W, CANVAS_H, shadow_cx, ground_y + 8, 220, 40, SHADOW)

    # --- Rasterize model with a per-pixel depth buffer ---
    depth_buffer = [[float("-inf")] * CANVAS_W for _ in range(CANVAS_H)]
    for cam_corners, color in camera_faces:
        points_3d = [(*project(c), c[2]) for c in cam_corners]
        fill_convex_polygon(pixels, depth_buffer, CANVAS_W, CANVAS_H, points_3d, color)

    write_png(OUT_PATH, CANVAS_W, CANVAS_H, pixels)
    print(f"wrote {OUT_PATH} ({len(camera_faces)} faces rendered, {len(faces) - len(camera_faces)} culled)")


if __name__ == "__main__":
    main()
