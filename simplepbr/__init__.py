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


def init(*, render_node=None, window=None, camera_node=None, msaa_samples=4, max_lights=8):
    '''Initialize the PBR render pipeline
    :param render_node: The node to attach the shader too, defaults to `base.render` if `None`
    :type render_node: `panda3d.core.NodePath`
    :param window: The window to attach the framebuffer too, defaults to `base.win` if `None`
    :type window: `panda3d.core.GraphicsOutput
    :param camera_node: The NodePath of the camera to use when rendering the scene, defaults to `base.cam` if `None`
    :type camera_node: `panda3d.core.NodePath
    '''

    if render_node is None:
        render_node = base.render

    if window is None:
        window = base.win

    if camera_node is None:
        camera_node = base.cam

    shader_dir = os.path.dirname(__file__)

    # Do not force power-of-two textures
    p3d.Texture.set_textures_power_2(p3d.ATS_none)

    # PBR shader
    with open(os.path.join(shader_dir, 'simplepbr.vert')) as vertfile:
        pbr_vert_str = vertfile.read()
    with open(os.path.join(shader_dir, 'simplepbr.frag')) as fragfile:
        pbr_frag_defines = {
            'MAX_LIGHTS': max_lights,
        }
        pbr_frag_str = _add_shader_defines(fragfile.read(), pbr_frag_defines)
        print(pbr_frag_str)

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
    tonemap_shader = p3d.Shader.load(
        p3d.Shader.SL_GLSL,
        vertex=os.path.join(shader_dir, 'post.vert'),
        fragment=os.path.join(shader_dir, 'tonemap.frag')
    )
    tonemap_quad.set_shader(tonemap_shader)
    tonemap_quad.set_shader_input('tex', scene_tex)
