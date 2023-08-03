from __future__ import annotations

from dataclasses import dataclass, field, InitVar
import builtins
import math
import os
import typing
from typing_extensions import (
    Any,
    ClassVar,
    Literal,
    TypeAlias,
)

import panda3d.core as p3d

from direct.showbase.ShowBase import ShowBase
from direct.filter.FilterManager import FilterManager
from direct.task.Task import TaskManager

from .version import __version__
from .envmap import EnvMap
from .envpool import EnvPool
from . import logging
from . import utils
from . import _shaderutils as shaderutils

try:
    from .textures import textures # type: ignore
except ImportError:
    textures = None


__all__ = [
    'load_sdr_lut',
    'sdr_lut_screenshot',
    'init',
    'Pipeline',
    'EnvMap',
    'EnvPool',
    'utils',
]

ShaderDefinesType: TypeAlias = 'dict[str, Any]'


def load_sdr_lut(filename: str) -> p3d.Texture:
    '''Load an SDR color LUT embedded in a screenshot'''
    path = p3d.Filename(filename)
    vfs = p3d.VirtualFileSystem.get_global_ptr()
    failed = (
        not vfs.resolve_filename(path, p3d.get_model_path().value)
        or not path.is_regular_file()
    )
    if failed:
        raise RuntimeError('Failed to find file {}'.format(filename))

    image = p3d.PNMImage(path)

    lutdim = 64
    xsize, ysize = image.get_size()
    tiles_per_row = xsize // lutdim
    num_rows = math.ceil(lutdim / tiles_per_row)
    ysize -= num_rows * lutdim

    texture = p3d.Texture()
    texture.setup_3d_texture(
        lutdim, lutdim, lutdim,
        p3d.Texture.T_unsigned_byte,
        p3d.Texture.F_rgb8
    )
    texture.minfilter = p3d.Texture.FT_linear
    texture.magfilter = p3d.Texture.FT_linear

    for tileidx in range(lutdim):
        xstart = tileidx % tiles_per_row * lutdim
        ystart = tileidx // tiles_per_row * lutdim + ysize
        islice = p3d.PNMImage(lutdim, lutdim, 3, 255)
        islice.copy_sub_image(image, 0, 0, xstart, ystart, lutdim, lutdim)
        texture.load(islice, tileidx, 0)
    return texture


def sdr_lut_screenshot(showbase: ShowBase, *args, **kwargs) -> str | None: # type: ignore[no-untyped-def]
    '''Take a screenshot with an embedded SDR color LUT'''
    filename = showbase.screenshot(*args, **kwargs)

    if not filename:
        return filename

    lutdim = 64
    stepsize = 256 // lutdim

    image = p3d.PNMImage(filename)
    xsize, ysize = image.get_size()
    tiles_per_row = xsize // lutdim
    num_rows = math.ceil(lutdim / tiles_per_row)

    image.expand_border(0, 0, num_rows * lutdim, 0, (0, 0, 0, 1))

    steps = list(range(0, 256, stepsize))
    maxoffset = len(steps) - 1

    for tileidx, bcol in enumerate(steps):
        xbase = tileidx % tiles_per_row * lutdim
        ybase = tileidx // tiles_per_row * lutdim + ysize
        for xoff, rcol in enumerate(steps):
            xcoord = xbase + xoff
            for yoff, gcol in enumerate(steps):
                ycoord = ybase + maxoffset - yoff
                image.set_xel_val(xcoord, ycoord, rcol, gcol, bcol)

    image.write(filename)

    return filename


def _load_texture(texturepath: str) -> p3d.Texture:
    texturedir = p3d.Filename.from_os_specific(
        os.path.join(
            os.path.dirname(__file__),
            'textures'
        )
    )
    if textures:
        texture = p3d.Texture.make_from_txo(
            p3d.StringStream(textures[texturepath]),
            (texturedir / texturepath).get_fullpath()
        )
    else:
        texture = p3d.TexturePool.load_texture(texturedir / texturepath)

    return texture


def _get_showbase_attr(attr: str) -> Any:
    showbase: ShowBase = builtins.base # type: ignore[attr-defined]
    return getattr(showbase, attr)


def _get_default_330() -> bool:
    cvar = p3d.ConfigVariableInt('gl-version')
    gl_version = [
        cvar.get_word(i)
        for i in range(cvar.get_num_words())
    ]
    if len(gl_version) >= 2 and gl_version[0] >= 3 and gl_version[1] >= 2:
        # Not exactly accurate, but setting this variable to '3 2' is common for disabling
        # the fixed-function pipeline and 3.2 support likely means 3.3 support as well.
        return True

    return False

@dataclass()
class Pipeline:
    # Class variables
    _EMPTY_ENV_MAP: ClassVar[EnvMap] = EnvMap.create_empty()
    _BRDF_LUT: ClassVar[p3d.Texture] = _load_texture('brdf_lut.txo')
    _PBR_VARS: ClassVar[list[str]] = [
        'enable_fog',
        'enable_hardware_skinning',
        'enable_shadows',
        'max_lights',
        'use_emission_maps',
        'use_normal_maps',
        'use_occlusion_maps',
    ]
    _POST_PROC_VARS: ClassVar[list[str]] = [
        'camera_node',
        'msaa_samples',
        'sdr_lut',
        'window',
    ]

    # Public instance variables
    render_node: p3d.NodePath[p3d.PandaNode] = field(default_factory=lambda: _get_showbase_attr('render'))
    window: p3d.GraphicsOutput = field(default_factory=lambda: _get_showbase_attr('win'))
    camera_node: p3d.NodePath[p3d.Camera] = field(default_factory=lambda: _get_showbase_attr('cam'))
    taskmgr: TaskManager = field(default_factory=lambda: _get_showbase_attr('task_mgr'))
    msaa_samples: Literal[0, 2, 4, 8, 16] = 4
    max_lights: int = 8
    use_normal_maps: bool = False
    use_emission_maps: bool = True
    use_occlusion_maps: bool = False
    exposure: float = 1.0
    enable_shadows: bool = True
    enable_fog: bool  = False
    use_330: bool = field(default_factory=_get_default_330)
    use_hardware_skinning: InitVar[bool | None] = None
    enable_hardware_skinning: bool = True
    sdr_lut: p3d.Texture | None = None
    sdr_lut_factor: float = 1.0
    env_map: EnvMap | str | None = None

    # Private instance variables
    _shader_ready: bool = False
    _filtermgr: FilterManager = field(init=False)
    _post_process_quad: p3d.NodePath[p3d.GeomNode] = field(init=False)

    def __post_init__(self, use_hardware_skinning: bool) -> None:
        self._shader_ready = False

        # Create a FilterManager instance
        self._filtermgr = FilterManager(self.window, self.camera_node)

        # Do not force power-of-two textures
        p3d.Texture.set_textures_power_2(p3d.ATS_none)

        # Make sure we have AA for if/when MSAA is enabled
        self.render_node.set_antialias(p3d.AntialiasAttrib.M_auto)

        # PBR Shader
        self.enable_hardware_skinning = use_hardware_skinning if use_hardware_skinning is not None else self.use_330
        self._recompile_pbr()

        # Tonemapping
        self._setup_tonemapping()

        # Do updates based on scene changes
        self.taskmgr.add(self._update, 'simplepbr update')

        self._shader_ready = True

        self._BRDF_LUT.wrap_u = p3d.SamplerState.WM_clamp
        self._BRDF_LUT.wrap_v = p3d.SamplerState.WM_clamp
        self._BRDF_LUT.minfilter = p3d.SamplerState.FT_linear
        self._BRDF_LUT.magfilter = p3d.SamplerState.FT_linear

    def __setattr__(self, name: str, value: Any) -> None:
        prev_value = getattr(self, name, None)
        super().__setattr__(name, value)

        if not self._shader_ready:
            return

        def resetup_tonemap() -> None:
            # Destroy previous buffers so we can re-create
            self._filtermgr.cleanup()

            # Create a new FilterManager instance
            self._filtermgr = FilterManager(self.window, self.camera_node)
            self._setup_tonemapping()

        if name == 'exposure':
            self._post_process_quad.set_shader_input('exposure', self.exposure)
        elif name == 'sdr_lut_factor':
            self._post_process_quad.set_shader_input('sdr_lut_factor', self.sdr_lut_factor)
        elif name == 'env_map':
            self._set_env_map_uniforms()

        if name in self._PBR_VARS and prev_value != value:
            self._recompile_pbr()

        if name in self._POST_PROC_VARS and prev_value != value:
            resetup_tonemap()

    def _set_env_map_uniforms(self) -> None:
        env_map = self.env_map
        if env_map is None:
            env_map = self._EMPTY_ENV_MAP
        elif isinstance(env_map, str):
            env_map = EnvPool.ptr().load(env_map)
        self.render_node.set_shader_input('sh_coeffs', env_map.sh_coefficients)
        self.render_node.set_shader_input('brdf_lut', self._BRDF_LUT)
        filtered_env_map = env_map.filtered_env_map
        self.render_node.set_shader_input('filtered_env_map', filtered_env_map)
        self.render_node.set_shader_input('max_reflection_lod', filtered_env_map.num_loadable_ram_mipmap_images)

    def _recompile_pbr(self) -> None:
        pbr_defines = {
            'MAX_LIGHTS': self.max_lights,
            'USE_NORMAL_MAP': self.use_normal_maps,
            'USE_EMISSION_MAP': self.use_emission_maps,
            'ENABLE_SHADOWS': self.enable_shadows,
            'ENABLE_FOG': self.enable_fog,
            'USE_OCCLUSION_MAP': self.use_occlusion_maps,
            'USE_330': self.use_330,
            'ENABLE_SKINNING': self.enable_hardware_skinning,
        }

        pbrshader = shaderutils.make_shader(
            'pbr',
            'simplepbr.vert',
            'simplepbr.frag',
            pbr_defines
        )
        attr = typing.cast(p3d.ShaderAttrib, p3d.ShaderAttrib.make(pbrshader))
        if self.enable_hardware_skinning:
            attr = typing.cast(p3d.ShaderAttrib, attr.set_flag(p3d.ShaderAttrib.F_hardware_skinning, True))
        self.render_node.set_attrib(attr)
        self._set_env_map_uniforms()

    def _setup_tonemapping(self) -> None:
        if self._shader_ready:
            # Destroy previous buffers so we can re-create
            self._filtermgr.cleanup()

            # Fix shadow buffers after FilterManager.cleanup()
            for caster in self.get_all_casters():
                sbuff_size = caster.get_shadow_buffer_size()
                caster.set_shadow_buffer_size((0, 0))
                caster.set_shadow_buffer_size(sbuff_size)


        fbprops = p3d.FrameBufferProperties()
        fbprops.float_color = True
        fbprops.set_rgba_bits(16, 16, 16, 16)
        fbprops.set_depth_bits(24)
        fbprops.set_multisamples(self.msaa_samples)
        scene_tex = p3d.Texture()
        scene_tex.set_format(p3d.Texture.F_rgba16)
        scene_tex.set_component_type(p3d.Texture.T_float)
        postquad = self._filtermgr.render_scene_into(colortex=scene_tex, fbprops=fbprops)

        if postquad is None:
            raise RuntimeError('Failed to setup FilterManager')

        defines = {
            'USE_330': self.use_330,
            'USE_SDR_LUT': bool(self.sdr_lut),
        }

        tonemap_shader = shaderutils.make_shader(
            'tonemap',
            'post.vert',
            'tonemap.frag',
            defines
        )
        postquad.set_shader(tonemap_shader)
        postquad.set_shader_input('tex', scene_tex)
        postquad.set_shader_input('exposure', self.exposure)
        if self.sdr_lut:
            postquad.set_shader_input('sdr_lut', self.sdr_lut)
            postquad.set_shader_input('sdr_lut_factor', self.sdr_lut_factor)

        self._post_process_quad = postquad

    def get_all_casters(self) -> list[p3d.LightLensNode]:
        engine = p3d.GraphicsEngine.get_global_ptr()
        cameras = [
            dispregion.camera
            for win in engine.windows
            for dispregion in win.active_display_regions
        ]

        return [
            i.node()
            for i in cameras
            if not i.is_empty() and hasattr(i.node(), 'is_shadow_caster') and i.node().is_shadow_caster()
        ]

    def _create_shadow_shader_attrib(self) -> p3d.ShaderAttrib:
        defines = {
            'USE_330': self.use_330,
            'ENABLE_SKINNING': self.enable_hardware_skinning,
        }
        shader = shaderutils.make_shader(
            'shadow',
            'shadow.vert',
            'shadow.frag',
            defines
        )
        attr = typing.cast(p3d.ShaderAttrib, p3d.ShaderAttrib.make(shader))
        if self.enable_hardware_skinning:
            attr = typing.cast(p3d.ShaderAttrib, attr.set_flag(p3d.ShaderAttrib.F_hardware_skinning, True))
        return attr

    def _update(self, task: p3d.PythonTask) -> int:
        recompile = False
        # Use a simpler, faster shader for shadows
        for caster in self.get_all_casters():
            if isinstance(caster, p3d.PointLight):
                logging.warning(f'PointLight shadow casters are not supported, disabling {caster.name}')
                caster.set_shadow_caster(False)
                recompile = True
                continue
            state = caster.get_initial_state()
            if not state.has_attrib(p3d.ShaderAttrib):
                attr = self._create_shadow_shader_attrib()
                state = state.add_attrib(attr, 1)
                caster.set_initial_state(state)

        if recompile:
            self._recompile_pbr()

        return task.DS_cont


    def verify_shaders(self) -> None:
        gsg = self.window.gsg

        def check_shader(shader: p3d.Shader) -> None:
            shader = p3d.Shader(shader)
            shader.prepare_now(gsg.prepared_objects, gsg)
            assert shader.is_prepared(gsg.prepared_objects)
            assert not shader.get_error_flag()

        check_shader(self.render_node.get_shader())
        check_shader(self._post_process_quad.get_shader())

        attr = self._create_shadow_shader_attrib()
        check_shader(attr.get_shader())


init = Pipeline # pylint: disable=invalid-name
