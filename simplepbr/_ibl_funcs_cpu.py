from __future__ import annotations
# pylint: disable=invalid-name

import functools
import math
import struct
import typing
from typing import (
    Final,
)
from typing_extensions import (
    TypeAlias,
)

import panda3d.core as p3d

Vec2TupleType: TypeAlias = 'tuple[float, float]'
Vec3TupleType: TypeAlias = 'tuple[float, float, float]'
SHTupleType: TypeAlias = '''tuple[
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
]'''


def calc_vector(dim: int, face_idx: int, xloc: float, yloc: float) -> Vec3TupleType:
    maxidx = dim - 1
    # Remap [0, dimension] to [-1, 1]
    xcoord = xloc / maxidx * 2 - 1
    ycoord = (maxidx - yloc) / maxidx * 2 - 1

    # This should always be the largest component, so add some room for
    # xcoord or ycoord to be 1.0
    unitlength = 1.00001

    if face_idx == 0:
        vec = (unitlength, ycoord, -xcoord)
    elif face_idx == 1:
        vec = (-unitlength, ycoord, xcoord)
    elif face_idx == 2:
        vec = (xcoord, unitlength, -ycoord)
    elif face_idx == 3:
        vec = (xcoord, -unitlength, ycoord)
    elif face_idx == 4:
        vec = (xcoord, ycoord, unitlength)
    elif face_idx == 5:
        vec = (-xcoord, ycoord, -unitlength)

    return vec


def calc_solid_angle(invdim: float, x: int, y: int) -> float:
    s = ((x + 0.5) * 2 * invdim) - 1
    t = ((y + 0.5) * 2 * invdim) - 1
    x0 = s - invdim
    y0 = t - invdim
    x1 = s + invdim
    y1 = t + invdim

    x02 = x0 * x0
    y02 = y0 * y0
    x12 = x1 * x1
    y12 = y1 * y1

    return math.atan2(x0*y0, math.sqrt(x02 + y02  + 1)) - \
        math.atan2(x0*y1, math.sqrt(x02 + y12 + 1)) - \
        math.atan2(x1*y0, math.sqrt(x12 + y02 + 1)) + \
        math.atan2(x1*y1, math.sqrt(x12 + y12 + 1))


def get_sh_basis_from_vector(vec: Vec3TupleType) -> SHTupleType:
    vecx, vecy, vecz = vec
    return (
        0.282095,
        0.488603 * vecx,
        0.488603 * vecz,
        0.488603 * vecy,
        1.092548 * vecx * vecz,
        1.092548 * vecy * vecz,
        1.092548 * vecy * vecx,
        (0.946176 * vecz * vecz - 0.315392),
        0.546274 * (vecx * vecx - vecy * vecy),
    )

def get_sh_coeffs_from_cube_map(texcubemap: p3d.Texture) -> list[p3d.LVector3]:
    if texcubemap.z_size != 6:
        raise RuntimeError('supplied texture was not a cube map')
    if texcubemap.x_size != texcubemap.y_size:
        raise RuntimeError('supplied cube map is using unsupported, non-square dimensions')
    if not texcubemap.might_have_ram_image():
        raise RuntimeError('expected might_have_ram_image() to be true on supplied texture')

    peeker = texcubemap.peek()

    if peeker is None:
        raise RuntimeError('unable to get TexturePeeker for texture')

    dim = texcubemap.x_size
    invdim = 1.0 / dim

    shcoeffs = [
        p3d.LVector3(0, 0, 0),
        p3d.LVector3(0, 0, 0),
        p3d.LVector3(0, 0, 0),
        p3d.LVector3(0, 0, 0),
        p3d.LVector3(0, 0, 0),
        p3d.LVector3(0, 0, 0),
        p3d.LVector3(0, 0, 0),
        p3d.LVector3(0, 0, 0),
        p3d.LVector3(0, 0, 0),
    ]
    colorptr = p3d.LColor()

    # SH Basis
    for x in range(texcubemap.x_size):
        for y in range(texcubemap.y_size):
            sa = calc_solid_angle(invdim, x, y)
            for face in range(texcubemap.z_size):
                # Grab the color value
                peeker.fetch_pixel(colorptr, x, y, face)
                color = colorptr.xyz

                # Use SA as a weight to better handle corners (box vs sphere)
                color *= sa

                # Multiply color by SH basis and add results
                vec = calc_vector(dim, face, x, y)
                basis = get_sh_basis_from_vector(vec)
                for idx, value in enumerate(basis):
                    shcoeffs[idx] += color * value

    # Convolution with cosine lobe for irradiance
    # this is actually for reconstruction, but we can bake it in here to avoid
    # extra math in the shader
    a0 = 3.141593 # pi
    a1 = 2.094395 # 2/3 pi
    a2 = 0.785398 # 1/4 pi
    shcoeffs[0] *= a0
    shcoeffs[1] *= a1
    shcoeffs[2] *= a1
    shcoeffs[3] *= a1
    shcoeffs[4] *= a2
    shcoeffs[5] *= a2
    shcoeffs[6] *= a2
    shcoeffs[7] *= a2

    return shcoeffs


def van_der_corput(idx: int, base: int = 2) -> float:
    result = 0.0
    denom = 1

    while idx:
        denom *= base
        idx, rem = divmod(idx, base)
        result += rem / denom

    return result


@functools.cache
def hammersley(idx: int, maxnum: int) -> Vec2TupleType:
    return (idx / maxnum, van_der_corput(idx))


VEC_Z: Final = p3d.LVector3(0, 0, 1)
VEC_X: Final = p3d.LVector3(1, 0, 0)
def importance_sample_ggx(
    xi: Vec2TupleType,
    normal: p3d.LVector3,
    roughness: float
) -> p3d.LVector3:
    alpha = roughness * roughness

    phi = 2 * math.pi * xi[0]
    costheta = math.sqrt((1 - xi[1]) / (1 + (alpha * alpha - 1) * xi[1]))
    sintheta = math.sqrt(1 - costheta * costheta)

    hvec_x = math.cos(phi) * sintheta
    hvec_y = math.sin(phi) * sintheta
    hvec_z = costheta

    upvec = VEC_Z if abs(normal.z < 0.999) else VEC_X
    tangent = upvec.cross(normal)
    tangent.normalize()
    bitangent = normal.cross(tangent)

    return (tangent * hvec_x + bitangent * hvec_y + normal * hvec_z).normalized()

def geometry_schlick_ggx(ndotv: float, roughness: float) -> float:
    alpha = roughness
    kibl = alpha * alpha / 2

    return ndotv / (ndotv * (1 - kibl) + kibl)


def geometry_smith(
    normal: p3d.LVector3,
    view: p3d.LVector3,
    light: p3d.LVector3,
    roughness: float
) -> float:
    ndotv = max(normal.dot(view), 0)
    ndotl = max(normal.dot(light), 0)

    return geometry_schlick_ggx(ndotv, roughness) * geometry_schlick_ggx(ndotl, roughness)


def integrate_brdf(ndotv: float, roughness: float, num_samples: int = 1024) -> p3d.LVector2:
    ndotv = max(ndotv, 0.0001)
    view = p3d.LVector3(
        math.sqrt(1 - ndotv * ndotv),
        0,
        ndotv
    )
    normal = p3d.LVector3(0, 0, 1)
    retval = p3d.LVector2(0, 0)

    for idx in range(num_samples):
        xi = hammersley(idx, num_samples)
        hvec = importance_sample_ggx(xi, normal, roughness)
        light = hvec * 2 * view.dot(hvec) - view
        light.normalize()

        ndotl = max(light.z, 0)

        if ndotl > 0:
            ndoth = max(hvec.z, 0)
            vdoth = max(view.dot(hvec), 0)
            geom = geometry_smith(normal, view, light, roughness)
            geom_vis = (geom * vdoth) / (ndoth * ndotv)
            fresnel = math.pow(1 - vdoth, 5)

            retval.x += (1 - fresnel) * geom_vis
            retval.y += fresnel * geom_vis


    retval /= num_samples
    return retval


def gen_brdf_lut(lutsize: int, num_samples: int = 1024) -> p3d.Texture:
    brdflut = p3d.Texture('brdf_lut')
    brdflut.setup_2d_texture(lutsize, lutsize, p3d.Texture.T_float, p3d.Texture.F_rg16)
    brdflut.wrap_u = p3d.SamplerState.WM_clamp
    brdflut.wrap_v = p3d.SamplerState.WM_clamp
    brdflut.minfilter = p3d.SamplerState.FT_linear
    brdflut.magfilter = p3d.SamplerState.FT_linear

    handle = typing.cast(memoryview, brdflut.modify_ram_image())
    pixelsize = brdflut.component_width * brdflut.num_components
    xsize = brdflut.x_size

    for ycoord in range(lutsize):
        for xcoord in range(lutsize):
            idx = (ycoord * xsize + xcoord) * pixelsize
            result = integrate_brdf(xcoord / lutsize, ycoord / lutsize, num_samples)
            struct.pack_into('ff', handle, idx, result[0], result[1])

    return brdflut


def filter_sample(
    pos: p3d.LVector3,
    envmap: p3d.TexturePeeker,
    roughness: float,
    num_samples: int
) -> p3d.LVector3:
    view = normal = pos.normalized()
    totweight = 0.0
    retval = p3d.LVector3(0.0, 0.0, 0.0)
    colorptr = p3d.LColor()

    for idx in range(num_samples):
        xi = hammersley(idx, num_samples)
        hvec = importance_sample_ggx(xi, normal, roughness)
        light = hvec * 2.0 * view.dot(hvec) - view
        light.normalize()

        ndotl = max(normal.dot(light), 0.0)
        if ndotl > 0.0:
            envmap.lookup(colorptr, light.x, light.y, light.z)
            retval += colorptr.xyz * ndotl
            totweight += ndotl

    retval /= totweight
    return retval


def filter_env_map(
        envmap: p3d.Texture,
        filtered: p3d.Texture,
        *,
        size: int = 16,
        num_mipmaps: int = 4,
        num_samples: int = 4
    ) -> None:
    peeker = envmap.peek()

    filtered.setup_cube_map(size, p3d.Texture.T_float, p3d.Texture.F_rgb32)
    filtered.magfilter = p3d.SamplerState.FT_linear
    filtered.minfilter = p3d.SamplerState.FT_linear_mipmap_linear

    pixelsize = filtered.component_width * filtered.num_components

    for i in range(num_mipmaps):
        mipsize = int(size * 0.5 ** i)
        roughness = 1 if num_mipmaps == 1 else i / (num_mipmaps - 1)
        texdata = p3d.PTA_uchar.empty_array(mipsize * mipsize * 6 * pixelsize)

        for face in range(6):
            for xcoord in range(mipsize):
                for ycoord in range(mipsize):
                    offset = ((face * mipsize + ycoord) * mipsize + xcoord) * pixelsize
                    vec = calc_vector(mipsize, face, xcoord, ycoord)
                    pos = p3d.LVector3(vec[0], vec[1], vec[2])
                    result = filter_sample(pos, peeker, roughness, num_samples)
                    struct.pack_into(
                        'fff',
                        typing.cast(memoryview, texdata), offset, result[2], result[1], result[0]
                    )
        filtered.set_ram_mipmap_image(i, texdata)
