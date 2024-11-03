# Getting Started


## Installation

Use pip to install the `panda3d-simplepbr` package:

```bash
pip install panda3d-simplepbr
```

To grab the latest development build, use:

```bash
pip install git+https://github.com/Moguri/panda3d-simplepbr.git
```

## Usage

Just add `simplepbr.init()` to your `ShowBase` instance:

```python
from direct.showbase.ShowBase import ShowBase

import simplepbr

class App(ShowBase):
    def __init__(self):
        super().__init__()

        simplepbr.init()
```

## PBR Textures

`simplepbr` expects the following textures are assigned to the following texture stages:

* BaseColor - Modulate
* MetalRoughness - Selector
* Normals - Normal
* Emission - Emission

For best results, ensure your asset pipeline is generating PBR materials for Panda3D.
For example, glTF files loaded with [panda3d-gltf](https://github.com/Moguri/panda3d-gltf) are known to work well.
However, EGG files do not support PBR materials at the time of writing.

## Tangents and Normal Maps

To use normal maps, `simplepbr` expects 4-component tangent values (with no bi-normal/bi-tangent), which matchesl glTF.
Panda3D may also switch to 4-component tangents [in the future](https://github.com/panda3d/panda3d/issues/546).
Unfortunately, this means that [panda3d-gltf](https://github.com/Moguri/panda3d-gltf) is the best option for getting vertex data that works with normal mapping in `simplepbr`.
