#version 120

uniform struct p3d_MaterialParameters {
    vec4 baseColor;
} p3d_Material;

uniform vec4 p3d_ColorScale;

// Give texture slots names
#define p3d_TextureBaseColor p3d_Texture0
#define p3d_TextureMetalRoughness p3d_Texture1
#define p3d_TextureNormal p3d_Texture2
#define p3d_TextureEmission p3d_Texture3

uniform sampler2D p3d_TextureBaseColor;
varying vec4 v_color;
varying vec2 v_texcoord;

void main() {
    vec4 base_color = p3d_Material.baseColor * v_color * p3d_ColorScale * texture2D(p3d_TextureBaseColor, v_texcoord);
    gl_FragColor = base_color;
}
