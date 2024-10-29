#version 120

uniform mat4 p3d_ProjectionMatrixInverse;
uniform mat4 p3d_ModelViewMatrix;

attribute vec4 p3d_Vertex;

varying vec3 v_texcoord;

void main() {
    mat3 inv_view = transpose(mat3(p3d_ModelViewMatrix));
    v_texcoord = inv_view * (p3d_ProjectionMatrixInverse * p3d_Vertex).xyz;
    gl_Position = p3d_Vertex;
}
