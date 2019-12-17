import os

import panda3d.core as p3d

from direct.filter.FilterManager import FilterManager

from .version import __version__


__all__ = [
    'init',
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


def init(*, render_node=None, window=None, camera_node=None, msaa_samples=4, max_lights=8, use_normal_maps=False):
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
    '''

    if render_node is None:
        render_node = base.render

    if window is None:
        window = base.win

    if camera_node is None:
        camera_node = base.cam


    # Do not force power-of-two textures
    p3d.Texture.set_textures_power_2(p3d.ATS_none)

    # PBR shader
    pbr_defines = {
        'MAX_LIGHTS': max_lights,
    }
    if use_normal_maps:
        pbr_defines['USE_NORMAL_MAP'] = ''

    pbr_vert_str = _load_shader_str('simplepbr.vert', pbr_defines)
    pbr_frag_str = _load_shader_str('simplepbr.frag', pbr_defines)
    pbrshader = p3d.Shader.make(
        p3d.Shader.SL_GLSL,
        vertex=pbr_vert_str,
        fragment=pbr_frag_str,
    )
    render_node.set_shader(pbrshader)

    # Tonemapping
    manager = FilterManager(window, camera_node)
    fbprops = p3d.FrameBufferProperties()
    fbprops.float_color = True
    fbprops.set_rgba_bits(16, 16, 16, 16)
    fbprops.set_depth_bits(24)
    fbprops.set_multisamples(msaa_samples)
    scene_tex = p3d.Texture()
    scene_tex.set_format(p3d.Texture.F_rgba16)
    scene_tex.set_component_type(p3d.Texture.T_float)
    tonemap_quad = manager.render_scene_into(colortex=scene_tex, fbprops=fbprops)

    post_vert_str = _load_shader_str('post.vert')
    post_frag_str = _load_shader_str('tonemap.frag')
    tonemap_shader = p3d.Shader.make(
        p3d.Shader.SL_GLSL,
        vertex=post_vert_str,
        fragment=post_frag_str,
    )
    tonemap_quad.set_shader(tonemap_shader)
    tonemap_quad.set_shader_input('tex', scene_tex)
