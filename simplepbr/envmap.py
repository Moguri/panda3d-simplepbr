import time

import panda3d.core as p3d
from direct.stdpy import threading

from . import _ibl_funcs as iblfuncs


class EnvMap:
    def __init__(self, cubemap: p3d.Texture, *, prefiltered_size=64, prefiltered_samples=16, skip_prepare=False):
        self.cubemap: p3d.Texture = cubemap
        self.sh_coefficients: p3d.PTA_LVecBase3f = p3d.PTA_LVecBase3f.empty_array(9)
        self.filtered_env_map = p3d.Texture('filtered_env_map')
        self.filtered_env_map.setup_cube_map(1, p3d.Texture.T_float, p3d.Texture.F_rgba16)

        self._prefiltered_size = prefiltered_size
        self._prefiltered_samples = prefiltered_samples
        self.is_prepared = p3d.AsyncFuture()

        if not skip_prepare:
            self._prepare()

    def __bool__(self):
        return self.cubemap.name != 'env_map_fallback'

    def _prepare(self):
        def calc_sh():
            starttime = time.perf_counter()
            shcoeffs = iblfuncs.get_sh_coeffs_from_cube_map(self.cubemap)
            for idx, val in enumerate(shcoeffs):
                self.sh_coefficients[idx] = val

            tottime = (time.perf_counter() - starttime) * 1000
            print(
                f'Spherical harmonics coefficients for {self.cubemap.name} calculated in {tottime:.3f}ms'
            )

        def filter_env_map():
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

        jobs = [
            calc_sh,
            filter_env_map,
        ]
        threads = []

        for job in jobs:
            thread = threading.Thread(target=job)
            threads.append(thread)
            thread.start()

        def wait_threads(future):
            for thread in threads:
                thread.join()
            future.set_result(self)
        future = p3d.AsyncFuture()
        def donecb(_):
            self.is_prepared.set_result(True)
        future.add_done_callback(donecb)
        thread = threading.Thread(target=wait_threads, args=[future])
        thread.start()
        return future

    def write(self, filepath):
        bfile = p3d.BamFile()
        bfile.open_write(filepath)
        bfile.writer.set_file_texture_mode(p3d.BamWriter.BTM_rawdata)

        shcoeffs_data = p3d.Datagram()
        for vec in self.sh_coefficients:
            for i in vec:
                shcoeffs_data.add_stdfloat(i)

        bfile.write_object(self.cubemap)
        bfile.write_object(self.filtered_env_map)
        bfile.writer.target.put_datagram(shcoeffs_data)

    @classmethod
    def _from_bam(cls, path: p3d.Filename):
        bfile = p3d.BamFile()
        bfile.open_read(path, True)

        reader = bfile.reader
        cubemap = reader.read_object()
        envmap = cls(cubemap, skip_prepare=True)
        envmap.filtered_env_map = reader.read_object()
        dgram = p3d.Datagram()
        reader.source.get_datagram(dgram)
        scan = p3d.DatagramIterator(dgram)
        for idx in range(len(envmap.sh_coefficients)):
            envmap.sh_coefficients[idx] = p3d.LVector3(
                scan.get_stdfloat(),
                scan.get_stdfloat(),
                scan.get_stdfloat()
            )
        return envmap

    @classmethod
    def from_file_path(cls, path):
        if not isinstance(path, p3d.Filename):
            path = p3d.Filename.from_os_specific(path)

        if path.get_extension() == 'env':
            return cls._from_bam(path)

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
