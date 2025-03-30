from pathlib import Path
from typing import Union
from typing_extensions import (
    Self,
)

import panda3d.core as p3d

from .envmap import (
    EnvMap,
    DEFAULT_PREFILTERED_SIZE,
    DEFAULT_PREFILTERED_SAMPLES,
)
from . import logging


class EnvPool:
    _ptr: Self | None = None

    def __init__(self) -> None:
        self._envmaps: dict[p3d.Filename, EnvMap] = {}

    def _get_cache_path(self, envmap: EnvMap) -> p3d.Filename:
        model_cache_dir = p3d.ConfigVariableFilename('model-cache-dir').value
        cache_path = model_cache_dir / f'{envmap.hash}.env'

        return cache_path

    def _write_cache(self, future: p3d.AsyncFuture) -> None:
        envmap = future.result()
        envmap.write(self._get_cache_path(envmap))

    def load(
        self,
        filepath: Union[p3d.Filename, Path, str],
        prefiltered_size: int = DEFAULT_PREFILTERED_SIZE,
        prefiltered_samples: int = DEFAULT_PREFILTERED_SAMPLES,
    ) -> EnvMap:
        if isinstance(filepath, Path):
            filepath = p3d.Filename(filepath)

        if not isinstance(filepath, p3d.Filename):
            filepath = p3d.Filename.from_os_specific(filepath)

        if filepath in self._envmaps:
            logging.info(f'EnvPool: loaded {filepath} from RAM cache')
            return self._envmaps[filepath]

        if filepath.get_extension() == 'env':
            envmap = EnvMap.from_file_path(filepath)
            self._envmaps[filepath] = envmap
            return envmap

        envmap = EnvMap.from_file_path(
            filepath,
            skip_prepare=True,
            prefiltered_size=prefiltered_size,
            prefiltered_samples=prefiltered_samples,
        )
        cache_file = self._get_cache_path(envmap)

        if cache_file.exists():
            logging.info(f'EnvPool: loaded {filepath} from disk cache')
            envmap = EnvMap.from_file_path(
                cache_file,
                prefiltered_size=prefiltered_size,
                prefiltered_samples=prefiltered_samples,
            )
        else:
            envmap.prepare()
            envmap.is_prepared.add_done_callback(self._write_cache)


        self._envmaps[filepath] = envmap
        return envmap

    @classmethod
    def ptr(cls) -> Self:
        if cls._ptr is None:
            cls._ptr = cls()

        return cls._ptr
