import typing

import panda3d.core as p3d

from .envmap import EnvMap

PathLikeType = typing.Union[str, p3d.Filename]

class EnvPool:
    _ptr: typing.Optional['EnvPool'] = None

    def __init__(self):
        self._envmaps: dict[p3d.Filename, EnvMap] = {}

    def _get_cache_path(self, envmap: EnvMap) -> p3d.Filename:
        model_cache_dir = p3d.ConfigVariableFilename('model-cache-dir').value
        cache_path = model_cache_dir / f'{envmap.hash}.env'

        return cache_path

    def _write_cache(self, future: p3d.AsyncFuture) -> None:
        envmap = future.result()
        envmap.write(self._get_cache_path(envmap))

    def load(self, filepath: PathLikeType) -> EnvMap:
        if not isinstance(filepath, p3d.Filename):
            filepath = p3d.Filename.from_os_specific(filepath)

        if filepath in self._envmaps:
            return self._envmaps[filepath]

        if filepath.get_extension() == 'env':
            envmap = EnvMap.from_file_path(filepath)
            self._envmaps[filepath] = envmap
            return envmap

        envmap = EnvMap.from_file_path(filepath, skip_prepare=True)
        cache_file = self._get_cache_path(envmap)

        if cache_file.exists():
            envmap = EnvMap.from_file_path(cache_file)
        else:
            envmap.prepare()
            envmap.is_prepared.add_done_callback(self._write_cache)


        self._envmaps[filepath] = envmap
        return envmap

    @classmethod
    def ptr(cls) -> 'EnvPool':
        if cls._ptr is None:
            cls._ptr = cls()

        return cls._ptr