from __future__ import annotations

import panda3d.core as p3d

from . import _shaderutils as shaderutils

def make_skybox(cubemap: p3d.Texture) -> p3d.NodePath[p3d.GeomNode]:
    verts = [
        -1.0,  1.0, -1.0,
        -1.0, -1.0, -1.0,
         1.0, -1.0, -1.0,
         1.0, -1.0, -1.0,
         1.0,  1.0, -1.0,
        -1.0,  1.0, -1.0,

        -1.0, -1.0,  1.0,
        -1.0, -1.0, -1.0,
        -1.0,  1.0, -1.0,
        -1.0,  1.0, -1.0,
        -1.0,  1.0,  1.0,
        -1.0, -1.0,  1.0,

         1.0, -1.0, -1.0,
         1.0, -1.0,  1.0,
         1.0,  1.0,  1.0,
         1.0,  1.0,  1.0,
         1.0,  1.0, -1.0,
         1.0, -1.0, -1.0,

        -1.0, -1.0,  1.0,
        -1.0,  1.0,  1.0,
         1.0,  1.0,  1.0,
         1.0,  1.0,  1.0,
         1.0, -1.0,  1.0,
        -1.0, -1.0,  1.0,

        -1.0,  1.0, -1.0,
         1.0,  1.0, -1.0,
         1.0,  1.0,  1.0,
         1.0,  1.0,  1.0,
        -1.0,  1.0,  1.0,
        -1.0,  1.0, -1.0,

        -1.0, -1.0, -1.0,
        -1.0, -1.0,  1.0,
         1.0, -1.0, -1.0,
         1.0, -1.0, -1.0,
        -1.0, -1.0,  1.0,
         1.0, -1.0,  1.0,
    ]
    num_verts = len(verts) // 3


    vdata = p3d.GeomVertexData('skybox', p3d.GeomVertexFormat.get_v3(), p3d.Geom.UH_static)
    vdata.set_num_rows(num_verts)

    vertex = p3d.GeomVertexWriter(vdata, 'vertex')
    for idx in range(0, len(verts), 3):
        vertex.add_data3(*verts[idx:idx+3])

    primitive = p3d.GeomTriangles(p3d.Geom.UH_static)
    primitive.add_consecutive_vertices(0, num_verts)

    geom = p3d.Geom(vdata)
    geom.add_primitive(primitive)

    node = p3d.GeomNode('skybox')
    node.add_geom(geom)
    node.set_bounds(p3d.OmniBoundingVolume())

    np = p3d.NodePath(node)
    shader = shaderutils.make_shader(
        'skybox',
        'skybox.vert',
        'skybox.frag',
        {}
    )
    np.set_shader(shader)
    np.set_shader_input('skybox', cubemap)
    np.set_depth_write(False)
    np.set_bin('background', 0)

    return np
