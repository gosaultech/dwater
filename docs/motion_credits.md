<!-- damned_waters/docs/motion_credits.md -->
<!-- Purpose: the motion capture the characters move by, and its credit (CC BY 4.0 asks for it). -->

# Motion capture

The survivor's sneak, walk, run and standing idle, and the Drowned's shambles (each of the three
walks its own way), are motion-captured gait cycles from:

**100STYLE** by Ian Mason, Sebastian Starke and Taku Komura (2022), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Dataset: <https://zenodo.org/records/8127870>.
Paper: Mason, Starke, Komura. "Real-Time Style Modelling of Human Locomotion via Feature-Wise
Transformations and Local Motion Phases." *Proceedings of the ACM on Computer Graphics and Interactive
Techniques* 5(1), 2022.

| In the game | Style | Take | What was changed |
|---|---|---|---|
| sneak (0.8 m/s) | Swat | forward walk | 8 cycles near 0.85 m/s averaged, mirrored for symmetry, the lean and gaze set |
| walk (1.9 m/s) | Rushed | forward walk | 4 cycles near 2.0 m/s averaged, mirrored, the lean and gaze set |
| run (3.8 m/s) | Rushed | forward run | 5 cycles near 2.6 m/s averaged, mirrored, the lean and gaze set; stretched to his speed |
| standing | Neutral | idle | 6 s looped, the lean and gaze set |
| a Drowned dragging a leg (0.85 m/s) | DragRightLeg | forward walk | 6 cycles near 0.8 m/s averaged, kept lopsided, hunched |
| a Drowned staggering | Drunk | forward walk | 6 cycles near 0.85 m/s averaged, kept lopsided, hunched |
| a Drowned lurching | BentForward | forward walk | 6 cycles near 0.85 m/s averaged, hunched |

Only the legs, hips, spine, neck and head are taken from it (for the Drowned, the legs, hips and
spine); his arms keep the game's own gun-carrying poses, and the Drowned keep their reaching arms,
lolling heads and twitches. `tools/anim/bake_mocap.py` does the baking (the dataset itself is not in the repo: download
`100STYLE.zip` from the record above and pass its folder with `--src`).
