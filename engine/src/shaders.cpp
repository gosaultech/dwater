// damned_waters/engine/src/shaders.cpp
// Purpose: the look of the game.
// CHARACTER lighting model (the "drowned house" recipe):
//   material-in-a-vertex   one uber-shader, procedural detail per material
//   procedural surfaces    marbling, black veins, bruises, mud, old blood, weave,
//                          sampled in SURFACE space so detail sticks to the body
//   bump from noise        surface-gradient bumps: pores, felt, cracks, fibres
//   wet vs dry             gloss comes from a wetness mask, never uniform
//   wrapped diffuse + SSS  flesh lets light bleed; cloth stays flat and matte
//   room lights            the same lights the Blender plates were rendered with
//   cold rim + fog         characters separate from the dark, then sink into it
// PLATE writes the pre-rendered depth into the depth buffer (see game/..).
#include "dw/shaders.hpp"

namespace dw::shaders {

const char* CHAR_VS = R"(#version 330
in vec3 vertexPosition; in vec3 vertexNormal; in vec2 vertexTexCoord; in vec4 vertexTangent; in vec4 vertexColor;
uniform mat4 mvp; uniform mat4 matModel; uniform mat4 matNormal;
out vec3 vWorld; out vec3 vNormal; out vec3 vSurf; out vec4 vColor; out float vAo; flat out int vMat;
void main() {
    vWorld = (matModel * vec4(vertexPosition, 1.0)).xyz;
    vNormal = normalize(mat3(matNormal) * vertexNormal);
    vSurf = vertexTangent.xyz;
    vColor = vertexColor;
    vMat = int(vertexTexCoord.x + 0.5);
    vAo = vertexTexCoord.y;
    gl_Position = mvp * vec4(vertexPosition, 1.0);
})";

const char* CHAR_FS = R"(#version 330
in vec3 vWorld; in vec3 vNormal; in vec3 vSurf; in vec4 vColor; in float vAo; flat in int vMat;
uniform vec3 u_camPos; uniform int u_lightCount;
uniform vec4 u_lightPos[8]; uniform vec4 u_lightCol[8]; uniform vec4 u_lightDir[8];
uniform vec3 u_ambTop; uniform vec3 u_ambBottom; uniform vec3 u_rim; uniform vec3 u_fog; uniform vec2 u_fogRange;
out vec4 finalColor;

float hash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float noise(vec3 x) {
    vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
    return mix(mix(mix(hash(i), hash(i + vec3(1,0,0)), f.x), mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
               mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x), mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z);
}
float fbm(vec3 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 5; i++) { s += a * noise(p); p *= 2.03; a *= 0.5; } return s; }
vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }
// Surface-gradient bump (Mikkelsen): perturb N by the screen-space slope of a height field.
vec3 bumpN(vec3 N, float h, float k) {
    vec3 dpx = dFdx(vWorld), dpy = dFdy(vWorld);
    float hx = dFdx(h), hy = dFdy(h);
    vec3 r1 = cross(dpy, N), r2 = cross(N, dpx);
    float det = dot(dpx, r1);
    if (abs(det) < 1e-10) return N;
    return normalize(N - k * sign(det) * (hx * r1 + hy * r2) / abs(det));
}

void main() {
    vec3 N = normalize(vNormal);
    if (!gl_FrontFacing) N = -N;   // cloth is single-skinned: light both sides
    vec3 V = normalize(u_camPos - vWorld);
    vec3 p = vSurf;
    vec3 albedo = lin(vColor.rgb);
    float spec = 0.04, gloss = 12.0, wrap = 0.2, h = 0.0, bk = 0.0, rim = 0.2;
    vec3 sss = vec3(0.0);
    float fogf = smoothstep(u_fogRange.x, u_fogRange.y, length(u_camPos - vWorld));
    if (vMat == 13) { finalColor = vec4(pow(u_fog * fogf * 0.5, vec3(1.0 / 2.2)), 1.0); return; }   // voids: mouths, wounds
    if (vMat == 1) {            // living skin: blotchy, faint pores, soft oily sheen
        albedo *= mix(0.88, 1.06, fbm(p * 40.0));
        h = fbm(p * 160.0); bk = 0.0008; spec = 0.1; gloss = 26.0; wrap = 0.45; sss = vec3(0.5, 0.12, 0.07); rim = 0.12;
    } else if (vMat == 2) {     // drowned skin: marbling, black veins, bruises, slime where wet
        float mb = fbm(p * 9.0);
        float vein = smoothstep(0.84, 0.97, 1.0 - abs(fbm(p * 13.0 + 3.1) * 2.0 - 1.0));
        albedo = mix(albedo, lin(vec3(0.3, 0.22, 0.32)), smoothstep(0.55, 0.78, mb) * 0.75);
        albedo = mix(albedo, lin(vec3(0.62, 0.64, 0.56)), smoothstep(0.7, 0.85, fbm(p * 22.0 + 5.0)) * 0.5);  // peeling
        albedo *= mix(1.0, 0.18, vein) * mix(0.8, 1.05, fbm(p * 60.0));
        float wet = smoothstep(0.45, 0.66, fbm(p * 5.0 + 7.0));
        spec = mix(0.05, 0.6, wet); gloss = mix(10.0, 80.0, wet);
        h = fbm(p * 70.0) * 0.7 + vein * 0.6; bk = 0.0025; wrap = 0.4; sss = vec3(0.08, 0.14, 0.08);
    } else if (vMat == 3) {     // coroner's sheet: dirty linen, canal mud, old blood; damp patches
        float st = fbm(p * 6.0);
        albedo = mix(albedo, albedo * vec3(0.5, 0.42, 0.3), smoothstep(0.48, 0.72, st));
        albedo = mix(albedo, lin(vec3(0.3, 0.06, 0.05)), smoothstep(0.64, 0.72, fbm(p * 8.0 + 11.0)) * 0.85);
        float weave = sin(p.x * 1400.0) * sin(p.y * 1400.0 + p.z * 1400.0);
        float wr = abs(sin(p.y * 40.0 + fbm(p * 5.0) * 6.0));   // creases running down the cloth
        h = wr * 0.6 + fbm(p * 30.0) * 0.4 + weave * 0.04; bk = 0.004;
        float wet = smoothstep(0.5, 0.7, fbm(p * 4.0 + 2.0));
        spec = mix(0.015, 0.22, wet); gloss = mix(6.0, 40.0, wet); wrap = 0.35; rim = 0.3;
    } else if (vMat == 4) {     // waterlogged wool: felted, dull, mud climbing from the hem
        albedo *= mix(0.7, 1.12, fbm(p * 90.0));
        float mud = (1.0 - smoothstep(0.1, 0.75, vWorld.y)) * smoothstep(0.3, 0.6, fbm(p * 5.0));
        albedo = mix(albedo, lin(vec3(0.2, 0.15, 0.09)), mud * 0.85);
        h = fbm(p * 110.0); bk = 0.0015; spec = 0.02; gloss = 6.0; wrap = 0.25;
    } else if (vMat == 5) {     // waxed cotton: creases, worn pale at the high points
        float cr = abs(sin(p.y * 22.0 + fbm(p * 4.0) * 4.0));
        albedo *= mix(0.72, 1.12, cr) * mix(0.88, 1.06, fbm(p * 45.0));
        h = cr * 0.7 + fbm(p * 60.0) * 0.3; bk = 0.003; spec = 0.1; gloss = 20.0; wrap = 0.25;
    } else if (vMat == 6) {     // denim twill
        float tw = sin((p.x + p.y + p.z) * 900.0) * 0.5 + 0.5;
        albedo *= mix(0.84, 1.08, tw) * mix(0.8, 1.12, fbm(p * 14.0));
        h = tw * 0.25 + fbm(p * 35.0) * 0.75; bk = 0.0015; spec = 0.03; gloss = 8.0; wrap = 0.2;
    } else if (vMat == 7) {     // leather
        albedo *= mix(0.65, 1.1, fbm(p * 35.0)); h = fbm(p * 70.0); bk = 0.002; spec = 0.25; gloss = 30.0;
    } else if (vMat == 8) {     // hair: strands, damp
        float strand = sin(p.x * 520.0 + p.z * 300.0 + fbm(p * 25.0) * 8.0) * 0.5 + 0.5;
        albedo *= mix(0.55, 1.25, strand); h = strand; bk = 0.0012; spec = 0.25; gloss = 45.0; wrap = 0.3;
    } else if (vMat == 9 || vMat == 10) { spec = 0.9; gloss = 220.0; wrap = 0.25; rim = 0.1; }   // wet eyes
    else if (vMat == 11) { albedo *= mix(0.7, 1.0, fbm(p * 50.0)); spec = 0.6; gloss = 60.0; }
    else if (vMat == 12) {     // raw flesh: fibres, wet
        float fib = abs(sin(p.y * 260.0 + fbm(p * 20.0) * 5.0));
        albedo *= mix(0.55, 1.15, fib); h = fib; bk = 0.0015; spec = 0.75; gloss = 70.0; wrap = 0.5; sss = vec3(0.35, 0.02, 0.02);
    } else if (vMat == 14) {   // leeches: ringed, slick
        float rg = sin(p.y * 600.0) * 0.5 + 0.5; albedo *= mix(0.55, 1.1, rg); h = rg; bk = 0.0008; spec = 0.9; gloss = 100.0;
    } else if (vMat == 15) { albedo *= mix(0.4, 1.0, fbm(p * 90.0)); spec = 0.04; gloss = 8.0; }
    if (bk > 0.0) N = bumpN(N, h, bk);

    vec3 col = albedo * mix(u_ambBottom, u_ambTop, N.y * 0.5 + 0.5) * vAo;
    for (int i = 0; i < 8; i++) {
        if (i >= u_lightCount) break;
        vec3 L; float att = 1.0;
        int type = int(u_lightCol[i].w + 0.5);
        if (type == 2) { L = normalize(-u_lightDir[i].xyz); }
        else {
            vec3 d = u_lightPos[i].xyz - vWorld; float dist = length(d); L = d / max(dist, 1e-4);
            float x = clamp(1.0 - pow(dist / u_lightPos[i].w, 4.0), 0.0, 1.0);
            att = x * x / (1.0 + dist * dist * 0.35);
            if (type == 1) att *= smoothstep(u_lightDir[i].w, mix(u_lightDir[i].w, 1.0, 0.3), dot(-L, normalize(u_lightDir[i].xyz)));
        }
        vec3 lc = u_lightCol[i].rgb * att;
        float ndl = dot(N, L);
        col += albedo * max((ndl + wrap) / (1.0 + wrap), 0.0) * lc * vAo;
        col += sss * (0.5 - 0.5 * ndl) * lc * 0.35;                                  // light bleeding through flesh
        col += spec * pow(max(dot(N, normalize(L + V)), 0.0), gloss) * lc * step(0.0, ndl) * vAo;
    }
    col += pow(1.0 - max(dot(N, V), 0.0), 4.0) * rim * u_rim * vAo;
    col = mix(col, u_fog, fogf * 0.6);
    finalColor = vec4(pow(max(col, 0.0), vec3(1.0 / 2.2)), 1.0);
})";

const char* PLATE_FS = R"(#version 330
in vec2 fragTexCoord;
uniform sampler2D texture0; uniform sampler2D u_depth;
uniform float u_near; uniform float u_far; uniform float u_depthMax;
out vec4 finalColor;
float decode(vec2 rg) { return (floor(rg.r * 255.0 + 0.5) * 256.0 + floor(rg.g * 255.0 + 0.5)) / 65535.0; }
void main() {
    finalColor = vec4(texture(texture0, fragTexCoord).rgb, 1.0);
    float d = max(decode(texture(u_depth, fragTexCoord).rg) * u_depthMax, u_near * 1.01);
    float zn = (u_far + u_near) / (u_far - u_near) - (2.0 * u_far * u_near) / ((u_far - u_near) * d);
    gl_FragDepth = zn * 0.5 + 0.5;
})";

const char* BLOB_FS = R"(#version 330
in vec2 fragTexCoord; out vec4 finalColor; uniform float u_strength;
void main() {
    float d = distance(fragTexCoord, vec2(0.5)) * 2.0;
    finalColor = vec4(0.0, 0.0, 0.0, (1.0 - smoothstep(0.25, 1.0, d)) * u_strength);
})";

const char* POST_FS = R"(#version 330
in vec2 fragTexCoord; uniform sampler2D texture0; uniform float u_time; uniform vec2 u_res; out vec4 finalColor;
float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void main() {
    vec3 c = texture(texture0, fragTexCoord).rgb;
    float v = smoothstep(0.4, 1.0, distance(fragTexCoord, vec2(0.5)) * 1.3);
    c *= 1.0 - v * 0.6;                                           // vignette
    c += (h(floor(fragTexCoord * u_res) + floor(u_time * 24.0) * vec2(17.0, 31.0)) - 0.5) * 0.028;   // grain
    finalColor = vec4(c, 1.0);
})";

}  // namespace dw::shaders
