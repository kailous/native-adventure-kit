"""Conservative body-volume checks over world collision geometry.

This does not classify water, resolve collision filters, or prove coverage.
Callers must establish those facts before marking a navigation cell walkable.
"""
import math


def _values(values):
    return all(type(v) in (int, float) and math.isfinite(v) for v in values)


def triangle_intersects_box(triangle, bounds):
    """Separating-axis test, including vertical walls missed by height rays."""
    if len(bounds) != 6 or not _values(bounds) or any(bounds[k] > bounds[k+3] for k in range(3)):
        raise ValueError('Invalid body volume')
    if len(triangle) != 3 or any(len(p) != 3 or not _values(p) for p in triangle):
        raise ValueError('Invalid collision triangle')
    center = [(bounds[k]+bounds[k+3])/2 for k in range(3)]
    extent = [(bounds[k+3]-bounds[k])/2 for k in range(3)]
    points = [[p[k]-center[k] for k in range(3)] for p in triangle]
    edges = [[points[(i+1)%3][k]-points[i][k] for k in range(3)] for i in range(3)]

    def cross(a, b):
        return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]

    unit_axes = [[1,0,0], [0,1,0], [0,0,1]]
    axes = unit_axes+[cross(edges[0], edges[1])]
    axes += [cross(edge, axis) for edge in edges for axis in unit_axes]
    for axis in axes:
        length = math.sqrt(sum(v*v for v in axis))
        if length < 1e-12:
            continue
        axis = [v/length for v in axis]
        projections = [sum(p[k]*axis[k] for k in range(3)) for p in points]
        radius = sum(extent[k]*abs(axis[k]) for k in range(3))
        if min(projections) > radius+1e-7 or max(projections) < -radius-1e-7:
            return False
    return True


def bounds_intersect(a, b):
    for bounds in (a,b):
        if len(bounds) != 6 or not _values(bounds) or any(bounds[k] > bounds[k+3] for k in range(3)):
            raise ValueError('Invalid collision bounds')
    return all(a[k] <= b[k+3] and b[k] <= a[k+3] for k in range(3))
