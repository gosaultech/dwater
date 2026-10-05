// damned_waters/engine/src/main.cpp
// Purpose: entry point. Normal play, or --capture DIR to stage fixed setups
// and save screenshots (used to review the look without playing).
//   ./damned_waters                 play: WASD move, Shift run, Q quick turn, RMB/K aim (W/S: head/legs),
//                                   LMB/J/Space fire, R reload, 1/2/F guns, C/Alt dodge, E kick, L flashlight,
//                                   T tank/modern, F3 debug; Enter after dying to try again
//   --flashlight                    start with the flashlight on (also for --capture)
//   ./damned_waters --capture out   stage + screenshot every setup, then exit
//   ./damned_waters --room proef --still 3.2,2.2,163 out.png [--shot c]
//                                   the survivor standing in a room (x, z, yaw degrees), one frame, then exit;
//                                   DW_ROOT=<dir> reads rooms, plates and audio from another tree
//   ./damned_waters --sheet out     studio turnaround of the cast (model review), then exit
//                                   (--only pieter,survivor: just those subjects)
//   ./damned_waters --view survivor,25,10,0.6,0,0.9,30 out.png   one full-resolution studio shot
//                                   (who, orbit, elevation, distance, target x, target height, fov), then exit;
//                                   who: survivor | drowned[N] [@head | @chest | @pelvis | @hand],
//                                   or a gun, catalogue-lit: m92fs | r870 (see Game::gun_view)
//   ./damned_waters --fitgrips      a tool: fit his hands to both guns as people hold them, write
//                                   src/grips_fitted.inc, then exit
//   ./damned_waters --fitpistol     a tool: fit the pistol in both hands (aiming: the right arm and
//                                   wrist, the head; at the low ready and running: the arms; the left
//                                   hand goes on by IK), print it for the pose tables, exit
//   ./damned_waters --fit870        a tool: fit the hold on the 870 (aim, low ready, reload: arms,
//                                   wrists and the turn of his back; aiming, also his head and lean,
//                                   the cheek down on the stock), print it for the pose tables, exit
//   ./damned_waters --clearance     a tool: play each way he carries a gun (standing, walking, running,
//                                   raising it and lowering it) and each reload through and print, step
//                                   by step, how deep his arms, hands and gun go into his body (and each
//                                   other), his wrists, and where his trigger finger is
//   ./damned_waters --fitreload     a tool: fit where the pistol is brought in to reload (least wrist
//                                   strain, nothing through anything), print it, exit
//   ./damned_waters --frames 600    auto-exit (smoke tests)
#include <raylib.h>
#include <rlgl.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>

#include "dw/character.hpp"
#include "dw/room_spec.hpp"
#include "dw/telemetry.hpp"
#include "game.hpp"

int main(int argc, char** argv) {
    std::string capture, sheet, only, view, view_png, room = "gang", still, still_png, shot;
    long max_frames = -1;
    for (int i = 1; i + 1 < argc; ++i) {
        std::string a = argv[i];
        if (a == "--capture") capture = argv[++i];
        else if (a == "--sheet") sheet = argv[++i];
        else if (a == "--only") only = argv[++i];
        else if (a == "--view" && i + 2 < argc) { view = argv[++i]; view_png = argv[++i]; }
        else if (a == "--room") room = argv[++i];
        else if (a == "--still" && i + 2 < argc) { still = argv[++i]; still_png = argv[++i]; }
        else if (a == "--shot") shot = argv[++i];
        else if (a == "--frames") max_frames = std::stol(argv[++i]);
    }
    bool flashlight = false, fit870 = false, fitgrips = false, fitpistol = false, clear = false, fitreload = false;
    for (int i = 1; i < argc; ++i) {
        flashlight = flashlight || std::string(argv[i]) == "--flashlight";
        fit870 = fit870 || std::string(argv[i]) == "--fit870";   // a tool: fit the shotgun hold, print it, exit
        fitgrips = fitgrips || std::string(argv[i]) == "--fitgrips";   // a tool: fit the hands to the guns, write them, exit
        fitpistol = fitpistol || std::string(argv[i]) == "--fitpistol";
        clear = clear || std::string(argv[i]) == "--clearance";   // a tool: play the reloads through, say what goes through what, exit
        fitreload = fitreload || std::string(argv[i]) == "--fitreload";   // a tool: fit where the pistol goes to reload, print it, exit
    }
    SetConfigFlags(FLAG_VSYNC_HINT | FLAG_WINDOW_RESIZABLE);
    InitWindow(dw::Game::W, dw::Game::H, "Damned Waters");
    SetExitKey(KEY_NULL);   // Esc pauses (the menu has Quit)
    SetTargetFPS(60);
    dw::Telemetry tel(std::string(GetApplicationDirectory()) + "damned_waters.db");
    tel.begin(!view.empty() ? "view" : !sheet.empty() ? "sheet" : capture.empty() ? "play" : "capture", room);
    dw::Game game;
    game.flashlight = flashlight;
    game.settings_path = std::string(GetApplicationDirectory()) + "damned_waters.db";   // the options live next to the telemetry
    if (!game.init(room)) {
        tel.end("init_failed", 0, 0, 0);
        CloseWindow();
        return 1;
    }
    double start = GetTime(), worst = 0;
    long frames = 0;
    if (fitreload) {
        dw::Character c = dw::Character::make(dw::Kind::Survivor);
        TraceLog(LOG_INFO, "FITRELOAD%s", c.fit_reload().c_str());
        c.unload();
    } else if (clear) {
        dw::Character c = dw::Character::make(dw::Kind::Survivor);
        const char* part = std::getenv("DW_CLEAR_ONLY");   // (stance or reload: just that half)
        if (!part || std::string(part) == "stance") TraceLog(LOG_INFO, "CLEARANCE (carrying the guns)%s", c.stance_clearance().c_str());
        if (!part || std::string(part) == "reload") TraceLog(LOG_INFO, "CLEARANCE (the reloads)%s", c.reload_clearance().c_str());
        c.unload();
    } else if (fitgrips) {
        dw::Character c = dw::Character::make(dw::Kind::Survivor);
        TraceLog(LOG_INFO, "FITGRIPS\n%s", c.fit_grips(dw::repo_root() + "/engine/src/grips_fitted.inc").c_str());
        c.unload();
    } else if (fitpistol) {
        dw::Character c = dw::Character::make(dw::Kind::Survivor);
        dw::Character::PistolFit aim, low, run;
        // The low ready, standing and walking: the gun low in front of him on his middle line, between
        // his belly and the bottom of his chest, the muzzle at the floor 1.5 to 2 m ahead.
        low.sights = false;
        low.grip_at = {0.02f, -0.30f, -0.48f};
        low.grip_band = {0.04f, 0.06f, 0.1f};
        low.floor_near = 1.5f;
        low.floor_far = 2.0f;
        low.pose = dw::Pose::Idle;
        // Running: the low ready still, on his running body (leaning into it), the gun pulled in a
        // little and the muzzle at the floor a little nearer. (Pulled in close to his chest, a
        // compressed ready, this rig's one-piece palm would bend the wrists past 55 degrees.)
        run.sights = false;
        run.grip_at = {0.02f, -0.30f, -0.46f};
        run.grip_band = {0.04f, 0.06f, 0.08f};
        run.floor_near = 1.3f;
        run.floor_far = 1.8f;
        run.pose = dw::Pose::Run;
        const char* only = std::getenv("DW_FIT_ONLY");   // (aim, low or run: just that one)
        auto want = [only](const char* id) { return !only || std::string(only) == id; };
        if (want("aim")) TraceLog(LOG_INFO, "FIT pistol aim %s", c.fit_pistol(aim).c_str());
        if (want("low")) TraceLog(LOG_INFO, "FIT pistol low ready %s", c.fit_pistol(low).c_str());
        if (want("run")) TraceLog(LOG_INFO, "FIT pistol running %s", c.fit_pistol(run).c_str());
        c.unload();
    } else if (fit870) {
        dw::Character c = dw::Character::make(dw::Kind::Survivor);
        dw::Character::ShotgunFit aim, low, reload;
        // The low ready: the muzzle 35 degrees down, the butt dropped from the shoulder pocket to just
        // under it, on the chest by the armpit (pinned in the pocket, the right wrist would have to
        // turn round it, past what wrists do).
        low.aim = {0, -0.574f, -0.819f};
        low.pocket = {-0.03f, -0.14f, -0.17f};
        low.cheek = false;
        low.wrist_easy = 60;               // (carried a long time: the wrists no more strained than aiming)
        low.turn_as_aim = true;            // (bladed as he aims: raising it is the arms alone)
        low.pose = dw::Pose::Idle;          // carried like this while he stands, walks and runs
        if (const char* e = std::getenv("DW_870_LOW"))   // (trying others: aim xyz, pocket xyz)
            std::sscanf(e, "%f,%f,%f,%f,%f,%f", &low.aim.x, &low.aim.y, &low.aim.z, &low.pocket.x, &low.pocket.y, &low.pocket.z);
        reload.aim = {0, 0.2f, -0.98f};   // loading: under the armpit, muzzle up a little, left hand at the port
        reload.pocket = {0.0f, -0.2f, 0.02f};
        reload.left = {0, -0.2447f, -0.0068f};
        reload.cheek = false;
        if (const char* e = std::getenv("DW_870_RELOAD"))   // (trying others: aim xyz, pocket xyz)
            std::sscanf(e, "%f,%f,%f,%f,%f,%f", &reload.aim.x, &reload.aim.y, &reload.aim.z, &reload.pocket.x, &reload.pocket.y, &reload.pocket.z);
        reload.pose = dw::Pose::Reload;
        const char* only = std::getenv("DW_FIT_ONLY");   // (aim, low or reload: just that one)
        auto want = [only](const char* id) { return !only || std::string(only) == id; };
        if (want("aim")) TraceLog(LOG_INFO, "FIT aim %s", c.fit_shotgun(aim).c_str());
        if (want("low")) TraceLog(LOG_INFO, "FIT low ready %s", c.fit_shotgun(low).c_str());
        if (want("reload")) TraceLog(LOG_INFO, "FIT reload %s", c.fit_shotgun(reload).c_str());
        c.unload();
    } else if (!still.empty()) {   // the survivor standing in a room: --still x,z,yaw out.png [--shot id]
        float x = 0, z = 0, yaw = 0;
        if (std::sscanf(still.c_str(), "%f,%f,%f", &x, &z, &yaw) == 3) {
            game.pose_still(x, z, yaw, shot);
            for (int warm = 0; warm < 2; ++warm) {
                game.render();
                BeginDrawing();
                game.present();
                if (warm == 1) {
                    rlDrawRenderBatchActive();
                    Image img = LoadImageFromScreen();
                    ExportImage(img, still_png.c_str());
                    UnloadImage(img);
                }
                EndDrawing();
            }
        } else {
            TraceLog(LOG_ERROR, "bad --still spec: %s (want x,z,yaw)", still.c_str());
        }
    } else if (!view.empty()) {
        if (!game.studio_view(view, view_png)) TraceLog(LOG_ERROR, "bad --view spec: %s", view.c_str());
    } else if (!sheet.empty()) {
        game.model_sheet(sheet, only);
    } else if (!capture.empty()) {
        for (int i = 0; i < game.capture_count(); ++i) {
            std::string name = game.stage(i);
            for (int warm = 0; warm < 2; ++warm) {   // first frame after a cut can be stale on some drivers
                game.render();
                BeginDrawing();
                game.present();
                if (warm == 1) {
                    rlDrawRenderBatchActive();   // text and overlays are batched: draw them before reading the screen
                    Image img = LoadImageFromScreen();
                    ExportImage(img, (capture + "/" + name + ".png").c_str());
                    UnloadImage(img);
                }
                EndDrawing();
            }
            TraceLog(LOG_INFO, "captured %s", name.c_str());
        }
    } else {
        while (!WindowShouldClose() && !game.quit_requested()) {
            float dt = std::min(GetFrameTime(), 1.0f / 20.0f);
            worst = std::max(worst, double(GetFrameTime()) * 1000.0);
            game.update(dt);
            game.render();
            BeginDrawing();
            game.present();
            EndDrawing();
            if (max_frames > 0 && ++frames >= max_frames) break;
        }
    }
    tel.end("clean", GetTime() - start, frames, worst);
    game.shutdown();
    CloseWindow();
    return 0;
}
