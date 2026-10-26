"""Vertical surface queries over decoded world-space collision triangles.

This is geometry only. A height hit does not establish clearance, hazard
classification or a complete navigation mesh.
"""
import math


def vertical_hits(triangles, x, z):
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (x, z)):
        raise ValueError('无效的表面查询坐标')
    hits = []
    for triangle in triangles:
        if len(triangle) != 3 or any(len(p) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in p) for p in triangle):
            raise ValueError('无效的碰撞三角形')
        a, b, c = triangle
        if not min(p[0] for p in triangle)-1e-7 <= x <= max(p[0] for p in triangle)+1e-7 or not min(p[2] for p in triangle)-1e-7 <= z <= max(p[2] for p in triangle)+1e-7:
            continue
        determinant = (b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
        if abs(determinant) < 1e-10:
            continue
        u = ((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/determinant
        v = ((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/determinant
        if u < -1e-7 or v < -1e-7 or u+v > 1+1e-7:
            continue
        d, e = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
        normal = [d[1]*e[2]-d[2]*e[1], d[2]*e[0]-d[0]*e[2], d[0]*e[1]-d[1]*e[0]]
        length = math.sqrt(sum(n*n for n in normal))
        if length < 1e-10:
            continue
        normal = [n/length for n in normal]
        hits.append({'height': u*a[1]+v*b[1]+(1-u-v)*c[1], 'normal': normal,
                     'upward': normal[1] > 0, 'slopeDegrees': math.degrees(math.acos(min(1, abs(normal[1]))))})
    return sorted(hits, key=lambda hit: hit['height'])


def supporting_surface(triangles, x, z, foot_height, tolerance=.15):
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (foot_height, tolerance)) or tolerance < 0:
        raise ValueError('无效的脚下高度或容差')
    candidates = [hit for hit in vertical_hits(triangles, x, z) if hit['upward'] and abs(hit['height']-foot_height) <= tolerance]
    return min(candidates, key=lambda hit: abs(hit['height']-foot_height)) if candidates else None
