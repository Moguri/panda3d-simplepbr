from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
    Field,
    InitVar,
    MISSING,
)
import builtins
import functools
import os
from typing import (
    ClassVar,
)
from typing_extensions import (
    Any,
    Literal,
    TypeAlias,
    TypeVar,
)

import panda3d.core as p3d

from direct.showbase.ShowBase import ShowBase
from direct.filter.FilterManager import FilterManager
from direct.task.Task import TaskManager

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
    'init',
    'Pipeline',
    'EnvMap',
    'EnvPool',
    'utils',
]

ShaderDefinesType: TypeAlias = 'dict[str, Any]'


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
    # Not exactly accurate, but setting this variable to '3 2' is common for disabling
    # the fixed-function pipeline and 3.2 support likely means 3.3 support as well.
    return (
        len(gl_version) >= 2
        and gl_version[0] >= 3
        and gl_version[1] >= 2
    )


TypeT = TypeVar('TypeT', bound=type)
def add_prc_fields(cls: TypeT) -> TypeT:
    prc_types = {
        'int': p3d.ConfigVariableInt,
        'bool': p3d.ConfigVariableBool,
        'float': p3d.ConfigVariableDouble,
        'str': p3d.ConfigVariableString,
    }

    def factoryfn(attrname: str, attrtype: str, default_value: Any) -> Any:
        name=f'simplepbr-{attrname.replace("_", "-")}'
        if isinstance(default_value, Field):
            if default_value.default_factory is not MISSING:
                default_value = default_value.default_factory()
            elif default_value.default is not MISSING:
                default_value = default_value.default
        return prc_types[attrtype](
            name=name,
            default_value=default_value,
        ).value

    def wrap(cls: type) -> type:
        annotations = cls.__dict__.get('__annotations__', {})
        for attrname, attrtype in annotations.items():
            if attrname.startswith('_'):
                # Private member, skip
                continue

            default_value = getattr(cls, attrname)
            if attrtype.startswith('Literal') and isinstance(default_value, int):
                attrtype = 'int'

            if attrtype not in prc_types:
                # Not a currently supported type, skip
                continue

            # pylint:disable-next=invalid-field-call
            setattr(cls, attrname, field(
                default_factory=functools.partial(factoryfn, attrname, attrtype, default_value)
            ))
        return cls
    return wrap(cls)

@dataclass()
@add_prc_fields
class Pipeline:
    # Class variables
    _EMPTY_ENV_MAP: ClassVar[EnvMap] = EnvMap.create_empty()
    _BRDF_LUT: ClassVar[p3d.Texture] = _load_texture('brdf_lut.txo')
    _PBR_VARS: ClassVar[list[str]] = [
        'enable_fog',
        'enable_hardware_skinning',
        'shadow_bias',
        'max_lights',
        'use_emission_maps',
        'use_normal_maps',
        'use_occlusion_maps',
        'calculate_normalmap_blue',
    ]
    _POST_PROC_VARS: ClassVar[list[str]] = [
        'camera_node',
        'msaa_samples',
        'sdr_lut',
        'window',
    ]

    # Public instance variables
    render_node: p3d.NodePath[p3d.PandaNode] = field(
        default_factory=lambda: _get_showbase_attr('render')
    )
    window: p3d.GraphicsOutput = field(default_factory=lambda: _get_showbase_attr('win'))
    camera_node: p3d.NodePath[p3d.Camera] = field(default_factory=lambda: _get_showbase_attr('cam'))
    taskmgr: TaskManager = field(default_factory=lambda: _get_showbase_attr('task_mgr'))
    msaa_samples: Literal[0, 2, 4, 8, 16] = 4
    max_lights: int = 8
    use_normal_maps: bool = False
    use_emission_maps: bool = True
    use_occlusion_maps: bool = False
    exposure: float = 0.0
    enable_shadows: bool = True
    shadow_bias: float = 0.005
    enable_fog: bool  = False
    use_330: bool = field(default_factory=_get_default_330)
    use_hardware_skinning: InitVar[bool | None] = None
    enable_hardware_skinning: bool = True
    sdr_lut: p3d.Texture | None = None
    sdr_lut_factor: float = 1.0
    env_map: EnvMap | str | None = None
    calculate_normalmap_blue: bool = True

    # Private instance variables
    _shader_ready: bool = False
    _filtermgr: FilterManager = field(init=False)
    _post_process_quad: p3d.NodePath[p3d.GeomNode] = field(init=False)
    _is_webgl: bool = field(init=False)

    def __post_init__(self, use_hardware_skinning: bool | None) -> None:
        self._shader_ready = False
        self._is_webgl = 'WebGL' in self.window.type.name

        # Create a FilterManager instance
        self._filtermgr = FilterManager(self.window, self.camera_node)
        if self._filtermgr.nextsort == -1000:
            self._filtermgr.nextsort = -9

        # Do not force power-of-two textures
        p3d.Texture.set_textures_power_2(p3d.ATS_none)

        # Make sure we have AA for if/when MSAA is enabled
        self.render_node.set_antialias(p3d.AntialiasAttrib.M_auto)

        # Add a default/fallback material
        fallback_material = p3d.Material('simplepbr-fallback')
        self.render_node.set_material(fallback_material)

        # PBR Shader
        if use_hardware_skinning is None:
            use_hardware_skinning = self.use_330
        self.enable_hardware_skinning = use_hardware_skinning
        self._recompile_pbr()

        # Tonemapping
        self._setup_tonemapping()

        # Do updates based on scene changes
        self.taskmgr.add(self._update, 'simplepbr update', sort=49)

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
            if self._filtermgr.nextsort == -1000:
                self._filtermgr.nextsort = -9

            # Create a new FilterManager instance
            self._filtermgr = FilterManager(self.window, self.camera_node)
            self._setup_tonemapping()

        if name == 'exposure':
            self._post_process_quad.set_shader_input('exposure', 2**self.exposure)
        elif name == 'sdr_lut_factor':
            self._post_process_quad.set_shader_input('sdr_lut_factor', self.sdr_lut_factor)
        elif name == 'env_map':
            self._set_env_map_uniforms()
        elif name == 'shadow_bias':
            self.render_node.set_shader_input('global_shadow_bias', self.shadow_bias)

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
        self.render_node.set_shader_input(
            'max_reflection_lod',
            filtered_env_map.num_loadable_ram_mipmap_images
        )

    def _recompile_pbr(self) -> None:
        pbr_defines = {
            'MAX_LIGHTS': self.max_lights,
            'USE_NORMAL_MAP': self.use_normal_maps,
            'USE_EMISSION_MAP': self.use_emission_maps,
            'ENABLE_SHADOWS': self.enable_shadows,
            'ENABLE_FOG': self.enable_fog,
            'USE_OCCLUSION_MAP': self.use_occlusion_maps,
            'USE_330': self.use_330,
            'IS_WEBGL': self._is_webgl,
            'ENABLE_SKINNING': self.enable_hardware_skinning,
            'CALC_NORMAL_Z': self.calculate_normalmap_blue,
        }

        pbrshader = shaderutils.make_shader(
            'pbr',
            'simplepbr.vert',
            'simplepbr.frag',
            pbr_defines
        )
        attr = p3d.ShaderAttrib.make(pbrshader)
        if self.enable_hardware_skinning:
            attr = attr.set_flag(p3d.ShaderAttrib.F_hardware_skinning, True)
        self.render_node.set_attrib(attr)
        self.render_node.set_shader_input('global_shadow_bias', self.shadow_bias)
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
        fbprops.srgb_color = False
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
            'IS_WEBGL': self._is_webgl,
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
        postquad.set_shader_input('exposure', 2**self.exposure)
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

        def is_caster(node: p3d.NodePath[p3d.PandaNode]) -> bool:
            if node.is_empty():
                return False

            pandanode = node.node()
            return hasattr(pandanode, 'is_shadow_caster') and pandanode.is_shadow_caster()

        return [
            i.node()
            for i in cameras
            if is_caster(i)
        ]

    def _create_shadow_shader_attrib(self) -> p3d.ShaderAttrib:
        defines = {
            'USE_330': self.use_330,
            'IS_WEBGL': self._is_webgl,
            'ENABLE_SKINNING': self.enable_hardware_skinning,
        }
        shader = shaderutils.make_shader(
            'shadow',
            'shadow.vert',
            'shadow.frag',
            defines
        )
        attr = p3d.ShaderAttrib.make(shader)
        if self.enable_hardware_skinning:
            attr = attr.set_flag(p3d.ShaderAttrib.F_hardware_skinning, True)
        return attr

    def _update(self, task: p3d.PythonTask) -> int:
        recompile = False
        # Use a simpler, faster shader for shadows
        for caster in self.get_all_casters():
            if isinstance(caster, p3d.PointLight):
                logging.warning(
                    f'PointLight shadow casters are not supported, disabling {caster.name}'
                )
                caster.set_shadow_caster(False)
                recompile = True
                continue
            state = caster.get_initial_state()
            if not state.has_attrib(p3d.ShaderAttrib):
                attr = self._create_shadow_shader_attrib()
                state = state.add_attrib(attr, 1)
                state = state.remove_attrib(p3d.CullFaceAttrib)
                caster.set_initial_state(state)

        if recompile:
            self._recompile_pbr()

        # Copy window background color so ShowBase.set_background_color() works
        self._filtermgr.buffers[0].set_clear_color(self.window.get_clear_color())

        self.render_node.set_shader_input(
            'camera_world_position',
            self.camera_node.get_pos(self.render_node)
        )

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
