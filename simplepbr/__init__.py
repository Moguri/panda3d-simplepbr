import os

import panda3d.core as p3d

from direct.filter.FilterManager import FilterManager

from .version import __version__


__all__ = [
    'init',
    'Pipeline'
]



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


def _load_shader_str(shaderpath, defines=None):
    shader_dir = os.path.dirname(__file__)

    with open(os.path.join(shader_dir, shaderpath)) as shaderfile:
        shaderstr = shaderfile.read()

    if defines is not None:
        shaderstr = _add_shader_defines(shaderstr, defines)

    return shaderstr

class Pipeline:
    def __init__(
            self,
            *,
            render_node=None,
            window=None,
            camera_node=None,
            msaa_samples=4,
            max_lights=8,
            use_normal_maps=False,
            use_emission_maps=False,
            exposure=1.0,
            enable_shadows=False,
            enable_fog=False,
    ):
        if render_node is None:
            render_node = base.render

        if window is None:
            window = base.win

        if camera_node is None:
            camera_node = base.cam

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

        # Create a FilterManager instance
        self.manager = FilterManager(window, camera_node)

        # Do not force power-of-two textures
        p3d.Texture.set_textures_power_2(p3d.ATS_none)

        # Make sure we have AA for if/when MSAA is enabled
        self.render_node.set_antialias(p3d.AntialiasAttrib.M_auto)

        # PBR Shader
        self._recompile_pbr()

        # Tonemapping
        self._setup_tonemapping()

        self._shader_ready = True

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
        ]
        if name in pbr_vars and prev_value != value:
            self._recompile_pbr()
        elif name == 'exposure':
            self.tonemap_quad.set_shader_input('exposure', self.exposure)
        elif name == 'msaa_samples':
            self._setup_tonemapping()

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

        pbr_vert_str = _load_shader_str('simplepbr.vert', pbr_defines)
        pbr_frag_str = _load_shader_str('simplepbr.frag', pbr_defines)
        pbrshader = p3d.Shader.make(
            p3d.Shader.SL_GLSL,
            vertex=pbr_vert_str,
            fragment=pbr_frag_str,
        )
        self.render_node.set_shader(pbrshader)

    def _setup_tonemapping(self):
        if self._shader_ready:
            # Destroy previous buffers so we can re-create
            self.manager.cleanup()

            # Fix shadow buffers after FilterManager.cleanup()
            for casternp in self.render_node.find_all_matches('**/+LightLensNode'):
                caster = casternp.node()
                if caster.is_shadow_caster():
                    # caster.set_shadow_caster(False)
                    # caster.set_shadow_caster(True)
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

        post_vert_str = _load_shader_str('post.vert')
        post_frag_str = _load_shader_str('tonemap.frag')
        tonemap_shader = p3d.Shader.make(
            p3d.Shader.SL_GLSL,
            vertex=post_vert_str,
            fragment=post_frag_str,
        )
        self.tonemap_quad.set_shader(tonemap_shader)
        self.tonemap_quad.set_shader_input('tex', scene_tex)
        self.tonemap_quad.set_shader_input('exposure', self.exposure)


def init(*,
         render_node=None,
         window=None,
         camera_node=None,
         msaa_samples=4,
         max_lights=8,
         use_normal_maps=False,
         use_emission_maps=False,
         exposure=1.0,
         enable_shadows=False,
         enable_fog=False,
         ):
    '''Initialize the PBR render pipeline
    :param render_node: The node to attach the shader too, defaults to `base.render` if `None`
    :type render_node: `panda3d.core.NodePath`
    :param window: The window to attach the framebuffer too, defaults to `base.win` if `None`
    :type window: `panda3d.core.GraphicsOutput
    :param camera_node: The NodePath of the camera to use when rendering the scene, defaults to `base.cam` if `None`
    :type camera_node: `panda3d.core.NodePath
    :param msaa_samples: The number of samples to use for multisample anti-aliasing, defaults to 4
    :type msaa_samples: int
    :param max_lights: The maximum number of lights to render, defaults to 8
    :type max_lights: int
    :param use_normal_maps: Use normal maps, defaults to `False` (NOTE: Requires models with appropriate tangents)
    :type use_normal_maps: bool
    :param use_emission_maps: Use emission maps, defaults to `False`
    :type use_emission_maps: bool
    :param exposure: a value used to multiply the screen-space color value prior to tonemapping, defaults to 1.0
    :type exposure: float
    :param enable_shadows: Enable shadow map support (breaks with point lights), defaults to False
    :type enable_shadows: bool
    :param enable_fog: Enable exponential fog, defaults to False
    :type enable_fog: bool
    '''

    return Pipeline(
        render_node=render_node,
        window=window,
        camera_node=camera_node,
        msaa_samples=msaa_samples,
        max_lights=max_lights,
        use_normal_maps=use_normal_maps,
        use_emission_maps=use_emission_maps,
        exposure=exposure,
        enable_shadows=enable_shadows,
        enable_fog=enable_fog,
    )
