#version 120

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
uniform int tonemapping_method;

varying vec2 v_texcoord;

#ifdef USE_330
out vec4 o_color;
#endif

vec3 PBRNeutralToneMapping( vec3 color ) {
  const float startCompression = 0.8 - 0.04;
  const float desaturation = 0.15;

  float x = min(color.r, min(color.g, color.b));
  float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
  color -= offset;

  float peak = max(color.r, max(color.g, color.b));
  if (peak < startCompression) return color;

  const float d = 1. - startCompression;
  float newPeak = 1. - d * d / (peak + d - startCompression);
  color *= newPeak / peak;

  float g = 1. - 1. / (desaturation * (peak - newPeak) + 1.);
  return mix(color, newPeak * vec3(1, 1, 1), g);
}

void main() {
    vec4 tex_color = texture2D(tex, v_texcoord);
    vec3 color = tex_color.rgb;

    color *= exposure;
    color = max(vec3(0.0), color - vec3(0.004));
	if (tonemapping_method==1){
		// default filmic tonemapping
		color = (color * (vec3(6.2) * color + vec3(0.5))) / (color * (vec3(6.2) * color + vec3(1.7)) + vec3(0.06));
		//color = color / (color + vec3(1.0));
	} else if (tonemapping_method==2){
		// Khronos PBR Neutral tone mapping
		color = PBRNeutralToneMapping(color);
	}

#ifdef USE_SDR_LUT
    vec3 lut_size = vec3(textureSize(sdr_lut, 0));
    vec3 lut_uvw = (color.rgb * float(lut_size - 1.0) + 0.5) / lut_size;
    vec3 lut_color = texture3D(sdr_lut, lut_uvw).rgb;
    color = mix(color, lut_color, sdr_lut_factor);
#endif
#ifdef USE_330
    o_color = vec4(color, tex_color.a);
#else
    gl_FragColor = vec4(color, tex_color.a);
#endif
}
