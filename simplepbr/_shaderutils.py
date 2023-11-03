from __future__ import annotations

import os

from typing_extensions import (
    TYPE_CHECKING,
    TypeAlias,
)

import panda3d.core as p3d

if TYPE_CHECKING:
    from typing import Any

try:
    from .shaders import shaders # type: ignore
except ImportError:
    shaders = None


ShaderDefinesType: TypeAlias = 'dict[str, Any]'


def _add_shader_defines(shaderstr: str, defines: ShaderDefinesType) -> str:
    shaderlines = shaderstr.split('\n')

    for line in shaderlines:
        if '#version' in line:
            version_line = line
            break
    else:
        raise RuntimeError('Failed to find GLSL version string')
    shaderlines.remove(version_line)

    define_lines = [
        f'#define {define} {value if value is not True else ""}'
        for define, value in defines.items()
        if value
    ]

    return '\n'.join(
        [version_line]
        + define_lines
        + ['#line 1']
        + shaderlines
    )


def _load_shader_str(shaderpath: str, defines: ShaderDefinesType | None = None) -> str:
    shaderstr = ''

    if shaders:
        shaderstr = shaders[shaderpath]
    else:
        shader_dir = os.path.join(os.path.dirname(__file__), 'shaders')

        with open(os.path.join(shader_dir, shaderpath), encoding='utf8') as shaderfile:
            shaderstr = shaderfile.read()

    if defines is None:
        defines = {}

    defines['p3d_TextureBaseColor'] = 'p3d_TextureModulate'
    defines['p3d_TextureMetalRoughness'] = 'p3d_TextureSelector'

    shaderstr = _add_shader_defines(shaderstr, defines)
    if 'USE_330' in defines:
        shaderstr = shaderstr.replace('#version 120', '#version 330')
        if shaderpath.endswith('vert'):
            shaderstr = shaderstr.replace('varying ', 'out ')
            shaderstr = shaderstr.replace('attribute ', 'in ')
        else:
            shaderstr = shaderstr.replace('varying ', 'in ')

    return shaderstr


def make_shader(name: str, vertex: str, fragment: str, defines: ShaderDefinesType) -> p3d.Shader:
    vertstr = _load_shader_str(vertex, defines)
    fragstr = _load_shader_str(fragment, defines)
    shader = p3d.Shader.make(
        p3d.Shader.SL_GLSL,
        vertstr,
        fragstr
    )
    shader.set_filename(p3d.Shader.ST_none, name)
    return shader
