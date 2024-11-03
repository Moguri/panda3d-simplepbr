# Configuration

`simplepbr` is highly configurable, but attempts to use good, sensible defaults.
The options below can be set via keyword arguments to `simplepbr.init()`
They can also be changed later by modifying attributes of the same name on the `Pipeline` object returned by `simplepbr.init()`.
For example:

```python
pipeline = simplepbr.init(
   enable_shadows=False,
   max_lights=4,
)

pipeline.max_lights = 6
pipeline.msaa_samples = 8
```

These options can also be set via PRC variables prior to initializing the `Pipeline` object (i.e., before calling `simplepbr.init()`.
Change the PRC variables after the `Pipeline` object has been initialized will have no effect.
The PRC variables use the same names as the options below except for:

  * They start with `simplepbr-`
  * All hyphens (`-`) are replaced with underscores (`_`)

For example, to set `max_lights` via a PRC variable:

```
simplepbr-max-lights 8
```

## Pipeline Options

### Setup
`render_node`
: The node to attach the shader too, defaults to `base.render` if `None`

`window`
: The window to attach the framebuffer too, defaults to `base.win` if `None`

`camera_node`
: The NodePath of the camera to use when rendering the scene, defaults to `base.cam` if `None`

`msaa_samples`
: The number of samples to use for multisample anti-aliasing, defaults to 4

`use_330`
: Force shaders to use GLSL version 330 (if `True`) or 120 (if `False`) or auto-detect if `None`, defaults to `None`

`use_hardware_skinning`
: Force usage of hardware skinning for skeleton animations or auto-detect if `None`, defaults to `None`

### Lighting and Shadows

`max_lights`
: The maximum number of lights to render, defaults to 8

`enable_shadows`
: Enable shadow map support, defaults to `True`

`shadow_bias`
: A global bias for shadow mapping (increase to reduce shadow acne, decrease to reduce peter-panning), defaults to `0.005`

`exposure`
: adjust the brightness of the scene prior to tonemapping (values greater than `0.0` brighten the scene and values less than `0.0` darken it), defaults to `0.0`

`enable_fog`
: Enable exponential fog, defaults to False

`env_map`
: An `EnvMap` or cubemap texture path to use for IBL, defaults to `None`

### Textures
`use_normal_maps`
: Use normal maps to modify fragment normals, defaults to `False` (NOTE: Requires models with appropriate tangents defined)

`calculate_normalmap_blue`
: Calculate the blue channel (Z-axis) for a normal map in the shader (allows saving memory/bandwidth by using 2 channel normal maps), defaults to `True`

`use_emission_maps`
: Use emission maps, defaults to `True`

`use_occlusion_maps`
: Use occlusion maps, defaults to `False` (NOTE: Requires occlusion channel in metal-roughness map)

### Color Grading

`sdr_lut`
: Color LUT to use post-tonemapping

`sdr_lut_factor`
: Factor (from 0.0 to 1.0) for how much of the LUT color to mix in, defaults to 1.0

