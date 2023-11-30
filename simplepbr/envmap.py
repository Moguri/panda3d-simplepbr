from __future__ import annotations

from pathlib import Path
import time
import typing
from typing_extensions import (
    Self,
)

import panda3d.core as p3d
from direct.stdpy import threading

from . import logging
from . import _ibl_funcs_cpu as iblfuncs


DEFAULT_PREFILTERED_SIZE=64
DEFAULT_PREFILTERED_SAMPLES=16

class EnvMap:
    def __init__(
        self, cubemap: p3d.Texture,
        *,
        prefiltered_size: int=DEFAULT_PREFILTERED_SIZE,
        prefiltered_samples: int=DEFAULT_PREFILTERED_SAMPLES,
        skip_prepare: bool=False,
        blocking_prepare: bool=False,
    ) -> None:
        self.cubemap: p3d.Texture = cubemap
        self.sh_coefficients: p3d.PTA_LVecBase3f = p3d.PTA_LVecBase3f.empty_array(9)
        for idx, _ in enumerate(self.sh_coefficients):
            self.sh_coefficients[idx] = p3d.LVecBase3(0, 0, 0)

        self.filtered_env_map = p3d.Texture('filtered_env_map')
        self.filtered_env_map.setup_cube_map(1, p3d.Texture.T_float, p3d.Texture.F_rgba16)
        self.filtered_env_map.set_clear_color(p3d.LColor(0, 0, 0, 0))
        self.filtered_env_map.wrap_u = p3d.SamplerState.WM_clamp
        self.filtered_env_map.wrap_v = p3d.SamplerState.WM_clamp
        self.filtered_env_map.wrap_w = p3d.SamplerState.WM_clamp
        self.filtered_env_map.minfilter = p3d.SamplerState.FT_linear
        self.filtered_env_map.magfilter = p3d.SamplerState.FT_linear_mipmap_linear

        self._prefiltered_size = prefiltered_size
        self._prefiltered_samples = prefiltered_samples
        self.is_prepared = p3d.AsyncFuture()

        self._blocking_prepare = blocking_prepare

        if not skip_prepare:
            self.prepare()

    def __bool__(self) -> bool:
        return self.cubemap.name != 'env_map_fallback'


    @property
    def hash(self) -> str:
        name = hash(self.cubemap.fullpath)
        return f'{name}{self._prefiltered_size}{self._prefiltered_samples}'

    def prepare(self) -> p3d.AsyncFuture:
        def calc_sh() -> None:
            starttime = time.perf_counter()
            shcoeffs = iblfuncs.get_sh_coeffs_from_cube_map(self.cubemap)
            for idx, val in enumerate(shcoeffs):
                self.sh_coefficients[idx] = val

            tottime = (time.perf_counter() - starttime) * 1000
            logging.info(
                f'Spherical harmonics coefficients for {self.cubemap.name} '
                f'calculated in {tottime:.3f}ms'
            )

        def filter_env_map() -> None:
            starttime = time.perf_counter()
            iblfuncs.filter_env_map(
                self.cubemap,
                self.filtered_env_map,
                size=self._prefiltered_size,
                num_samples=self._prefiltered_samples,
            )

            tottime = (time.perf_counter() - starttime) * 1000
            logging.info(
                f'Pre-filtered environment map for {self.cubemap.name} '
                f'calculated in {tottime:.3f}ms'
            )

        jobs = [
            calc_sh,
            filter_env_map,
        ]
        threads = []

        for job in jobs:
            if self._blocking_prepare:
                job()
            else:
                thread = threading.Thread(target=job)
                threads.append(thread)
                thread.start()

        def wait_threads(future: p3d.AsyncFuture) -> None:
            for thread in threads:
                thread.join()
            future.set_result(self)
        future = p3d.AsyncFuture()
        def donecb(_: p3d.AsyncFuture) -> None:
            self.is_prepared.set_result(self)
        future.add_done_callback(donecb)

        if self._blocking_prepare:
            wait_threads(future)
        else:
            thread = threading.Thread(target=wait_threads, args=[future])
            thread.start()
        return future

    def write(self, filepath: p3d.Filename) -> None:
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
    def _from_bam(cls, path: p3d.Filename) -> Self:
        bfile = p3d.BamFile()
        bfile.open_read(path, True)

        reader = bfile.reader
        cubemap = typing.cast(p3d.Texture, reader.read_object())
        envmap = cls(cubemap, skip_prepare=True)
        envmap.filtered_env_map = typing.cast(p3d.Texture, reader.read_object())
        dgram = p3d.Datagram()
        reader.source.get_datagram(dgram)
        scan = p3d.DatagramIterator(dgram)
        for idx, _ in enumerate(envmap.sh_coefficients):
            envmap.sh_coefficients[idx] = p3d.LVector3(
                scan.get_stdfloat(),
                scan.get_stdfloat(),
                scan.get_stdfloat()
            )
        envmap.is_prepared.set_result(envmap)
        return envmap

    @classmethod
    def from_file_path(
        cls,
        path: p3d.Filename | Path | str,
        prefiltered_size: int = DEFAULT_PREFILTERED_SIZE,
        prefiltered_samples: int = DEFAULT_PREFILTERED_SAMPLES,
        skip_prepare: bool=False,
        blocking_prepare: bool=False,
    ) -> Self:
        if isinstance(path, Path):
            path = p3d.Filename(path)

        if not isinstance(path, p3d.Filename):
            path = p3d.Filename.from_os_specific(path)

        if path.get_extension() == 'env':
            return cls._from_bam(path)

        cubemap = p3d.TexturePool.load_cube_map(path)
        return cls(
            cubemap,
            prefiltered_size=prefiltered_size,
            prefiltered_samples=prefiltered_samples,
            skip_prepare=skip_prepare,
            blocking_prepare=blocking_prepare,
        )

    @classmethod
    def create_empty(cls) -> Self:
        cubemap = p3d.Texture('env_map_fallback')
        cubemap.setup_cube_map(
            2,
            p3d.Texture.T_unsigned_byte,
            p3d.Texture.F_rgb
        )
        cubemap.set_clear_color(p3d.LColor(0, 0, 0, 0))
        envmap =  cls(cubemap, skip_prepare=True)
        envmap.is_prepared.set_result(envmap)
        return envmap
