#version 120

uniform mat4 p3d_ProjectionMatrix;
uniform mat4 p3d_ViewMatrix;

attribute vec4 p3d_Vertex;

varying vec3 v_texcoord;

void main() {
    v_texcoord = p3d_Vertex.xyz;
    mat4 view = mat4(mat3(p3d_ViewMatrix));
    gl_Position = p3d_ProjectionMatrix * view * p3d_Vertex;
}
