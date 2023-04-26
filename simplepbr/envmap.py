import time

import panda3d.core as p3d
from direct.stdpy import threading

from . import _ibl_funcs as iblfuncs


class EnvMap:
    def __init__(self, cubemap: p3d.Texture, prefiltered_size=64, prefiltered_samples=16):
        self.cubemap: p3d.Texture = cubemap
        self.sh_coefficients: p3d.PTA_LVecBase3f = p3d.PTA_LVecBase3f.empty_array(9)
        self.filtered_env_map = p3d.Texture('filtered_env_map')

        self._prefiltered_size = prefiltered_size
        self._prefiltered_samples = prefiltered_samples

        self.prepare()

    def __bool__(self):
        return self.cubemap.name != 'env_map_fallback'

    def prepare(self):
        self.filtered_env_map.setup_cube_map(1, p3d.Texture.T_float, p3d.Texture.F_rgba16)

        def calc_sh(future):
            starttime = time.perf_counter()
            shcoeffs = iblfuncs.get_sh_coeffs_from_cube_map(self.cubemap)
            for idx, val in enumerate(shcoeffs):
                self.sh_coefficients[idx] = val

            tottime = (time.perf_counter() - starttime) * 1000
            print(
                f'Spherical harmonics coefficients for {self.cubemap.name} calculated in {tottime:.3f}ms'
            )
            future.set_result(self)

        def filter_env_map(future):
            starttime = time.perf_counter()
            iblfuncs.filter_env_map(
                self.cubemap,
                self.filtered_env_map,
                size=self._prefiltered_size,
                num_samples=self._prefiltered_samples,
            )

            tottime = (time.perf_counter() - starttime) * 1000
            print(
                f'Pre-filtered environment map for {self.cubemap.name} calculated in {tottime:.3f}ms'
            )
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
        cubemap.set_clear_color(p3d.LColor(1, 1, 1, 1))
        cubemap.make_ram_image()
        return cls(cubemap, prefiltered_size=16, prefiltered_samples=1)
