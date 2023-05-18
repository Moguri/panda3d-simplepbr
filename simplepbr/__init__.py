import math
import os

import panda3d.core as p3d

from direct.filter.FilterManager import FilterManager

from .version import __version__
from .envmap import EnvMap
from .envpool import EnvPool

try:
    from .shaders import shaders # type: ignore
except ImportError:
    shaders = None

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
]


def load_sdr_lut(filename):
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


def sdr_lut_screenshot(showbase, *args, **kwargs):
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
                image.set_xel_val(xcoord, ycoord, (rcol, gcol, bcol))

    image.write(filename)

    return filename


def _add_shader_defines(shaderstr, defines):
    shaderlines = shaderstr.split('\n')

    for line in shaderlines:
        if '#version' in line:
            version_line = line
            break
    else:
        raise RuntimeError('Failed to find GLSL version string')
    shaderlines.remove(version_line)


    define_lines = [
        f'#define {define} {value}'
        for define, value in defines.items()
    ]

    return '\n'.join(
        [version_line]
        + define_lines
        + ['#line 1']
        + shaderlines
    )


def _load_texture(texturepath):
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


def _load_shader_str(shaderpath, defines=None):
    if shaders:
        shaderstr = shaders[shaderpath]
    else:
        shader_dir = os.path.join(os.path.dirname(__file__), 'shaders')

        with open(os.path.join(shader_dir, shaderpath)) as shaderfile:
            shaderstr = shaderfile.read()

    if defines is None:
        defines = {}

    defines['p3d_TextureBaseColor'] = 'p3d_TextureModulate'
    defines['p3d_TextureMetalRoughness'] = 'p3d_TextureSelector'
    defines['p3d_TextureNormal'] = 'p3d_TextureNormal'
    defines['p3d_TextureEmission'] = 'p3d_TextureEmission'

    shaderstr = _add_shader_defines(shaderstr, defines)

    if 'USE_330' in defines:
        shaderstr = shaderstr.replace('#version 120', '#version 330')
        if shaderpath.endswith('vert'):
            shaderstr = shaderstr.replace('varying ', 'out ')
            shaderstr = shaderstr.replace('attribute ', 'in ')
        else:
            shaderstr = shaderstr.replace('varying ', 'in ')

    return shaderstr


def _make_shader(name, vertex, fragment, defines):
    vertstr = _load_shader_str(vertex, defines)
    fragstr = _load_shader_str(fragment, defines)
    shader = p3d.Shader.make(
        p3d.Shader.SL_GLSL,
        vertstr,
        fragstr
    )
    shader.set_filename(p3d.Shader.ST_none, name)
    return shader


class Pipeline:
    def __init__(
            self,
            *,
            render_node=None,
            window=None,
            camera_node=None,
            taskmgr=None,
            msaa_samples=4,
            max_lights=8,
            use_normal_maps=False,
            use_emission_maps=True,
            exposure=1.0,
            enable_shadows=False,
            enable_fog=False,
            use_occlusion_maps=False,
            use_330=None,
            use_hardware_skinning=None,
            sdr_lut=None,
            sdr_lut_factor=1.0,
            env_map=None,
    ):
        if render_node is None:
            render_node = base.render

        if window is None:
            window = base.win

        if camera_node is None:
            camera_node = base.cam

        if taskmgr is None:
            taskmgr = base.task_mgr

        self._shader_ready = False
        self.render_node = render_node
        self.window = window
        self.camera_node = camera_node
        self.max_lights = max_lights
        self.use_normal_maps = use_normal_maps
        self.use_emission_maps = use_emission_maps
        self.enable_shadows = enable_shadows
        self.enable_fog = enable_fog
        self.exposure = exposure
        self.msaa_samples = msaa_samples
        self.use_occlusion_maps = use_occlusion_maps
        self.sdr_lut = sdr_lut
        self.sdr_lut_factor = sdr_lut_factor

        self._set_use_330(use_330)
        self.enable_hardware_skinning = use_hardware_skinning if use_hardware_skinning is not None else self.use_330

        # Create a FilterManager instance
        self.manager = FilterManager(window, camera_node)

        # Do not force power-of-two textures
        p3d.Texture.set_textures_power_2(p3d.ATS_none)

        # Make sure we have AA for if/when MSAA is enabled
        self.render_node.set_antialias(p3d.AntialiasAttrib.M_auto)

        self._brdf_lut = _load_texture('brdf_lut.txo')

        # Setup env map to be used for irradiance
        self._empty_env_map = EnvMap.create_empty()
        if env_map is None:
            env_map = self._empty_env_map
        if not isinstance(env_map, EnvMap):
            env_map = EnvPool.ptr().load(env_map)
        self.env_map = env_map

        # PBR Shader
        self._recompile_pbr()

        # Tonemapping
        self._setup_tonemapping()

        # Do updates based on scene changes
        taskmgr.add(self._update, 'simplepbr update')

        self._shader_ready = True

    def _set_use_330(self, use_330):
        if use_330 is not None:
            self.use_330 = use_330
        else:
            self.use_330 = False

            cvar = p3d.ConfigVariableInt('gl-version')
            gl_version = [
                cvar.get_word(i)
                for i in range(cvar.get_num_words())
            ]
            if len(gl_version) >= 2 and gl_version[0] >= 3 and gl_version[1] >= 2:
                # Not exactly accurate, but setting this variable to '3 2' is common for disabling
                # the fixed-function pipeline and 3.2 support likely means 3.3 support as well.
                self.use_330 = True


    def __setattr__(self, name, value):
        if hasattr(self, name):
            prev_value = getattr(self, name)
        else:
            prev_value = None
        super().__setattr__(name, value)
        if not self._shader_ready:
            return

        pbr_vars = [
            'max_lights',
            'use_normal_maps',
            'use_emission_maps',
            'enable_shadows',
            'enable_fog',
            'use_occlusion_maps',
        ]
        def resetup_tonemap():
            # Destroy previous buffers so we can re-create
            self.manager.cleanup()

            # Create a new FilterManager instance
            self.manager = FilterManager(self.window, self.camera_node)
            self._setup_tonemapping()

        if name in pbr_vars and prev_value != value:
            self._recompile_pbr()
        elif name == 'exposure':
            self.tonemap_quad.set_shader_input('exposure', self.exposure)
        elif name == 'msaa_samples':
            self._setup_tonemapping()
        elif name == 'render_node' and prev_value != value:
            self._recompile_pbr()
        elif name in ('camera_node', 'window') and prev_value != value:
            resetup_tonemap()
        elif name == 'use_330' and prev_value != value:
            self._set_use_330(value)
            self._recompile_pbr()
            resetup_tonemap()
        elif name == 'sdr_lut' and prev_value != value:
            resetup_tonemap()
        elif name == 'sdr_lut_factor' and self.sdr_lut:
            self.tonemap_quad.set_shader_input('sdr_lut_factor', self.sdr_lut_factor)
        elif name == 'env_map':
            if value is None:
                self.env_map = self._empty_env_map
            elif not isinstance(value, EnvMap):
                self.env_map = EnvPool.ptr().load(value)
            self._recompile_pbr()

    def _recompile_pbr(self):
        pbr_defines = {
            'MAX_LIGHTS': self.max_lights,
        }
        if self.use_normal_maps:
            pbr_defines['USE_NORMAL_MAP'] = ''
        if self.use_emission_maps:
            pbr_defines['USE_EMISSION_MAP'] = ''
        if self.enable_shadows:
            pbr_defines['ENABLE_SHADOWS'] = ''
        if self.enable_fog:
            pbr_defines['ENABLE_FOG'] = ''
        if self.use_occlusion_maps:
            pbr_defines['USE_OCCLUSION_MAP'] = ''
        if self.use_330:
            pbr_defines['USE_330'] = ''
        if self.enable_hardware_skinning:
            pbr_defines['ENABLE_SKINNING'] = ''

        pbrshader = _make_shader(
            'pbr',
            'simplepbr.vert',
            'simplepbr.frag',
            pbr_defines
        )
        attr = p3d.ShaderAttrib.make(pbrshader)
        if self.enable_hardware_skinning:
            attr = attr.set_flag(p3d.ShaderAttrib.F_hardware_skinning, True)
        self.render_node.set_attrib(attr)
        self.render_node.set_shader_input('sh_coeffs', self.env_map.sh_coefficients)
        self.render_node.set_shader_input('brdf_lut', self._brdf_lut)
        self.render_node.set_shader_input('filtered_env_map', self.env_map.filtered_env_map)

    def _setup_tonemapping(self):
        if self._shader_ready:
            # Destroy previous buffers so we can re-create
            self.manager.cleanup()

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
        self.tonemap_quad = self.manager.render_scene_into(colortex=scene_tex, fbprops=fbprops)

        defines = {}
        if self.use_330:
            defines['USE_330'] = ''
        if self.sdr_lut:
            defines['USE_SDR_LUT'] = ''

        tonemap_shader = _make_shader(
            'tonemap',
            'post.vert',
            'tonemap.frag',
            defines
        )
        self.tonemap_quad.set_shader(tonemap_shader)
        self.tonemap_quad.set_shader_input('tex', scene_tex)
        self.tonemap_quad.set_shader_input('exposure', self.exposure)
        if self.sdr_lut:
            self.tonemap_quad.set_shader_input('sdr_lut', self.sdr_lut)
            self.tonemap_quad.set_shader_input('sdr_lut_factor', self.sdr_lut_factor)

    def get_all_casters(self):
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

    def _create_shadow_shader_attrib(self):
        defines = {}
        if self.use_330:
            defines['USE_330'] = ''
        if self.enable_hardware_skinning:
            defines['ENABLE_SKINNING'] = ''
        shader = _make_shader(
            'shadow',
            'shadow.vert',
            'shadow.frag',
            defines
        )
        attr = p3d.ShaderAttrib.make(shader)
        if self.enable_hardware_skinning:
            attr = attr.set_flag(p3d.ShaderAttrib.F_hardware_skinning, True)
        return attr

    def _update(self, task):
        # Use a simpler, faster shader for shadows
        for caster in self.get_all_casters():
            state = caster.get_initial_state()
            if not state.has_attrib(p3d.ShaderAttrib):
                attr = self._create_shadow_shader_attrib()
                state = state.add_attrib(attr, 1)
                caster.set_initial_state(state)

        return task.cont


    def verify_shaders(self):
        gsg = self.window.gsg

        def check_shader(shader):
            shader = p3d.Shader(shader)
            shader.prepare_now(gsg.prepared_objects, gsg)
            assert shader.is_prepared(gsg.prepared_objects)
            assert not shader.get_error_flag()

        check_shader(self.render_node.get_shader())
        check_shader(self.tonemap_quad.get_shader())

        attr = self._create_shadow_shader_attrib()
        check_shader(attr.get_shader())


def init(**kwargs):
    '''Initialize the PBR render pipeline
    :param render_node: The node to attach the shader too, defaults to `base.render` if `None`
    :type render_node: `p3d.NodePath`
    :param window: The window to attach the framebuffer too, defaults to `base.win` if `None`
    :type window: `p3d.GraphicsOutput
    :param camera_node: The NodePath of the camera to use when rendering the scene, defaults to `base.cam` if `None`
    :type camera_node: `p3d.NodePath
    :param msaa_samples: The number of samples to use for multisample anti-aliasing, defaults to 4
    :type msaa_samples: int
    :param max_lights: The maximum number of lights to render, defaults to 8
    :type max_lights: int
    :param use_normal_maps: Use normal maps, defaults to `False` (NOTE: Requires models with appropriate tangents)
    :type use_normal_maps: bool
    :param use_emission_maps: Use emission maps, defaults to `True`
    :type use_emission_maps: bool
    :param exposure: a value used to multiply the screen-space color value prior to tonemapping, defaults to 1.0
    :type exposure: float
    :param enable_shadows: Enable shadow map support (breaks with point lights), defaults to False
    :type enable_shadows: bool
    :param enable_fog: Enable exponential fog, defaults to False
    :type enable_fog: bool
    :param use_occlusion_maps: Use occlusion maps, defaults to `False` (NOTE: Requires occlusion channel in
    metal-roughness map)
    :type use_occlusion_maps: bool
    :param use_330: Force the usage of GLSL 330 shaders (version 120 otherwise, auto-detect if None)
    :type use_330: bool or None
    :param use_hardware_skinning: Force usage of hardware skinning for skeleton animations
        (auto-detect if None, defaults to None)
    :type use_hardware_skinning: bool or None
    :param sdr_lut: Color LUT to use post-tonemapping
    :type sdr_lut: `p3d.Texture`
    :param sdr_lut_factor: Factor (from 0.0 to 1.0) for how much of the LUT color to mix in, defaults to 1.0
    :type sdr_lut_factor: float
    :param env_map: An environment map to use for indirect lighting (image-based lighting)
    :type env_map: `panda3d.core.Texture` (must be a cube map)
    '''

    return Pipeline(**kwargs)
