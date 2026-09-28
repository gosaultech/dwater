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

// Skinned bodies (u_skin = 1) blend four joint matrices per vertex (GPU skinning); rigid
// parts and rebuilt tubes (u_skin = 0) use the model matrix alone.
const char* CHAR_VS = R"(#version 330
in vec3 vertexPosition; in vec3 vertexNormal; in vec2 vertexTexCoord; in vec4 vertexTangent; in vec4 vertexColor;
in vec4 vertexBoneIds; in vec4 vertexBoneWeights;
uniform mat4 mvp; uniform mat4 matModel; uniform mat4 matNormal;
uniform mat4 boneMatrices[24]; uniform int u_skin;
out vec3 vWorld; out vec3 vNormal; out vec3 vRestN; out vec3 vSurf; out vec4 vColor; out float vAo; flat out int vMat;
void main() {
    vRestN = vertexNormal;   // before skinning: which way the surface faces in pattern space (knit columns)
    vec4 pos = vec4(vertexPosition, 1.0);
    vec3 nrm = vertexNormal;
    if (u_skin == 1) {
        mat4 S = boneMatrices[int(vertexBoneIds.x)] * vertexBoneWeights.x + boneMatrices[int(vertexBoneIds.y)] * vertexBoneWeights.y
               + boneMatrices[int(vertexBoneIds.z)] * vertexBoneWeights.z + boneMatrices[int(vertexBoneIds.w)] * vertexBoneWeights.w;
        pos = S * pos;
        nrm = mat3(S) * nrm;
    }
    vWorld = (matModel * pos).xyz;
    vNormal = normalize(mat3(matNormal) * nrm);
    vSurf = vertexTangent.xyz;
    vColor = vertexColor;
    vMat = int(vertexTexCoord.x + 0.5);
    vAo = vertexTexCoord.y;
    gl_Position = mvp * pos;
})";

const char* CHAR_FS = R"(#version 330
in vec3 vWorld; in vec3 vNormal; in vec3 vRestN; in vec3 vSurf; in vec4 vColor; in float vAo; flat in int vMat;
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
float ridge(vec3 p) { return 1.0 - abs(noise(p) * 2.0 - 1.0); }   // 1 along thin winding lines
vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }
// Hand knitting on a plane (metres): u runs across the stitch columns, v up the rows. Columns of
// "V" stitches, and every 12 columns a 4-column rope cable framed by sunken purl channels.
// Returns loop height 0..1; `aa` fades it to its average once a stitch is smaller than a pixel.
float knit(vec2 q, float aa) {
    vec2 g = q * vec2(95.0, 120.0);                        // chunky yarn: ~10.5 mm columns, ~8 mm rows
    float cx = fract(g.x) - 0.5;
    float y = fract(g.y - abs(cx) * 0.9);                  // each stitch is a V: its legs climb outward
    float st = (1.0 - abs(abs(cx) * 4.0 - 1.0)) * sin(3.14159 * y);
    float c = mod(g.x, 12.0);
    if (c > 1.0 && c < 5.0) {                              // the cable: two ropes crossing every 7 rows
        float cu = (c - 1.0) / 4.0, s = sin(6.2832 * g.y / 7.0) * 0.26;
        float rope = max(1.0 - abs(cu - 0.5 - s) / 0.24, 1.0 - abs(cu - 0.5 + s) / 0.24);
        st = clamp(rope, 0.0, 1.0) * (0.8 + 0.2 * sin(3.14159 * fract(g.y * 2.0)));
    } else if (c < 1.0 || (c > 5.0 && c < 6.0)) st *= 0.3;   // purl channels either side
    return mix(0.45, st, aa);
}
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
    int mat = vMat;
    // Seen from the inside, a body is meat: a torn scalp, a split, the far side of a cut.
    bool skinlike = mat == 1 || mat == 2 || mat == 8 || mat == 20 || mat == 23 || mat == 24;
    if (!gl_FrontFacing && skinlike) { mat = 12; albedo = lin(vec3(0.2, 0.045, 0.04)) * (vMat == 8 ? 0.45 : 1.0); }   // scalp undersides darker
    if (!gl_FrontFacing && (mat == 3 || mat == 4 || mat == 5 || mat == 6 || mat == 7 || mat == 27 || mat == 28 || mat == 32 ||
                            mat == 33 || mat == 34)) albedo *= 0.35;   // inside a garment
    if (mat == 13) { finalColor = vec4(pow(vec3(0.004, 0.001, 0.001) + u_fog * fogf * 0.5, vec3(1.0 / 2.2)), 1.0); return; }   // voids: throats, wounds
    if (mat == 36) {   // a lit lens: brightest at its centre, facing you
        float face = max(dot(N, V), 0.0);
        finalColor = vec4(pow(albedo * (1.2 + 2.2 * face * face), vec3(1.0 / 2.2)), 1.0);
        return;
    }
    if (mat == 1) {            // living skin: blotchy, faint pores, soft oily sheen; light bleeds through in its own tone
        albedo *= mix(0.9, 1.06, fbm(p * 40.0));
        h = fbm(p * 160.0); bk = 0.0008; spec = 0.12; gloss = 28.0; wrap = 0.42; rim = 0.16;
        sss = albedo * vec3(1.1, 0.42, 0.3);
    } else if (mat == 2) {     // drowned skin: marbled vessels, slipping skin, blisters, slime where wet
        albedo *= mix(0.86, 1.06, fbm(p * 8.0));
        albedo = mix(albedo, albedo * vec3(0.92, 1.02, 0.9), smoothstep(0.4, 0.7, fbm(p * 3.0 + 9.0)));   // greening
        vec3 q = p * 15.0 + vec3(fbm(p * 4.0) * 2.2);                                        // warped: vessels wander
        float ves = max(smoothstep(0.9, 0.985, ridge(q)), smoothstep(0.93, 0.99, ridge(q * 2.13 + 7.3)) * 0.7);
        float region = smoothstep(0.38, 0.62, fbm(p * 2.4 + 3.0));                            // marbling comes in patches
        albedo = mix(albedo, lin(vec3(0.2, 0.18, 0.2)), ves * region * 0.6);
        albedo = mix(albedo, lin(vec3(0.28, 0.22, 0.3)), (1.0 - smoothstep(0.1, 0.95, vWorld.y)) * 0.4);   // blood pooled low
        float sl = fbm(p * 7.0 + 11.7);                                                      // skin slippage
        float curl = smoothstep(0.615, 0.64, sl) - smoothstep(0.648, 0.67, sl);
        float raw = smoothstep(0.655, 0.675, sl);
        albedo = mix(albedo, lin(vec3(0.8, 0.78, 0.7)), curl * 0.8);
        albedo = mix(albedo, lin(vec3(0.42, 0.19, 0.17)) * mix(0.7, 1.1, fbm(p * 40.0)), raw);
        float bl = smoothstep(0.84, 0.9, noise(p * 62.0)) * (1.0 - raw);                      // gas blisters
        albedo = mix(albedo, lin(vec3(0.62, 0.62, 0.52)), bl * 0.35);
        float wet = max(smoothstep(0.45, 0.66, fbm(p * 5.0 + 7.0)), raw);
        spec = max(mix(0.05, 0.55, wet), bl * 0.7); gloss = max(mix(10.0, 80.0, wet), bl * 110.0);
        h = fbm(p * 70.0) * 0.6 + ves * region * 0.4 + bl * 0.9 - raw * 0.4 + curl * 0.5; bk = 0.0022; wrap = 0.4;
        sss = mix(vec3(0.07, 0.11, 0.07), vec3(0.3, 0.05, 0.04), raw);
    } else if (mat == 3) {     // coroner's sheet: dirty linen, canal mud, old blood; damp patches
        float st = fbm(p * 6.0);
        albedo = mix(albedo, albedo * vec3(0.5, 0.42, 0.3), smoothstep(0.48, 0.72, st));
        albedo = mix(albedo, lin(vec3(0.3, 0.06, 0.05)), smoothstep(0.64, 0.72, fbm(p * 8.0 + 11.0)) * 0.85);
        float weave = sin(p.x * 1400.0) * sin(p.y * 1400.0 + p.z * 1400.0);
        float wr = abs(sin(p.y * 40.0 + fbm(p * 5.0) * 6.0));   // creases running down the cloth
        h = wr * 0.6 + fbm(p * 30.0) * 0.4 + weave * 0.04; bk = 0.004;
        float wet = smoothstep(0.5, 0.7, fbm(p * 4.0 + 2.0));
        spec = mix(0.015, 0.22, wet); gloss = mix(6.0, 40.0, wet); wrap = 0.35; rim = 0.3;
    } else if (mat == 4) {     // waterlogged wool: felted, dull, mud climbing from the hem
        albedo *= mix(0.7, 1.12, fbm(p * 90.0));
        float mud = (1.0 - smoothstep(0.1, 0.75, vWorld.y)) * smoothstep(0.3, 0.6, fbm(p * 5.0));
        albedo = mix(albedo, lin(vec3(0.2, 0.15, 0.09)), mud * 0.85);
        h = fbm(p * 110.0); bk = 0.0015; spec = 0.02; gloss = 6.0; wrap = 0.25;
    } else if (mat == 5) {     // waxed cotton: creases, worn pale at the high points
        float cr = abs(sin(p.y * 22.0 + fbm(p * 4.0) * 4.0));
        albedo *= mix(0.72, 1.12, cr) * mix(0.88, 1.06, fbm(p * 45.0));
        h = cr * 0.7 + fbm(p * 60.0) * 0.3; bk = 0.003; spec = 0.1; gloss = 20.0; wrap = 0.25;
    } else if (mat == 6) {     // denim twill
        float tw = sin((p.x + p.y + p.z) * 900.0) * 0.5 + 0.5;
        albedo *= mix(0.84, 1.08, tw) * mix(0.8, 1.12, fbm(p * 14.0));
        h = tw * 0.25 + fbm(p * 35.0) * 0.75; bk = 0.0015; spec = 0.03; gloss = 8.0; wrap = 0.2;
    } else if (mat == 7) {     // leather: a soft satin sheen, pebbled grain, a sharper shine only where it's worn smooth
        float worn = smoothstep(0.5, 0.78, fbm(p * 6.0));
        float aa = clamp(1.5 - length(fwidth(p)) * 500.0, 0.0, 1.0);
        float pebble = mix(0.5, noise(p * 900.0) * 0.6 + noise(p * 430.0) * 0.4, aa);
        albedo *= mix(0.85, 1.12, fbm(p * 35.0)) * mix(1.0, 1.22, worn);
        h = pebble * 0.55 + fbm(p * 26.0) * 0.45; bk = 0.0012 * (1.0 - worn * 0.6);
        spec = mix(0.055, 0.14, worn); gloss = mix(9.0, 26.0, worn); wrap = 0.25; rim = 0.22;
    } else if (mat == 8) {     // hair: tight curls, matte, a soft rim
        float curl = noise(p * 700.0) * 0.6 + noise(p * 260.0) * 0.4;
        albedo *= mix(0.7, 1.15, curl); h = curl; bk = 0.00035; spec = 0.05; gloss = 14.0; wrap = 0.35; rim = 0.35;
    } else if (mat == 9 || mat == 10) { spec = 0.9; gloss = 220.0; wrap = 0.25; rim = 0.1; }   // wet eyes
    else if (mat == 11) { albedo *= mix(0.7, 1.0, fbm(p * 50.0)); spec = 0.6; gloss = 60.0; }
    else if (mat == 12) {     // raw flesh: fibres, wet
        float fib = abs(sin(p.y * 260.0 + fbm(p * 20.0) * 5.0));
        albedo *= mix(0.55, 1.15, fib); h = fib; bk = 0.0015; spec = 0.75; gloss = 70.0; wrap = 0.5; sss = vec3(0.35, 0.02, 0.02);
    } else if (mat == 14) {   // leeches: ringed, slick
        float rg = sin(p.y * 600.0) * 0.5 + 0.5; albedo *= mix(0.55, 1.1, rg); h = rg; bk = 0.0008; spec = 0.9; gloss = 100.0;
    } else if (mat == 15) { albedo *= mix(0.4, 1.0, fbm(p * 90.0)); spec = 0.04; gloss = 8.0; }
    else if (mat == 16) {     // dead eye: milky, clouded cornea under a wet film
        albedo *= mix(0.86, 1.04, fbm(p * 120.0)); spec = 0.9; gloss = 240.0; wrap = 0.35; rim = 0.25;
        sss = vec3(0.12, 0.13, 0.14);
    } else if (mat == 17) {   // teeth: yellowed, stained at the gumline
        albedo *= mix(0.7, 1.05, fbm(p * 90.0)); h = fbm(p * 200.0); bk = 0.0006; spec = 0.35; gloss = 50.0; wrap = 0.3;
    } else if (mat == 18) {   // bone: dirty ivory, pitted, wet
        albedo *= mix(0.78, 1.06, fbm(p * 45.0)); h = fbm(p * 150.0); bk = 0.0012; spec = 0.3; gloss = 35.0; wrap = 0.3;
    } else if (mat == 19) {   // tongue: swollen, papillae, glossy
        albedo *= mix(0.7, 1.15, fbm(p * 60.0)); h = noise(p * 380.0); bk = 0.0009; spec = 0.6; gloss = 70.0; wrap = 0.45;
        sss = vec3(0.25, 0.03, 0.06);
    } else if (mat == 20) {   // intestine: grey-pink, fine vessels, slick
        float ves = smoothstep(0.86, 0.97, 1.0 - abs(fbm(p * 30.0) * 2.0 - 1.0));
        albedo = mix(albedo * mix(0.8, 1.1, fbm(p * 25.0)), lin(vec3(0.45, 0.08, 0.1)), ves * 0.7);
        h = fbm(p * 90.0); bk = 0.001; spec = 0.8; gloss = 85.0; wrap = 0.55; sss = vec3(0.4, 0.12, 0.12);
    } else if (mat == 21) {   // mussel shell: growth rings, lacquered wet
        float gr = sin(length(p) * 1400.0) * 0.5 + 0.5;
        albedo *= mix(0.82, 1.08, gr); h = gr; bk = 0.0005; spec = 0.55; gloss = 60.0;
    } else if (mat == 22) {   // canal weed: slimy, light glows through it
        albedo *= mix(0.6, 1.2, fbm(p * 50.0)); spec = 0.5; gloss = 40.0; wrap = 0.6; sss = vec3(0.1, 0.18, 0.05);
    } else if (mat == 23) {   // loose skin: bleached, wrinkled like a washerwoman's fingers, wet
        float wr = abs(sin(p.y * 170.0 + fbm(p * 30.0) * 5.0));
        albedo *= mix(0.72, 1.06, wr) * mix(0.9, 1.05, fbm(p * 70.0));
        h = wr; bk = 0.0012; spec = 0.35; gloss = 35.0; wrap = 0.5; sss = vec3(0.2, 0.16, 0.12);
    } else if (mat == 28) {   // chunky cable knit, projected three ways by which way the cloth faces at rest
        vec3 w = pow(abs(normalize(vRestN)), vec3(6.0));
        w /= max(w.x + w.y + w.z, 1e-4);
        float aa = clamp((1.3 - length(fwidth(p)) * 110.0) / 0.8, 0.0, 1.0);
        float k = knit(p.xy, aa) * w.z + knit(p.zy, aa) * w.x + knit(p.xz, aa) * w.y;
        albedo *= mix(0.66, 1.05, k) * mix(0.93, 1.03, fbm(p * 30.0));
        h = k; bk = 0.0024; spec = 0.02; gloss = 6.0; wrap = 0.55; rim = 0.55;
    } else if (mat == 29) {   // lips: skin with a moist sheen
        albedo *= mix(0.9, 1.05, fbm(p * 90.0)); h = fbm(p * 260.0); bk = 0.0006; spec = 0.28; gloss = 45.0; wrap = 0.45;
        sss = albedo * vec3(1.0, 0.35, 0.3);
    } else if (mat == 30) {   // brows: short dark hairs
        float st = sin(p.x * 900.0 + p.y * 300.0) * 0.5 + 0.5;
        albedo *= mix(0.6, 1.1, st); h = st; bk = 0.0005; spec = 0.08; gloss = 20.0;
    } else if (mat == 31) {   // rubber soles
        albedo *= mix(0.8, 1.05, fbm(p * 60.0)); spec = 0.05; gloss = 10.0;
    } else if (mat == 32) {   // nylon: smooth, glossy, crinkled
        float cr = fbm(p * 24.0);
        albedo *= mix(0.86, 1.06, cr); h = cr; bk = 0.0022; spec = 0.22; gloss = 30.0; rim = 0.25;
    } else if (mat == 33) {   // cotton: matte, fine weave
        float wv = sin(p.x * 1200.0) * sin(p.y * 1200.0);
        albedo *= mix(0.88, 1.04, fbm(p * 40.0)); h = wv * 0.3 + fbm(p * 60.0) * 0.7; bk = 0.0012; spec = 0.03; gloss = 8.0; wrap = 0.35;
    } else if (mat == 34) {   // printed fabric: small flowers over the base colour
        vec3 q = p * 38.0;
        vec3 cell = floor(q);
        float rnd = hash(cell);
        float petal = length(fract(q) - 0.5 - (rnd - 0.5) * 0.3);
        float flower = 1.0 - smoothstep(0.12, 0.2, petal);
        albedo = mix(albedo, mix(lin(vec3(0.62, 0.52, 0.28)), lin(vec3(0.55, 0.18, 0.2)), step(0.5, rnd)), flower * step(0.35, rnd));
        h = fbm(p * 50.0); bk = 0.001; spec = 0.03; gloss = 8.0; wrap = 0.35;
    } else if (mat == 35) {   // locs: palm-rolled rope, matted and fuzzy, a dull sheen (p: around, along, seed)
        float ang = 6.2832 * p.x;
        vec3 cyl = vec3(cos(ang) * 1.3, sin(ang) * 1.3, p.y * 160.0 + p.z);
        float aa = clamp(1.4 - fwidth(p.y * 90.0) * 1.5, 0.0, 1.0);
        float tw = mix(0.5, sin(ang * 2.0 + p.y * 560.0) * 0.5 + 0.5, aa);    // two plies wrapping round
        float fuzz = fbm(cyl), lumps = fbm(vec3(p.z * 3.1, p.y * 45.0, 0.5));
        albedo *= mix(0.7, 1.08, tw * 0.45 + fuzz * 0.55) * mix(0.82, 1.12, lumps);
        h = tw * 0.5 + fuzz * 0.5; bk = 0.0009; spec = 0.05; gloss = 10.0; wrap = 0.3; rim = 0.06;   // thin tubes are mostly edge: keep the rim faint
    } else if (mat == 24) {   // raw dermis where the outer skin slipped off: wet and pink
        albedo *= mix(0.7, 1.1, fbm(p * 55.0)); h = fbm(p * 140.0); bk = 0.0008; spec = 0.55; gloss = 65.0; wrap = 0.5;
        sss = vec3(0.28, 0.05, 0.04);
    }
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
