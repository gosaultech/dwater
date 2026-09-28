// damned_waters/engine/src/main.cpp
// Purpose: entry point. Normal play, or --capture DIR to stage fixed setups
// and save screenshots (used to review the look without playing).
//   ./damned_waters                 play (WASD, Shift run, Q quick turn, RMB/K aim, T tank/modern, F3 debug)
//   ./damned_waters --capture out   stage + screenshot every setup, then exit
//   ./damned_waters --sheet out     studio turnaround of the cast (model review), then exit
//                                   (--only pieter,survivor: just those subjects)
//   ./damned_waters --view survivor,25,10,0.6,0,0.9,30 out.png   one full-resolution studio shot
//                                   (who, orbit, elevation, distance, target x, target height, fov), then exit;
//                                   who: survivor | drowned[N] [@head | @chest | @pelvis]
//   ./damned_waters --frames 600    auto-exit (smoke tests)
#include <raylib.h>
#include <algorithm>
#include <string>

#include "dw/telemetry.hpp"
#include "game.hpp"

int main(int argc, char** argv) {
    std::string capture, sheet, only, view, view_png, room = "gang";
    long max_frames = -1;
    for (int i = 1; i + 1 < argc; ++i) {
        std::string a = argv[i];
        if (a == "--capture") capture = argv[++i];
        else if (a == "--sheet") sheet = argv[++i];
        else if (a == "--only") only = argv[++i];
        else if (a == "--view" && i + 2 < argc) { view = argv[++i]; view_png = argv[++i]; }
        else if (a == "--room") room = argv[++i];
        else if (a == "--frames") max_frames = std::stol(argv[++i]);
    }
    SetConfigFlags(FLAG_VSYNC_HINT | FLAG_WINDOW_RESIZABLE);
    InitWindow(dw::Game::W, dw::Game::H, "Damned Waters");
    SetTargetFPS(60);
    dw::Telemetry tel(std::string(GetApplicationDirectory()) + "damned_waters.db");
    tel.begin(!view.empty() ? "view" : !sheet.empty() ? "sheet" : capture.empty() ? "play" : "capture", room);
    dw::Game game;
    if (!game.init(room)) {
        tel.end("init_failed", 0, 0, 0);
        CloseWindow();
        return 1;
    }
    double start = GetTime(), worst = 0;
    long frames = 0;
    if (!view.empty()) {
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
                    Image img = LoadImageFromScreen();
                    ExportImage(img, (capture + "/" + name + ".png").c_str());
                    UnloadImage(img);
                }
                EndDrawing();
            }
            TraceLog(LOG_INFO, "captured %s", name.c_str());
        }
    } else {
        while (!WindowShouldClose()) {
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
