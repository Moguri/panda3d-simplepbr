from __future__ import annotations

import panda3d.core as p3d

from . import cpu

def get_sh_coeffs_from_cube_map(cubemap: p3d.Texture) -> list[p3d.LVector3]:
    return cpu.get_sh_coeffs_from_cube_map(cubemap)

def gen_brdf_lut(lutsize: int, num_samples: int = 1024) -> p3d.Texture:
    return cpu.gen_brdf_lut(lutsize, num_samples=num_samples)

def filter_env_map(
        envmap: p3d.Texture,
        filtered: p3d.Texture,
        *,
        size: int = 16,
        num_mipmaps: int = 4,
        num_samples: int = 4
) -> None:
    return cpu.filter_env_map(
        envmap,
        filtered,
        size=size,
        num_mipmaps=num_mipmaps,
        num_samples=num_samples,
    )
