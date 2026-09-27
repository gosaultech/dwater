// damned_waters/engine/include/dw/anatomy.hpp
// Purpose: the body regions a character is split into, so parts can be hit,
// wounded and cut off separately (RE2-Remake-style dismemberment). Pure data,
// no rendering: the renderer uses it to decide what to draw, the combat rules
// use it to decide what a Drowned can still do.
// Regions form a tree: cutting an upper arm also removes the forearm hanging
// from it, the way cutting a branch takes its twigs with it.
#ifndef DW_ANATOMY_HPP
#define DW_ANATOMY_HPP

namespace dw {

enum Region : int {
    R_BODY,                 // torso, pelvis, neck, coat: never comes off
    R_HEAD, R_JAW,          // the head can burst; the jaw can be shot away
    R_UARM_L, R_FARM_L,     // upper arm (cut at the shoulder), forearm + hand (cut at the elbow)
    R_UARM_R, R_FARM_R,
    R_THIGH_L, R_SHIN_L,    // thigh (cut at the hip), shin + foot (cut at the knee)
    R_THIGH_R, R_SHIN_R,
    R_COUNT
};

// Parent of each region; -1 = root.
constexpr int REGION_PARENT[R_COUNT] = {-1,     R_BODY,    R_HEAD,   R_BODY,    R_UARM_L, R_BODY,
                                        R_UARM_R, R_BODY, R_THIGH_L, R_BODY,    R_THIGH_R};

// True if `r` is `root` or hangs (directly or indirectly) from it.
constexpr bool region_within(int r, int root) {
    for (int x = r; x >= 0; x = REGION_PARENT[x])
        if (x == root) return true;
    return false;
}

}  // namespace dw
#endif
