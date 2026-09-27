# damned_waters/tools/audio/synth_sfx.py
# Purpose: synthesize every placeholder sound the demo needs (footsteps, pistol,
# doors, the Drowned, ambience beds) into game/assets/audio/*.wav, plus Godot
# .import files (PCM = zero decode cost; ambience flagged to loop).
# Replace any file with a real recording of the same name and nothing else changes.
#   python3 tools/audio/synth_sfx.py        (needs numpy + scipy)
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 44100
OUT = Path(__file__).resolve().parents[2] / "game" / "assets" / "audio"
rng = np.random.default_rng(1996)


def t(sec):
    return np.arange(round(sec * SR)) / SR


def noise(sec):
    return rng.standard_normal(round(sec * SR))


def env(n, attack, decay):
    """Attack/exponential-decay envelope, times in seconds."""
    x = np.arange(n) / SR
    a = np.clip(x / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(x - attack, 0) / max(decay, 1e-4))


def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def tail(x, sec, decay, lo=200, hi=3000, mix=0.25):
    """Cheap room tail: filtered noise convolved in, like a small hall."""
    ir = bp(noise(sec), lo, hi) * env(round(sec * SR), 0.002, decay)
    wet = signal.fftconvolve(x, ir)[: len(x) + len(ir)] * mix / max(1e-9, np.abs(ir).sum() ** 0.5)
    y = np.zeros(len(wet))
    y[: len(x)] += x
    return y + wet


def pad(x, sec):
    return np.concatenate([x, np.zeros(round(sec * SR))])


def at(total_sec, events):
    """Place (time, clip) events on a timeline."""
    y = np.zeros(round(total_sec * SR))
    for when, clip in events:
        i = int(when * SR)
        n = min(len(clip), len(y) - i)
        if n > 0:
            y[i:i + n] += clip[:n]
    return y


def loopable(x, fade_sec=1.5):
    """Crossfade the tail into the head so the loop point is inaudible."""
    f = int(fade_sec * SR)
    body, over = x[:-f].copy(), x[-f:]
    ramp = np.linspace(0, 1, f)
    body[:f] = body[:f] * ramp + over * (1 - ramp)
    return body


def moan(sec, f0, f1, vib=5.0):
    """Guttural voice: vibrato sawtooth through two formant bands."""
    tt = t(sec)
    f = np.linspace(f0, f1, len(tt)) * (1 + 0.03 * np.sin(2 * np.pi * vib * tt))
    saw = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR)
    v = bp(saw, 250, 700) * 1.0 + bp(saw, 900, 1400) * 0.5 + bp(noise(sec), 300, 1200) * 0.3
    return v * env(len(tt), 0.08, sec * 0.5)


def bubbles(sec, rate):
    ev = []
    for _ in range(int(sec * rate)):
        d = rng.uniform(0.02, 0.07)
        f = rng.uniform(250, 700)
        tt = t(d)
        ev.append((rng.uniform(0, sec - d), np.sin(2 * np.pi * np.cumsum(np.linspace(f, f * 1.8, len(tt))) / SR) * env(len(tt), 0.003, d / 3)))
    return at(sec, ev)


def build() -> dict[str, tuple[np.ndarray, bool]]:
    s: dict[str, tuple[np.ndarray, bool]] = {}
    # Footsteps: hard marble click, hollow wood thump, wading slosh.
    s["step_marble"] = (tail(hp(noise(0.05), 1500) * env(2205, 0.001, 0.008) + bp(noise(0.05), 2500, 6000) * env(2205, 0.001, 0.02) * 0.4, 0.5, 0.18), False)
    s["step_wood"] = (tail(bp(noise(0.12), 80, 400) * env(5292, 0.002, 0.035) * 2 + bp(noise(0.12), 600, 2000) * env(5292, 0.001, 0.015) * 0.5, 0.35, 0.1), False)
    s["step_water"] = (lp(noise(0.35), 1800) * env(15435, 0.03, 0.09) + bubbles(0.35, 20) * 0.3, False)
    # Pistol: crack + body + low thump + hall.
    crack = hp(noise(0.02), 2000) * env(882, 0.0005, 0.004) * 3
    body = bp(noise(0.4), 150, 3000) * env(17640, 0.001, 0.06) * 1.5
    thump = np.sin(2 * np.pi * 55 * t(0.25)) * env(11025, 0.001, 0.05) * 1.2
    s["gunshot"] = (tail(at(0.4, [(0, crack), (0, body), (0, thump)]), 1.2, 0.35, 150, 2500, 0.5), False)
    click = bp(noise(0.02), 2000, 7000) * env(882, 0.0005, 0.004)
    s["dry_fire"] = (pad(click, 0.1), False)
    s["reload"] = (at(0.9, [(0.0, click * 0.8), (0.35, bp(noise(0.03), 800, 3000) * env(1323, 0.001, 0.01)), (0.7, click), (0.74, click * 0.7)]), False)
    # Doors.
    tt = t(0.9)
    creak_f = 180 + 120 * np.sin(2 * np.pi * 1.3 * tt) + rng.standard_normal(len(tt)).cumsum() * 0.02
    creak = bp(signal.sawtooth(2 * np.pi * np.cumsum(creak_f) / SR) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 7 * tt))), 400, 2500)
    s["door_open"] = (tail(at(1.4, [(0, creak * env(len(tt), 0.1, 0.5) * 0.6), (1.0, bp(noise(0.2), 60, 300) * env(8820, 0.002, 0.05) * 2)]), 0.8, 0.3), False)
    s["door_locked"] = (at(0.6, [(k * 0.09, bp(noise(0.04), 500, 3000) * env(1764, 0.001, 0.01)) for k in range(5)]), False)
    bang = lp(noise(0.6), 250) * env(26460, 0.003, 0.15) * 3 + bp(noise(0.6), 800, 3000) * env(26460, 0.001, 0.05)
    s["door_bang"] = (tail(pad(bang, 0.3), 1.5, 0.4, 80, 800, 0.6), False)
    # UI + pickups + save.
    chime = sum(np.sin(2 * np.pi * f * t(1.2)) * env(round(1.2 * SR), 0.005, d) for f, d in ((880, 0.4), (1320, 0.3), (1760, 0.2)))
    s["pickup"] = (chime * 0.25, False)
    s["ui_move"] = (np.sin(2 * np.pi * 1200 * t(0.05)) * env(2205, 0.001, 0.01) * 0.3, False)
    s["ui_confirm"] = (np.sin(2 * np.pi * 660 * t(0.25)) * env(11025, 0.003, 0.08) * 0.35, False)
    keys = [(i * 0.11 + rng.uniform(0, 0.03), bp(noise(0.03), 1500, 5000) * env(1323, 0.0005, 0.006)) for i in range(7)]
    bell = np.sin(2 * np.pi * 2100 * t(1.0)) * env(SR, 0.002, 0.3) * 0.3
    s["save"] = (at(2.0, keys + [(0.95, bell)]), False)
    # People and the Drowned.
    s["player_hurt"] = (moan(0.35, 180, 120, 8) * 0.8 + lp(noise(0.35), 500) * env(15435, 0.005, 0.05) * 0.5, False)
    s["enemy_gurgle"] = (moan(1.6, 70, 60, 3) * 0.6 + bubbles(1.6, 18) * 0.5, False)
    s["enemy_alert"] = (moan(1.1, 85, 110, 4) + bubbles(1.1, 10) * 0.3, False)
    s["enemy_windup"] = (moan(0.8, 90, 160, 9) * 1.1 + bubbles(0.8, 25) * 0.4, False)
    s["enemy_hit"] = (lp(noise(0.2), 900) * env(8820, 0.001, 0.04) * 1.5 + bubbles(0.2, 30) * 0.3, False)
    s["enemy_death"] = (moan(2.0, 110, 45, 3) * 1.0 + at(2.0, [(1.2, lp(noise(0.8), 600) * env(35280, 0.01, 0.2))]), False)
    s["splash"] = (lp(noise(1.2), 2500) * env(52920, 0.02, 0.3) + bubbles(1.2, 30) * 0.5, False)
    # Ambience beds (seamless loops).
    L = 24.0
    tt = t(L + 1.5)
    wind = bp(noise(L + 1.5), 60, 400) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt)) * 0.35
    rain = hp(noise(L + 1.5), 3000) * 0.025
    creaks = at(L + 1.5, [(rng.uniform(1, L - 2), bp(signal.sawtooth(2 * np.pi * np.cumsum(90 + 40 * rng.standard_normal(26460).cumsum() * 0.001) / SR), 300, 1500) * env(26460, 0.2, 0.25) * 0.12) for _ in range(4)])
    s["amb_house"] = (loopable(wind + rain + creaks), True)
    drips = at(L + 1.5, [(rng.uniform(0, L), tail(np.sin(2 * np.pi * rng.uniform(900, 1600) * t(0.08)) * env(3528, 0.001, 0.015), 0.6, 0.25, 300, 4000, 0.8) * 0.4) for _ in range(28)])
    lap = lp(noise(L + 1.5), 350) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * tt)) * 0.5
    rumble = lp(noise(L + 1.5), 60) * 0.6
    s["amb_cellar"] = (loopable(drips + lap + rumble), True)
    drone = sum(lp(signal.sawtooth(2 * np.pi * f * tt), 500) * a for f, a in ((55, 0.3), (55.4, 0.3), (82.5, 0.15), (110.7, 0.08)))
    s["title_drone"] = (loopable(drone * (0.7 + 0.3 * np.sin(2 * np.pi * 0.05 * tt)) + bp(noise(L + 1.5), 200, 900) * 0.04), True)
    # ── combat set ──
    boom = lp(noise(0.9), 1200) * env(round(0.9 * SR), 0.001, 0.12) * 2.5
    s["shotgun"] = (tail(at(0.9, [(0, crack * 1.5), (0, boom), (0, np.sin(2 * np.pi * 42 * t(0.4)) * env(round(0.4 * SR), 0.001, 0.09) * 2)]), 1.6, 0.5, 100, 2200, 0.6), False)
    shell = at(0.25, [(0.0, bp(noise(0.03), 700, 2500) * env(1323, 0.001, 0.01)), (0.12, click)])
    s["shotgun_reload"] = (at(2.0, [(0.0, click * 1.2), (0.5, shell), (1.0, shell), (1.6, bp(noise(0.08), 300, 2000) * env(3528, 0.001, 0.02) * 2)]), False)
    s["weapon_switch"] = (at(0.4, [(0.0, bp(noise(0.08), 200, 1500) * env(3528, 0.01, 0.03)), (0.2, click * 0.6)]), False)
    s["kick"] = (tail(lp(noise(0.25), 400) * env(round(0.25 * SR), 0.001, 0.03) * 3 + bp(noise(0.25), 1000, 3000) * env(round(0.25 * SR), 0.001, 0.01), 0.5, 0.15), False)
    s["dodge"] = (bp(noise(0.35), 300, 2500) * env(round(0.35 * SR), 0.08, 0.08) * np.linspace(1.5, 0.3, round(0.35 * SR)), False)
    sweep = np.sin(2 * np.pi * np.cumsum(np.linspace(900, 120, round(1.2 * SR))) / SR) * env(round(1.2 * SR), 0.01, 0.5)
    s["perfect_dodge"] = (tail(sweep * 0.5 + lp(noise(1.2), 300) * env(round(1.2 * SR), 0.2, 0.4) * 0.6, 1.5, 0.6, 200, 2000, 0.7), False)
    s["crawler_skitter"] = (at(0.3, [(k * 0.04 + rng.uniform(0, 0.02), hp(noise(0.015), 2500) * env(662, 0.0005, 0.003) * 0.7) for k in range(6)]), False)
    tt2 = t(0.6)
    screech = bp(signal.sawtooth(2 * np.pi * np.cumsum(np.linspace(900, 1500, len(tt2)) * (1 + 0.08 * np.sin(2 * np.pi * 31 * tt2))) / SR), 1200, 5000)
    s["crawler_screech"] = (screech * env(len(tt2), 0.02, 0.2) + hp(noise(0.6), 3000) * env(len(tt2), 0.01, 0.1) * 0.3, False)
    s["boss_roar"] = (tail(moan(2.4, 55, 38, 2) * 1.2 + moan(2.4, 82, 60, 3) * 0.8 + moan(2.4, 130, 95, 5) * 0.4 + lp(noise(2.4), 200) * env(round(2.4 * SR), 0.3, 1.0), 2.0, 0.8, 60, 900, 0.7), False)
    s["boss_slam"] = (tail(lp(noise(1.0), 180) * env(SR, 0.002, 0.2) * 3 + np.sin(2 * np.pi * 34 * t(1.0)) * env(SR, 0.002, 0.25) * 2 + bubbles(1.0, 30) * 0.4, 2.0, 0.6, 60, 700, 0.6), False)
    s["boss_emerge"] = (tail(lp(noise(3.0), 1500) * env(3 * SR, 0.5, 1.2) * 1.5 + bubbles(3.0, 60) * 0.8 + moan(3.0, 45, 60, 1) * 0.6, 2.0, 0.8, 80, 1500, 0.5), False)
    tt3 = t(L + 1.5)
    pulse = (np.sin(2 * np.pi * 1.6 * tt3) > 0.6).astype(float)
    thump = lp(pulse * np.sin(2 * np.pi * 50 * tt3), 150) * 0.9
    strings = sum(bp(signal.sawtooth(2 * np.pi * f * tt3), 150, 1800) * a for f, a in ((73.4, 0.25), (77.8, 0.2), (110.0, 0.12), (116.5, 0.1)))
    stabs = at(L + 1.5, [(b * 60 / 96 * 4, bp(noise(0.4), 400, 3000) * env(round(0.4 * SR), 0.001, 0.08) * 0.4) for b in range(int((L + 1.5) * 96 / 60 / 4))])
    s["boss_theme"] = (loopable(thump + strings * (0.7 + 0.3 * np.sin(2 * np.pi * 0.1 * tt3)) + stabs), True)
    return s


IMPORT = """[remap]

importer="wav"
type="AudioStreamWAV"

[deps]

source_file="res://assets/audio/{name}.wav"

[params]

force/8_bit=false
force/mono=false
force/max_rate=false
force/max_rate_hz=44100
edit/trim=false
edit/normalize=false
edit/loop_mode={loop}
edit/loop_begin=0
edit/loop_end=-1
compress/mode=0
"""


def write_wav(path: Path, x: np.ndarray, peak_db: float = -1.0) -> None:
    peak = np.max(np.abs(x)) or 1.0
    y = x / peak * (10 ** (peak_db / 20))
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    levels = {"boss_theme": -9.0, "crawler_skitter": -10.0, "dodge": -8.0, "amb_house": -14.0, "amb_cellar": -12.0, "title_drone": -10.0, "step_marble": -8.0,
              "step_wood": -6.0, "step_water": -8.0, "ui_move": -12.0}
    for name, (x, loop) in build().items():
        write_wav(OUT / f"{name}.wav", x, levels.get(name, -1.0))
        (OUT / f"{name}.wav.import").write_text(IMPORT.format(name=name, loop=2 if loop else 0))
        print(f"[sfx] {name:14s} {len(x) / SR:5.2f}s {'loop' if loop else ''}")


if __name__ == "__main__":
    main()
