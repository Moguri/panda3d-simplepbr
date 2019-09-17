import os

import panda3d.core as p3d

from direct.filter.FilterManager import FilterManager

from .version import __version__


__all__ = [
    'init',
]


def init(*, render_node=None, window=None, camera_node=None):
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
        pbr_frag_str = fragfile.read()

    pbrshader = p3d.Shader.make(
        p3d.Shader.SL_GLSL,
        vertex=pbr_vert_str,
        fragment=pbr_frag_str,
    )
    render_node.set_shader(pbrshader)

    # Tonemapping
    manager = FilterManager(window, camera_node)
    tonemap_tex = p3d.Texture()
    tonemap_tex.set_component_type(p3d.Texture.T_float)
    tonemap_quad = manager.render_scene_into(colortex=tonemap_tex)
    tonemap_shader = p3d.Shader.load(
        p3d.Shader.SL_GLSL,
        vertex=os.path.join(shader_dir, 'post.vert'),
        fragment=os.path.join(shader_dir, 'tonemap.frag')
    )
    tonemap_quad.set_shader(tonemap_shader)
    tonemap_quad.set_shader_input('tex', tonemap_tex)
