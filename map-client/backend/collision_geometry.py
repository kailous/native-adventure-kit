"""Conservative obstacle bounds; these are never accepted as ground surfaces."""
import itertools
import math
import struct


def finite(values):
    return all(not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) and abs(v) <= 1e8 for v in values)


def convex_bounds_from_blob(blob):
    """Decode the 1.0.0 convex family's packed float3 vertex view.

    The radius expands the hull or capsule segment. Unsupported families are
    rejected; bounds never establish the supporting ground surface.
    """
    if not isinstance(blob, bytes) or len(blob) < 72 or blob[24] not in (0,2,3,5):
        raise ValueError('尚未验证的碰撞形状类型')
    radius = struct.unpack_from('<f', blob, 32)[0]
    offset, count = struct.unpack_from('<iI', blob, 64)
    start = 64+offset
    valid_count = count == 8 if blob[24] == 5 else count == 2 if blob[24] == 2 else 4 <= count <= 256
    if not finite([radius]) or radius < 0 or not valid_count or offset < 8 or start+count*12 > len(blob):
        raise ValueError('无效的盒体顶点视图')
    vertices = [struct.unpack_from('<3f', blob, start+i*12) for i in range(count)]
    if not all(finite(v) for v in vertices):
        raise ValueError('无效的盒体顶点')
    bounds = [min(v[k] for v in vertices)-radius for k in range(3)]
    bounds += [max(v[k] for v in vertices)+radius for k in range(3)]
    if any(bounds[k] >= bounds[k+3] for k in range(3)):
        raise ValueError('退化的盒体几何')
    return bounds


def box_bounds_from_blob(blob):
    if not isinstance(blob, bytes) or len(blob) < 25 or blob[24] != 5:
        raise ValueError('尚未验证的碰撞形状类型')
    return convex_bounds_from_blob(blob)


def transform_bounds(bounds, poses, body_matrix=None):
    """Transform all corners through inner-to-outer instance transforms.

    poses are supplied in hierarchy order (outer first). The body stores the
    inverse transform, matching the independently verified terrain decoder.
    """
    if len(bounds) != 6 or not finite(bounds) or any(bounds[k] > bounds[k+3] for k in range(3)):
        raise ValueError('无效的碰撞范围')
    for pose in poses:
        q, t, s = pose['rotation'], pose['translation'], pose['scale']
        if len(q) != 4 or len(t) != 3 or len(s) != 3 or not finite([*q,*t,*s]) or abs(sum(v*v for v in q)-1) > .002 or any(v <= 0 for v in s):
            raise ValueError('无效的碰撞变换')
    if body_matrix is not None:
        if len(body_matrix) != 12 or not finite(body_matrix):
            raise ValueError('无效的物理体变换')
        for i in range(3):
            for j in range(3):
                if abs(sum(body_matrix[i*4+k]*body_matrix[j*4+k] for k in range(3))-(1 if i==j else 0)) > .002:
                    raise ValueError('非正交的物理体变换')
    points=[]
    for corner in itertools.product(*[(bounds[k],bounds[k+3]) for k in range(3)]):
        p=list(corner)
        for pose in reversed(poses):
            q,t,s=pose['rotation'],pose['translation'],pose['scale']
            v=[p[k]*s[k] for k in range(3)]
            c=[q[1]*v[2]-q[2]*v[1],q[2]*v[0]-q[0]*v[2],q[0]*v[1]-q[1]*v[0]]
            p=[v[0]+2*(q[3]*c[0]+q[1]*c[2]-q[2]*c[1])+t[0],
               v[1]+2*(q[3]*c[1]+q[2]*c[0]-q[0]*c[2])+t[1],
               v[2]+2*(q[3]*c[2]+q[0]*c[1]-q[1]*c[0])+t[2]]
        if body_matrix is not None:
            p=[sum(body_matrix[j*4+i]*(p[j]-body_matrix[j*4+3]) for j in range(3)) for i in range(3)]
        if not finite(p):raise ValueError('碰撞变换超出支持范围')
        points.append(p)
    return [min(p[k] for p in points) for k in range(3)]+[max(p[k] for p in points) for k in range(3)]
