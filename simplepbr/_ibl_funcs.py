# pylint: disable=invalid-name
import functools
import math
import struct

import panda3d.core as p3d


def calc_vector(dim, face_idx, xloc, yloc):
    # Remap [0, dimension] to [-1, 1]
    xcoord = xloc / (dim - 1) * 2 - 1
    ycoord = 1 - yloc / (dim - 1) * 2

    if face_idx == 0:
        vec = p3d.LVector3(1, ycoord, -xcoord)
    elif face_idx == 1:
        vec = p3d.LVector3(-1, ycoord, xcoord)
    elif face_idx == 2:
        vec = p3d.LVector3(xcoord, 1, -ycoord)
    elif face_idx == 3:
        vec = p3d.LVector3(xcoord, -1, ycoord)
    elif face_idx == 4:
        vec = p3d.LVector3(xcoord, ycoord, 1)
    elif face_idx == 5:
        vec = p3d.LVector3(-xcoord, ycoord, -1)

    return vec


def calc_sphere_quadrant_area(x, y):
    return math.atan2(x*y, math.sqrt(x*x + y*y  + 1))


def calc_solid_angle(invdim, x, y):
    s = ((x + 0.5) * 2 * invdim) - 1
    t = ((y + 0.5) * 2 * invdim) - 1
    x0 = s - invdim
    y0 = t - invdim
    x1 = s + invdim
    y1 = t + invdim

    return calc_sphere_quadrant_area(x0, y0) - \
        calc_sphere_quadrant_area(x0, y1) - \
        calc_sphere_quadrant_area(x1, y0) + \
        calc_sphere_quadrant_area(x1, y1)


def get_sh_basis_from_vector(vec):
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

def get_sh_coeffs_from_cube_map(texcubemap):
    if texcubemap.z_size != 6:
        raise RuntimeError('supplied texture was not a cube map')
    if texcubemap.x_size != texcubemap.y_size:
        raise RuntimeError('supplied cube map is using unsupported, non-square dimensions')
    if not texcubemap.might_have_ram_image:
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
    samples = (
        (face, x, y)
        for face in range(texcubemap.z_size)
        for x in range(texcubemap.x_size)
        for y in range(texcubemap.y_size)
    )

    for sample in samples:
        # Grab the color value
        peeker.fetch_pixel(colorptr, *sample[1:], sample[0])
        color = colorptr.get_xyz()

        # Use SA as a weight to better handle corners (box vs sphere)
        color *= calc_solid_angle(invdim, *sample[1:])

        # Multiply color by SH basis and add results
        vec = calc_vector(dim, *sample)
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
    result = 0
    denom = 1

    while idx:
        denom *= base
        idx, rem = divmod(idx, base)
        result += rem / denom

    return result


@functools.cache
def hammersley(idx: int, maxnum: int) -> p3d.LVector2:
    return p3d.LVector2(idx / maxnum, van_der_corput(idx))


@functools.cache
def importance_sample_ggx(xi: p3d.LVector2, normal: p3d.LVector3, roughness: float) -> p3d.LVector3:
    alpha = roughness * roughness

    phi = 2 * math.pi * xi.x
    costheta = math.sqrt((1 - xi.y) / (1 + (alpha * alpha - 1) * xi.y))
    sintheta = math.sqrt(1 - costheta * costheta)

    hvec = p3d.LVector3(
        math.cos(phi) * sintheta,
        math.sin(phi) * sintheta,
        costheta
    )

    upvec = p3d.LVector3(0, 0, 1) if abs(normal.z < 0.999) else p3d.LVector3(1, 0, 0)
    tangent = upvec.cross(normal)
    tangent.normalize()
    bitangent = normal.cross(tangent)

    return (tangent * hvec.x + bitangent * hvec.y + normal * hvec.z).normalized()

def geometry_schlick_ggx(ndotv: float, roughness: float) -> float:
    alpha = roughness
    kibl = alpha * alpha / 2

    return ndotv / (ndotv * (1 - kibl) + kibl)


def geometry_smith(normal: p3d.LVector3, view: p3d.LVector3, light: p3d.LVector3, roughness: float) -> float:
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

    def calc_sample(idx: int):
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

    _ = [calc_sample(idx) for idx in range(num_samples)]

    retval /= num_samples
    return retval


def gen_brdf_lut(lutsize: int, num_samples: int = 1024) -> p3d.Texture:
    brdflut = p3d.Texture('brdf_lut')
    brdflut.setup_2d_texture(lutsize, lutsize, p3d.Texture.T_float, p3d.Texture.F_rg16)

    handle = brdflut.modify_ram_image()
    pixelsize = brdflut.component_width * brdflut.num_components
    xsize = brdflut.x_size

    for ycoord in range(lutsize):
        for xcoord in range(lutsize):
            idx = (ycoord * xsize + xcoord) * pixelsize
            result = integrate_brdf(xcoord / lutsize, ycoord / lutsize, num_samples)
            struct.pack_into('ff', handle, idx, result[1], result[0])

    return brdflut


def filter_sample(pos: p3d.LVector3, envmap: p3d.TexturePeeker, roughness: float, num_samples: int) -> p3d.LVector3:
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
            envmap.lookup(colorptr, *pos)
            retval += colorptr.xyz * ndotl
            totweight += ndotl

    retval /= totweight
    return retval


def filter_env_map(envmap: p3d.Texture, filtered: p3d.Texture, *, size: int = 16, num_mipmaps: int = 4, num_samples: int = 4) -> p3d.Texture:
    peeker = envmap.peek()

    filtered.setup_cube_map(size, p3d.Texture.T_float, p3d.Texture.F_rgb32)
    filtered.magfilter = p3d.SamplerState.FT_linear
    filtered.minfilter = p3d.SamplerState.FT_linear_mipmap_linear

    pixelsize = filtered.component_width * filtered.num_components

    for i in range(num_mipmaps):
        mipsize = int(size * 0.5 ** i)
        roughness = i / num_mipmaps
        texdata = p3d.PTA_uchar.empty_array(mipsize * mipsize * 6 * pixelsize)
        coords = (
            (face, x, y)
            for face in range(6)
            for x in range(mipsize)
            for y in range(mipsize)
        )

        for coord in coords:
            face, xcoord, ycoord = coord
            offset = ((face * mipsize + ycoord) * mipsize + xcoord) * pixelsize
            pos = calc_vector(mipsize, face, xcoord, ycoord)
            result = filter_sample(pos, peeker, roughness, num_samples)
            struct.pack_into('fff', texdata, offset, result[2], result[1], result[0])
        filtered.set_ram_mipmap_image(i, texdata)
