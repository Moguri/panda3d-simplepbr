#version 120

#ifdef USE_330
    #define texture2D texture
#endif

#ifdef USE_330
    #define texture2D texture
    #define texture3D texture
#endif

uniform sampler2D tex;
#ifdef USE_SDR_LUT
    uniform sampler3D sdr_lut;
    uniform float sdr_lut_factor;
#endif
uniform float exposure;

varying vec2 v_texcoord;

#ifdef USE_330
out vec4 o_color;
#endif

void main() {
    vec3 color = texture2D(tex, v_texcoord).rgb;

    color *= exposure;
    color = max(vec3(0.0), color - vec3(0.004));
    color = (color * (vec3(6.2) * color + vec3(0.5))) / (color * (vec3(6.2) * color + vec3(1.7)) + vec3(0.06));

#ifdef USE_SDR_LUT
    vec3 lut_size = vec3(textureSize(sdr_lut, 0));
    vec3 lut_uvw = (color.rgb * float(lut_size - 1.0) + 0.5) / lut_size;
    vec3 lut_color = texture3D(sdr_lut, lut_uvw).rgb;
    color = mix(color, lut_color, sdr_lut_factor);
#endif
#ifdef USE_330
    o_color = vec4(color, 1.0);
#else
    gl_FragColor = vec4(color, 1.0);
#endif
}
