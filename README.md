# GitHub Profile README — CLI terminal effect

A self-hosted animated SVG terminal for your profile README: colored `BUILD` /
`STATS` / `MODULE` labels, `[timestamp]` lines, a real terminal window frame,
and commands that type out character by character before their output fades in.

**What changed from the first version:**
- It no longer loops. Once the last command's output has printed, a fresh
  `➜  ~` prompt appears and the cursor just blinks there forever.
- Everything you'd want to edit — the commands, the output lines, every
  color, the font, and the typing speed — now lives in one file,
  `terminal.config.json`. You never touch the SVG by hand again.
- A GitHub Action watches that file. Edit it, push, and the Action
  regenerates `assets/terminal.svg` and commits it for you. Your README
  doesn't change at all — it just keeps pointing at `assets/terminal.svg`,
  and that file's contents update.

## Setup

1. Copy these into your `<your-username>/<your-username>` profile repo,
   keeping the folder structure:
   ```
   assets/terminal.svg
   scripts/generate_terminal_svg.py
   terminal.config.json
   .github/workflows/generate-terminal.yml
   ```
2. In `README.md`, embed the SVG as an image (not inline `<svg>` — GitHub
   strips animations from inline SVG in markdown, but a referenced image
   keeps them):
   ```html
   <div align="center">
     <img src="./assets/terminal.svg" alt="terminal" width="100%" />
   </div>
   ```
3. Push. GitHub Actions needs permission to commit back to the repo:
   in **Settings → Actions → General → Workflow permissions**, select
   **"Read and write permissions"** and save. (One-time setup.)
4. Push again (or re-run the workflow from the Actions tab) and confirm
   `assets/terminal.svg` gets committed by the `github-actions[bot]`.

## How to edit it

Everything is controlled by **`terminal.config.json`**. Edit that file,
commit, and push — the Action rebuilds `assets/terminal.svg` for you within
a minute or two. No local tools required.

### Change what the terminal shows

Each entry in `"commands"` is one typed command plus its output:

```json
{
  "prompt": "cat thesis.md",
  "output": [
    { "type": "badge", "label": "MODULE", "text": "" },
    { "type": "path", "text": "../thesis/A-RICD.md" },
    { "type": "line", "timestamp": "00:00:12", "text": "Some output line" }
  ]
}
```

Output line `"type"` options:
| type    | fields                          | renders as                                  |
|---------|----------------------------------|----------------------------------------------|
| `badge` | `label`, `text`                  | colored tag (e.g. `BUILD`) + description      |
| `path`  | `text`                            | a file path, in the path color                |
| `line`  | `timestamp` (optional), `text`   | `[00:00:12]  text`, or just `text` if no timestamp |
| `text`  | `text`, `color` (optional)       | a plain line in the default output color      |

Add, remove, or reorder commands and output lines freely — the SVG's height
and every timing offset is recalculated automatically each time it's
regenerated.

### Change the colors

Everything lives under `"colors"` in the config:

```json
"colors": {
  "background": "#0d0e12",
  "command_text": "#8a8a8a",
  "output_text": "#c9c9c9",
  "prompt_symbol": "#7ec699",
  "timestamp": "#6b6f76",
  "path_text": "#6fb3d2",
  "badges": { "BUILD": "#27c93f", "STATS": "#5c9dd4", "MODULE": "#d7ba7d" }
}
```

Add your own badge labels here too — any `label` you use in a `commands`
entry that has a matching key in `"colors.badges"` will use that color.

A note on contrast: `command_text` is set to `#8a8a8a` by default because
the raw `#454545` from the original spec is quite hard to read against the
near-black background — that's just contrast math, not a bug. Set it back
to `#454545` if you want it darker; nothing stops you.

### Change speed and pacing

```json
"timing": {
  "typing_speed_ms": 45,
  "enter_pause_ms": 250,
  "line_reveal_delay_ms": 350,
  "command_gap_ms": 700
}
```

- `typing_speed_ms` — delay between each typed character.
- `enter_pause_ms` — pause after a command finishes typing, before its output appears.
- `line_reveal_delay_ms` — delay between each output line fading in.
- `command_gap_ms` — pause after a command's output finishes, before the next command starts typing.

### Turn the idle cursor off

`"show_idle_cursor_prompt": true` adds a final empty `➜  ~` prompt with a
blinking cursor after the last command — that's the "done" state. Set it to
`false` if you'd rather the cursor just rest at the end of the last output
line instead.

## Regenerating locally (optional)

You don't need this — the Action does it on push — but if you want to
preview a change before committing:

```bash
python3 scripts/generate_terminal_svg.py terminal.config.json assets/terminal.svg
```

No dependencies beyond the Python standard library.

## Things to know

- **Font:** SVGs embedded via `<img>` can't load external `@font-face`
  files — browsers block that for security — so it falls back to
  `JetBrains Mono` / `Fira Code` / system monospace. If you have a
  `.ttf`/`.woff2` you have the right to redistribute, it can be base64-embedded
  directly in the generator so it renders correctly everywhere; that's a
  separate follow-up if you want it.
- **Timing math:** the generator computes every character's and every
  line's reveal time from the `timing` settings, so edits to `commands` or
  `timing` never require touching timestamps by hand.
