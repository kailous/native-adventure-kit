---
name: native-mod-build
description: Assemble the pinned Native Adventure Kit Mod from upstream sources, verify patches, and guide a user-owned macOS game build. Use for this kit's preparation, reconstruction, upgrades or build failures.
---

Read [the kit entry](../../README.md), [assembly steps](../../docs/bootstrap.md) and [risk notice](../../使用协议.md). This skill also works as a readable guide in non-Codex agents; do not assume the host discovers or installs it automatically.

- Prepare with `python3 scripts/prepare_native.py --work <new-external-directory>`, from the kit root. The script fetches the exact `upstream.lock.json` commit and applies checked text patches. Preparation is not a game build.
- An explicitly supplied `--upstream-cache` is read-only. Never use its uncommitted files, reset it, update its refs, or rely on the original maintainer's machine paths.
- Existing output is verified with `--verify`; choose a new directory for another assembly. Do not overwrite, delete, or silently repair user work.
- Stop on patch, source hash, unsafe path or permission mismatches. Do not invent a merge, bypass validation or follow latest main. An upstream upgrade requires maintainer-reviewed patches and updated lock evidence.
- Default loading artwork is neutral generated placeholder content. `--loading-assets` accepts user-authorized external assets only; do not download game images or include them in patches.
- For an actual build, use the assembled `MacNativeGames/build_app.py`; inspect its help and the assembly guide. Obtain input paths from the user without printing key values. Game inputs, build caches and App output stay external.
- Explain filesystem, remote-access and game-state risks before relevant actions. Do not fabricate acknowledgements; these workflow measures do not restrict MIT rights.
- Game/GPU acceptance is a separate authorized action: follow the assembled source's GameSlot and user-takeover rules; use isolated saves and the specified window configuration. Do not start a game merely to validate preparation.

- Every upstream sync, branch merge, cherry-pick, manual port or conflict resolution requires a pre-merge baseline of every maintained feature and post-merge checks of entry points, implementation, protocol, resources, persisted settings and actual artifacts, including unchanged features and cross-repository links. Read [the mandatory merge gate](../../docs/upstream-merge-policy.md).
- If any maintained feature regresses or any required check is pending, do not mark the merge complete, merge stable main, publish a Release or replace an existing delivery. Candidate branches and private drafts may retain explicit blockers. Do not hide failures by deleting entry points/tests, resetting configuration, disabling defaults, lowering checks or changing a baseline. Missing hardware or an occupied game does not waive the gate; preserve GameSlot, isolated saves and user takeover.

Report the pinned commit, workspace, actual checks and remaining limitations. Separate assembly, host tests, App build and in-game results. Upstream code, patch context, assets and binaries retain their respective rights; downloading them separately is not legal clearance.
