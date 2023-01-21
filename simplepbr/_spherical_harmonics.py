# pylint: disable=invalid-name
import math
import time


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

    # vec.normalize()
    return vec.x, vec.y, vec.z


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


def get_sh_coeffs_from_cube_map(texcubemap, irradiance=True):
    starttime = time.perf_counter()
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

    # SH Basis
    samples = (
        (face, x, y)
        for face in range(texcubemap.z_size)
        for x in range(texcubemap.x_size)
        for y in range(texcubemap.y_size)
    )
    for sample in samples:
        # Grab the color value
        color = p3d.LColor()
        peeker.fetch_pixel(color, *sample[1:], sample[0])
        color = color.get_xyz()

        # Use SA as a weight to better handle corners (box vs sphere)
        color *= calc_solid_angle(invdim, *sample[1:])

        # Multiply color by SH basis and add results
        vec = calc_vector(dim, *sample)
        basis = get_sh_basis_from_vector(vec)
        for idx, value in enumerate(basis):
            shcoeffs[idx] += color * value

    if irradiance:
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

    tottime = (time.perf_counter() - starttime) * 1000
    print(
        f'Spherical harmonics coefficients calculated in {tottime:.3f}ms'
    )
    return shcoeffs
