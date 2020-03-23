#version 120

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat3 p3d_NormalMatrix;

attribute vec4 p3d_Vertex;
attribute vec4 p3d_Color;
attribute vec3 p3d_Normal;
attribute vec4 p3d_Tangent;
attribute vec2 p3d_MultiTexCoord0;


varying vec3 v_position;
varying vec4 v_color;
varying mat3 v_tbn;
varying vec2 v_texcoord;

void main() {
    v_position = vec3(p3d_ModelViewMatrix * p3d_Vertex);
    v_color = p3d_Color;
    vec3 normal = normalize(p3d_NormalMatrix * p3d_Normal);
    v_texcoord = p3d_MultiTexCoord0;

    vec3 tangent = normalize(vec3(p3d_ModelViewMatrix * vec4(p3d_Tangent.xyz, 0.0)));
    vec3 bitangent = cross(normal, tangent) * p3d_Tangent.w;
    v_tbn = mat3(
        tangent,
        bitangent,
        normal
    );

    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
}
