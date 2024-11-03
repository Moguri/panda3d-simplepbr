# Features

## Skyboxes

While not the trickiest thing to setup with standard Panda3D APIs, skyboxes can still be a bit involved to get right.
`simplepbr` provides a utility function to take out some of the guess-work and just get a skybox going:

```python
from direct.showbase.ShowBase import ShowBase

import simplepbr

class App(ShowBase):
    def __init__(self):
        super().__init__()

        simplepbr.init()

        cubemap = self.loader.load_cube_map('cubemap_#.hdr')
        self.skybox = simplepbr.utils.make_skybox(cubemap)
        self.skybox.reparent_to(self.render)
```

## EnvMap and Image-based Lighting 


Imaged-based lighting (IBL) requires a `simplepbr.EnvMap`.
These asynchronously pre-compute items necessary for IBL diffuse (spherical harmonics) and IBL specular lighting (pre-filtered environment map).
`EnvMap` objects can also be saved to disk to avoid doing these calculations at runtime as they can be quite slow.
Similar to Panda3D's `TexturePool`, `simplepbr` provides a `simplepbr.EnvPool` to automatically handle caching `EnvMap` objects.
Below is an example of using `simplepbr.EnvPool` to load a `simplepbr.EnvMap` from cubemap files on disk:

```python
from direct.showbase.ShowBase import ShowBase

import simplepbr

class App(ShowBase):
    def __init__(self):
        super().__init__()

        env_map = simplepbr.EnvPool.ptr().load('cubemap_#.hdr')

        simplepbr.init(
            env_map,
        )
```

To created `EnvMap` files offline, `simplepbr` ships with an `hdr2env` tool:

```bash
hdr2env cubemap_#.hdr cubemap.env
```

An `env` file can be loaded like cubemap images using:
```python
env_map = simplepbr.EnvPool.ptr().load('cubemap.env')
```
