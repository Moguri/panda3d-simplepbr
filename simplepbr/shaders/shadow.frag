#version 120

uniform struct p3d_MaterialParameters {
    vec4 baseColor;
} p3d_Material;

uniform vec4 p3d_ColorScale;

uniform sampler2D p3d_TextureBaseColor;
varying vec4 v_color;
varying vec2 v_texcoord;

void main() {
    vec4 base_color = p3d_Material.baseColor * v_color * p3d_ColorScale * texture2D(p3d_TextureBaseColor, v_texcoord);
    gl_FragColor = base_color;
}
