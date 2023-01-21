import panda3d.core as p3d
from direct.stdpy import threading

from . import _spherical_harmonics as sh

class EnvMap:
    def __init__(self, cubemap: p3d.Texture):
        self.cubemap: p3d.Texture = cubemap
        self.sh_coefficients: p3d.PTA_LVecBase3f = p3d.PTA_LVecBase3f.empty_array(9)

        self.prepare()

    def __bool__(self):
        return self.cubemap.name != 'env_map_fallback'

    def prepare(self):
        future = p3d.AsyncFuture()
        def inner():
            shcoeffs = sh.get_sh_coeffs_from_cube_map(self.cubemap)
            for idx, val in enumerate(shcoeffs):
                self.sh_coefficients[idx] = val

            future.set_result(self)

        thread = threading.Thread(target=inner)
        thread.start()

        return future

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
