import panda3d.core as p3d
from direct.stdpy import threading

from . import _ibl_funcs as iblfuncs

class EnvMap:
    def __init__(self, cubemap: p3d.Texture):
        self.cubemap: p3d.Texture = cubemap
        self.sh_coefficients: p3d.PTA_LVecBase3f = p3d.PTA_LVecBase3f.empty_array(9)
        self.brdf_lut = p3d.Texture('brdf_lut')
        self.filtered_env_map = p3d.Texture('filtered_env_map')

        self.prepare()

    def __bool__(self):
        return self.cubemap.name != 'env_map_fallback'

    def prepare(self):
        self.brdf_lut.setup_2d_texture(
            512,
            512,
            p3d.Texture.T_float,
            p3d.Texture.F_rg16,
        )
        self.brdf_lut.set_clear_color(p3d.LColor(1, 0, 0, 0))

        self.filtered_env_map.setup_cube_map(1, p3d.Texture.T_float, p3d.Texture.F_rgba16)

        def calc_sh(future):
            shcoeffs = iblfuncs.get_sh_coeffs_from_cube_map(self.cubemap)
            for idx, val in enumerate(shcoeffs):
                self.sh_coefficients[idx] = val

            future.set_result(self)

        def filter_env_map(future):
            self.filtered_env_map = self.cubemap.make_copy()
            self.filtered_env_map.set_clear_color(p3d.LColor(1, 1, 1, 1))
            self.filtered_env_map.magfilter = p3d.SamplerState.FT_linear
            self.filtered_env_map.minfilter = p3d.SamplerState.FT_linear_mipmap_linear

            future.set_result(self)

        jobs = [
            calc_sh,
            filter_env_map,
        ]
        futures = []

        for job in jobs:
            future = p3d.AsyncFuture()
            futures.append(future)
            thread = threading.Thread(target=job, args=[future])
            thread.start()

        return p3d.AsyncFuture.gather(
            *futures
        )

    @classmethod
    def from_file_path(cls, path):
        cubemap = p3d.TexturePool.load_cube_map(path)
        return cls(cubemap)

    @classmethod
    def create_empty(cls):
        cubemap = p3d.Texture('env_map_fallback')
        cubemap.setup_cube_map(
            2,
            p3d.Texture.T_unsigned_byte,
            p3d.Texture.F_rgb
        )
        cubemap.set_clear_color(p3d.LColor(0, 0, 0, 1))
        cubemap.make_ram_image()
        return cls(cubemap)
