#version 120

#ifdef USE_330
    #define textureCube texture

    out vec4 o_color;
#endif

uniform samplerCube skybox;

varying vec3 v_texcoord;

void main() {
    vec4 color = textureCube(skybox, v_texcoord);
#ifdef USE_330
    o_color = color;
#else
    gl_FragColor = color;
#endif
}
