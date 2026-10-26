---
title: Camera Monitor - Plan
type: feat
date: 2026-10-26
topic: camera-monitor
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-brainstorm
execution: code
---

# Camera Monitor - Plan

## Goal Capsule

- **Objective:** Artists have a view-only camera monitor in Maya that shows persp with shading and lighting of its own, so the panel, its menu entry and its settings exist before the Active camera concept does and later work can use those settings for renders.
- **Means:** A Maya workspace panel holding a model panel, opened from a checkable Camera menu on the Mise Stage shell (Key Decisions).
- **Product authority:** The Product Contract wins on behavior; a Key Decision wins on mechanism. This plan covers the monitor panel, its menu entry and its interim settings storage only. The Active camera concept, the render link, a layout-pane version, embedding in the shell window and the permanent home for settings (#20, #21) are not active scope.
- **Execution profile:** Code, on a branch named `22-camera-monitor`, landing as a PR containing `Closes #22`. Start with a hands-on Maya check of the unverified assumptions under Dependencies / Assumptions. Maya behavior is checked by hand against AE1 to AE6 and the PR carries that checklist; CI covers only the pure Python pieces.
- **Stop conditions:** Stop and ask if Maya cannot lock out camera movement and selection (R7), hold the monitor to its role (R8), or show its standard panel menus (R5) in this panel.
- **Open blockers:** None.

---

## Product Contract

### Summary

A "Camera Monitor" panel for Maya 2026+. It floats or tabs beside the Attribute Editor or the Mise Stage panel, looks through persp, and is view-only. Its shading and lighting are its own, are changed through Maya's standard panel menus, and persist across restarts. A new Camera menu on the shell's menu bar has a checkable Camera Monitor item that opens and closes it.

### Problem Frame

Mise is moving toward one camera that the artist works through, and the shading and lighting of that view will eventually drive renders. Today the only way to see a camera is to switch a working viewport to it, which disturbs the stock persp, side and top views. A separate monitor keeps those views alone and gives the render-oriented display settings a home of their own.

The monitor ships first with persp alone, looking through it directly, so for now it is effectively a second persp view with independent shading and lighting. It becomes distinct from persp when the Active camera arrives. Building the panel, menu entry and settings first means that later change is a swap of the camera, not a new feature.

### Key Decisions

- **The monitor is its own Maya workspace panel, not part of the shell window.** Maya docks and restores it like any panel. Governs R1, R2. (session-settled: user-directed — chosen over embedding it in the shell body and over a pane in Maya's view layout: in Maya 2026 a model panel built in one place and moved into a Qt window stayed blank, while a workspace panel docked and floated correctly.)
- **The monitor looks through the camera directly.** Mise adds no camera or constraint to the scene. Governs R4. (session-settled: user-directed — chosen over a follower camera: the follower gives the monitor its own lens but puts extra nodes in every scene.)
- **Shading and lighting are changed through Maya's own panel menus.** Governs R5. (session-settled: user-directed — chosen over no controls and over Mise-built controls: familiar controls now, Mise's own settings UI later.)
- **The monitor is view-only at first.** An option to allow tumble and dolly may come later. Governs R7. (session-settled: user-directed — chosen over a navigable monitor.)
- **The monitor stays a camera monitor showing persp.** Maya's camera-changing, panel-swapping and tear-off items must not change it. Governs R8. (session-settled: user-directed — chosen over letting the artist point it at any camera.)
- **The Camera menu item is a check mark for "monitor is open".** Governs R9, R10, R11. (session-settled: user-approved — proposed with the check state following the panel's real state.)
- **Display settings persist, stored in Maya's own preferences for now.** The permanent home is decided with the user settings system (#20) and the scene settings system (#21), and the stored values then move there. Governs R6. (session-settled: user-approved — chosen over resetting to the default on every rebuild, which silently loses the look set before a restart, and over storing them in Mise's per-show settings, which are for values shared across a production.)
- **The monitor first opens floating, like the shell, and File ▸ Exit on the shell closes only the shell.** Governs R1, R3. (session-settled: user-approved — proposed for consistency with the shell.)

### Requirements

**Panel**

- R1. The camera monitor is a panel titled "Camera Monitor" that first opens floating, and that the artist can float, or dock as a tab beside the Attribute Editor, the Mise Stage panel or any other Maya panel.
- R2. Its dock position, size and floating state persist across Maya restarts. A monitor left open at exit is rebuilt in place; one the artist closed stays closed.
- R3. File ▸ Exit on the shell closes only the shell; an open monitor stays open.

**Camera and display**

- R4. The monitor shows the view through persp, and Mise adds no camera, constraint or other node to the scene to do it.
- R5. The monitor's shading and lighting settings belong to it alone: changing them does not change any other view, and changing another view does not change them. It opens with Maya's default new-panel look (smooth shaded, default lighting), and the artist changes it with Maya's standard panel menus.
- R6. The shading and lighting the artist sets persist across closing and reopening the monitor and across Maya restarts, stored in Maya's own preferences until #20 and #21 provide a permanent home.
- R7. The monitor is view-only: the artist cannot move a camera through it by mouse or by shortcut (for example F to frame the selection), and clicking in it selects nothing and shows no manipulators. Selection made elsewhere still shows highlighted in it.
- R8. Maya's panel menus and controls cannot make the monitor show a different camera, turn it into a different panel, or create a copy of it.

**Camera menu**

- R9. The shell's menu bar has a Camera menu containing a checkable "Camera Monitor" item.
- R10. Checking the item opens the monitor, or raises it if it already exists; it never creates a second one. Unchecking closes it.
- R11. The item's check state matches whether the monitor is open at all times, including after the artist closes the monitor with its own close button and after a restart restores it.

**Structure**

- R12. All Maya calls, including panel creation, camera binding, navigation lock and preference storage, live in `python/mise_stage/dcc/` in a new camera-monitor module. The Camera menu, its check state and its model, view and controller live in `python/mise_stage/ui/shell/`. There is no `backends/` part. Tests go in `tests/test_camera_monitor*.py`, with the shell menu covered by the existing shell tests.
- R13. A technical doc, `docs/technical/camera-monitor.md`, is added and linked from `docs/technical/README.md`. It covers opening the monitor, the `sys.path` requirement for restore, where the display settings are stored for now, and the manual steps for reloading modules during development.

### Acceptance Examples

The open-and-close behavior is a single toggle, so there is no separate flow section; these examples cover it.

- AE1. **Covers R1, R2.** Given the monitor opens for the first time, it floats. When the artist drags it onto the Attribute Editor tab bar, it becomes a tab there; after restarting Maya it appears in the same tab group.
- AE2. **Covers R9, R10, R11.** Given the monitor is closed and the Camera Monitor item is unchecked, when the artist checks it, the monitor opens and the item is checked. When the artist then closes the monitor with its own close button, the item becomes unchecked.
- AE3. **Covers R4, R5.** Given the monitor is open next to the persp view, when the artist sets the monitor to wireframe with all lights, the persp view's shading and lighting do not change.
- AE4. **Covers R7, R8.** When the artist drags in the monitor with the tumble or dolly tool, presses F, or clicks an object, nothing moves, nothing is selected and no manipulator appears. No item in the monitor's panel menus can make it show another camera, become another panel or make a copy.
- AE5. **Covers R6.** Given the artist set the monitor to wireframe, when they close and reopen it, or restart Maya, it shows wireframe.
- AE6. **Covers R3.** Given the monitor is open, when the artist chooses File ▸ Exit on the shell, the shell closes and the monitor stays open.

### Scope Boundaries

**Deferred for later**

- The Active camera concept, and the monitor following it instead of persp.
- Using the monitor's shading and lighting for renders.
- The permanent home for the stored display settings, and moving them there: user settings (#20) and scene settings (#21).
- Showing the monitor as a pane in Maya's view layout alongside persp, side and top.
- An option that allows tumble and dolly in the monitor.
- Mise-built shading and lighting controls.
- Embedding the monitor inside the Mise Stage shell window. Not possible with the approaches tried in Maya 2026.
- Opening the monitor with the shell closed. The Camera menu lives on the shell, so the monitor is opened from there.

### Dependencies / Assumptions

- **Restore at startup** works like the shell's (R2): it needs `python/` on Maya's `sys.path`, as documented in `docs/technical/shell.md`.
- **Unverified in Maya:** that camera movement, shortcuts and selection can be locked out cleanly (R7), that camera-changing, panel-swapping and tear-off items can be hidden or reversed (R8), that Maya's standard panel menus appear in a model panel inside a workspace panel (R5), that the menu check can follow the panel when it is closed with its own close button (R11), and that the stored settings can be reapplied to a rebuilt panel (R6).
- **Verified in a throwaway spike in Maya 2026:** a model panel inside a workspace panel floats and docks as a tab; its shading and lighting stay independent of the stock persp panel; a panel looking through persp stays in step with the other persp view, updating when a drag ends.
- **Follow-up work:** #20 (user settings system) and #21 (scene settings system).

### Outstanding Questions

**Deferred to Planning**

- How camera movement, shortcuts and selection are locked out (R7), and how the monitor is held to its role (R8): hiding menus versus putting the camera or panel back when it changes.
- How the check state follows the panel's real state (R11).
- How the display settings are stored in Maya's preferences and reapplied to a rebuilt panel (R6).

### Sources / Research

- `docs/technical/shell.md`: how the shell panel is built, restored and documented.
- `python/mise_stage/dcc/workspace.py`: the existing panel create, raise, close and restore-script helpers.
- `python/mise_stage/ui/shell/view.py`: the shell's menu bar today (File ▸ Exit only).
- A throwaway Maya 2026 spike, kept locally and not committed under `.context/compound-engineering/ce-prototype/2026-10-26-camera-monitor-hosting/`; its findings are carried in the Key Decisions above.
