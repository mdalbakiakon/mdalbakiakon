"""
Generates assets/terminal.svg from terminal.config.json.

No third-party dependencies.

Usage:
    python3 scripts/generate_terminal_svg.py [config_path] [output_path]

Defaults:
    config_path = terminal.config.json
    output_path = assets/terminal.svg
"""

import base64
import html
import json
import os
import sys


# ============================================================
# CONSTANTS
# ============================================================

CHAR_WIDTH_RATIO = 0.6

TOP_PAD = 56
HEADER_HEIGHT = 40
BOTTOM_PAD = 40

CURSOR_WIDTH_RATIO = 0.55
CURSOR_HEIGHT_RATIO = 1.15

GUTTER_SIDE_PAD = 10


# ============================================================
# HELPERS
# ============================================================

def esc(value):
    return html.escape(str(value), quote=True)


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_commands(commands):
    """
    Supports both the existing prompt/output schema and the compact
    nested command schema used for API-style terminal sequences.

    A nested object such as:
        {"command": "node", "console": [...], "output": [...], "json": {...}}

    becomes a normal terminal command so it gets its own prompt and
    participates in the same scrolling timeline.
    """

    normalized = []

    for raw_cmd in commands:
        prompt = str(
            raw_cmd.get(
                "prompt",
                raw_cmd.get("command", ""),
            )
        )

        base_output = []
        nested_commands = []

        for console_line in raw_cmd.get(
            "console",
            [],
        ):
            base_output.append(
                {
                    "type": "text",
                    "text": str(console_line),
                }
            )

        for item in raw_cmd.get("output", []):
            if (
                isinstance(item, dict)
                and item.get("command")
            ):
                nested = dict(item)
                nested_prompt = str(
                    nested.pop("command")
                )

                nested_output = []

                for console_line in nested.get(
                    "console",
                    [],
                ):
                    nested_output.append(
                        {
                            "type": "text",
                            "text": str(console_line),
                        }
                    )

                nested_output.extend(
                    nested.get("output", [])
                )

                if "json" in nested:
                    json_text = json.dumps(
                        nested["json"],
                        indent=2,
                        ensure_ascii=False,
                    )

                    nested_output.extend(
                        {
                            "type": "text",
                            "text": line,
                        }
                        for line in json_text.splitlines()
                    )

                nested_commands.append(
                    {
                        "prompt": nested_prompt,
                        "output": nested_output,
                        "api_delay": bool(
                            nested.get("api_delay", False)
                        ),
                    }
                )
            else:
                base_output.append(item)

        if "json" in raw_cmd:
            json_text = json.dumps(
                raw_cmd["json"],
                indent=2,
                ensure_ascii=False,
            )

            base_output.extend(
                {
                    "type": "text",
                    "text": line,
                }
                for line in json_text.splitlines()
            )

        normalized.append(
            {
                **raw_cmd,
                "prompt": prompt,
                "output": base_output,
            }
        )

        normalized.extend(nested_commands)

    return normalized


def load_font_base64(font_path):
    """
    Loads the custom WOFF2 font and returns base64 data.

    This embeds the font directly inside terminal.svg,
    so the SVG does not depend on the browser finding the
    font file separately.
    """

    if not font_path:
        return None

    if not os.path.exists(font_path):
        print(
            f"Warning: font file not found: {font_path}",
            file=sys.stderr,
        )
        return None

    with open(font_path, "rb") as f:
        data = f.read()

    return base64.b64encode(data).decode("ascii")


# ============================================================
# CURSOR
# ============================================================

class Cursor:
    """Collects cursor movement keyframes."""

    def __init__(self):
        self.moves = []

    def move_to(self, t, x, y):
        self.moves.append(
            (
                round(t, 3),
                round(x, 2),
                round(y, 2),
            )
        )

    def to_svg(self, color, width, height, radius=1):
        if not self.moves:
            return ""

        x0 = self.moves[0][1]
        y0 = self.moves[0][2]

        x_animates = "".join(
            f'<animate '
            f'attributeName="x" '
            f'to="{x}" '
            f'begin="{t}s" '
            f'dur="0.01s" '
            f'fill="freeze"/>'
            for t, x, y in self.moves
        )

        y_animates = "".join(
            f'<animate '
            f'attributeName="y" '
            f'to="{y}" '
            f'begin="{t}s" '
            f'dur="0.01s" '
            f'fill="freeze"/>'
            for t, x, y in self.moves
        )

        return (
            f'<rect '
            f'x="{x0}" '
            f'y="{y0}" '
            f'width="{width:.2f}" '
            f'height="{height:.2f}" '
            f'rx="{radius}" '
            f'fill="{color}">'

            f'<animate '
            f'attributeName="opacity" '
            f'values="1;1;0;0;1" '
            f'keyTimes="0;0.45;0.5;0.95;1" '
            f'dur="1.05s" '
            f'repeatCount="indefinite"/>'

            f'{x_animates}'
            f'{y_animates}'

            f'</rect>'
        )


# ============================================================
# ROW COUNT
# ============================================================

def count_rows(
    commands,
    command_gap_lines,
    show_idle_cursor,
):
    rows = 0

    for cmd in commands:
        # Prompt
        rows += 1

        # Output
        rows += len(
            cmd.get(
                "output",
                [],
            )
        )

        # Blank gap
        rows += command_gap_lines

    if show_idle_cursor:
        rows += 1

    return rows


# ============================================================
# SVG BUILDER
# ============================================================

def build_svg(cfg, font_data=None):
    # ========================================================
    # COLORS
    # ========================================================

    colors = cfg.get("colors", {})

    bg = colors.get(
        "background",
        "#0d0e12",
    )

    header_bg = colors.get(
        "header_bg",
        "#101217",
    )

    border = colors.get(
        "border",
        "#22252b",
    )

    dot_red = colors.get(
        "dot_red",
        "#ff5f56",
    )

    dot_yellow = colors.get(
        "dot_yellow",
        "#ffbd2e",
    )

    dot_green = colors.get(
        "dot_green",
        "#27c93f",
    )

    prompt_color = colors.get(
        "prompt_symbol",
        "#7ec699",
    )

    command_color = colors.get(
        "command_text",
        "#8a8a8a",
    )

    output_color = colors.get(
        "output_text",
        "#c9c9c9",
    )

    timestamp_color = colors.get(
        "timestamp",
        "#6b6f76",
    )

    path_color = colors.get(
        "path_text",
        "#6fb3d2",
    )

    cursor_color = colors.get(
        "cursor",
        "#c9c9c9",
    )

    badge_default = colors.get(
        "badge_default",
        "#9ba0a6",
    )

    badges = colors.get(
        "badges",
        {},
    )

    line_number_color = colors.get(
        "line_number",
        "#4b5568",
    )

    gutter_divider_color = colors.get(
        "gutter_divider",
        border,
    )

    link_color = (
        colors.get("link_text")
        or colors.get("link_color")
        or "#6fb3d2"
    )

    link_hover_color = colors.get(
        "link_hover",
        "#F72585",
    )

    # ========================================================
    # FONT
    # ========================================================

    font_family = cfg.get(
        "font_family",
        "'JetBrains Mono', 'Fira Code', 'White Rabbit', ui-monospace, monospace",
    )

    font_size = cfg.get(
        "font_size",
        14,
    )

    char_width = (
        font_size * CHAR_WIDTH_RATIO
    )

    # ========================================================
    # LAYOUT
    # ========================================================

    line_height = cfg.get(
        "line_height",
        round(font_size * 1.45),
    )

    command_gap_lines = cfg.get(
        "command_gap_lines",
        2,
    )

    # Fixed visible terminal viewport. Content taller than this is
    # automatically scrolled upward as newly revealed rows arrive.
    viewport_height = cfg.get(
        "viewport_height",
        360,
    )

    viewport_top = HEADER_HEIGHT
    viewport_bottom_pad = cfg.get(
        "viewport_bottom_pad",
        18,
    )

    scroll_duration = (
        cfg.get(
            "scroll_duration_ms",
            220,
        )
        / 1000.0
    )

    show_line_numbers = cfg.get(
        "show_line_numbers",
        True,
    )

    line_number_start = cfg.get(
        "line_number_start",
        0,
    )

    content_left_pad = cfg.get(
        "content_left_pad",
        20,
    )

    # ========================================================
    # TIMING
    # ========================================================

    timing = cfg.get(
        "timing",
        {},
    )

    char_dur = (
        timing.get(
            "typing_speed_ms",
            45,
        )
        / 1000.0
    )

    enter_pause = (
        timing.get(
            "enter_pause_ms",
            250,
        )
        / 1000.0
    )

    api_delay = (
        timing.get(
            "api_delay_ms",
            900,
        )
        / 1000.0
    )

    line_delay = (
        timing.get(
            "line_reveal_delay_ms",
            350,
        )
        / 1000.0
    )

    command_gap = (
        timing.get(
            "command_gap_ms",
            700,
        )
        / 1000.0
    )

    image_delay = (
        timing.get(
            "image_delay_ms",
            3500,
        )
        / 1000.0
    )

    # ========================================================
    # GENERAL CONFIG
    # ========================================================

    window_title = cfg.get(
        "window_title",
        "user@dev: ~",
    )

    show_idle_cursor = cfg.get(
        "show_idle_cursor_prompt",
        True,
    )

    commands = normalize_commands(
        cfg.get(
            "commands",
            [],
        )
    )

    prompt_prefix = cfg.get(
        "prompt_prefix",
        "➜ ~ ",
    )

    # ========================================================
    # GUTTER
    # ========================================================

    total_rows = count_rows(
        commands,
        command_gap_lines,
        show_idle_cursor,
    )

    max_line_number = (
        line_number_start
        + max(
            total_rows - 1,
            0,
        )
    )

    digits = (
        len(
            str(max_line_number)
        )
        if total_rows > 0
        else 1
    )

    gutter_font_size = max(
        font_size - 2,
        10,
    )

    gutter_char_width = (
        gutter_font_size
        * CHAR_WIDTH_RATIO
    )

    if show_line_numbers:
        gutter_num_width = (
            digits
            * gutter_char_width
        )

        num_right_x = (
            GUTTER_SIDE_PAD
            + gutter_num_width
        )

        gutter_width = (
            num_right_x
            + GUTTER_SIDE_PAD
        )

        left_pad = (
            gutter_width
            + content_left_pad
        )

    else:
        gutter_width = 0
        num_right_x = 0

        left_pad = cfg.get(
            "left_pad",
            32,
        )

    # ========================================================
    # DESIGN WIDTH
    #
    # IMPORTANT:
    #
    # This is the INTERNAL SVG coordinate width.
    #
    # The final SVG is rendered with:
    #
    #     width="100%"
    #
    # while preserving:
    #
    #     viewBox="0 0 DESIGN_WIDTH ..."
    #
    # This makes the entire terminal scale proportionally.
    # ========================================================

    configured_width = cfg.get(
        "width",
        760,
    )

    design_width = (
        configured_width
        + gutter_width
        if show_line_numbers
        else configured_width
    )

    # ========================================================
    # TEXT / LINK HELPER
    # ========================================================

    def make_content(
        text,
        base_color,
        href=None,
        link_match=None,
        hover_color=None,
    ):
        if not href:
            return (
                f'<tspan fill="{base_color}">'
                f'{esc(text)}'
                f'</tspan>'
            )

        match = (
            link_match
            if link_match
            else text
        )

        hover = (
            hover_color
            or link_hover_color
        )

        idx = (
            text.find(match)
            if match
            else -1
        )

        if idx == -1:
            pre = ""
            mid = text
            post = ""

        else:
            pre = text[:idx]
            mid = match
            post = text[
                idx + len(match):
            ]

        parts = []

        if pre:
            parts.append(
                f'<tspan fill="{base_color}">'
                f'{esc(pre)}'
                f'</tspan>'
            )

        parts.append(
            f'<a '
            f'href="{esc(href)}" '
            f'target="_blank" '
            f'rel="noopener noreferrer">'
            f'<tspan '
            f'class="term-link" '
            f'fill="{link_color}" '
            f'style="--link-hover:{hover}">'
            f'{esc(mid)}'
            f'</tspan>'
            f'</a>'
        )

        if post:
            parts.append(
                f'<tspan fill="{base_color}">'
                f'{esc(post)}'
                f'</tspan>'
            )

        return "".join(parts)

    # ========================================================
    # BODY
    # ========================================================

    body_parts = []

    cursor = Cursor()

    # Each entry is (time, previous_offset, new_offset).  The SVG uses
    # these to animate the terminal content upward without changing the
    # fixed outer viewport height.
    scroll_moves = []
    scroll_offset = 0.0

    def ensure_visible(row_top, row_bottom, reveal_time):
        nonlocal scroll_offset

        visible_bottom = (
            viewport_height
            - viewport_bottom_pad
        )

        desired_offset = max(
            0.0,
            row_bottom - visible_bottom,
        )

        # Never scroll backwards. A real terminal only advances the
        # viewport once new output reaches the bottom.
        if desired_offset > scroll_offset + 0.01:
            previous_offset = scroll_offset
            scroll_offset = desired_offset

            scroll_moves.append(
                (
                    max(
                        0.0,
                        reveal_time - scroll_duration,
                    ),
                    previous_offset,
                    scroll_offset,
                )
            )

    line_number = line_number_start

    # ========================================================
    # GUTTER
    # ========================================================

    def draw_gutter(
        baseline_y,
        reveal_time=None,
    ):
        nonlocal line_number

        if show_line_numbers:

            if reveal_time is None:
                reveal_time = 0

            body_parts.append(
                f'<text '
                f'x="{num_right_x:.2f}" '
                f'y="{baseline_y}" '
                f'text-anchor="end" '
                f'font-family="{esc(font_family)}" '
                f'font-size="{gutter_font_size}" '
                f'fill="{line_number_color}" '
                f'opacity="0">'

                f'{line_number}'

                f'<animate '
                f'attributeName="opacity" '
                f'to="1" '
                f'dur="0.03s" '
                f'begin="{reveal_time:.3f}s" '
                f'fill="freeze"/>'

                f'</text>'
            )

        line_number += 1

    # ========================================================
    # INITIAL TIMELINE
    # ========================================================

    y = TOP_PAD

    t = 0.3

    # ========================================================
    # COMMANDS
    # ========================================================

    for cmd in commands:

        cmd_text = str(
            cmd.get(
                "prompt",
                "",
            )
        )

        output_lines = cmd.get(
            "output",
            [],
        )

        # ====================================================
        # PROMPT
        # ====================================================

        prompt_baseline_y = y

        row_top_y = (
            y
            - font_size
            + 3
        )

        ensure_visible(
            row_top_y,
            y + 3,
            t,
        )

        draw_gutter(
            prompt_baseline_y,
            t,
        )

        prefix_x = left_pad

        body_parts.append(
            f'<text '
            f'x="{prefix_x}" '
            f'y="{prompt_baseline_y}" '
            f'font-family="{esc(font_family)}" '
            f'font-size="{font_size}" '
            f'fill="{prompt_color}" '
            f'opacity="0">'

            f'{esc(prompt_prefix)}'

            f'<animate '
            f'attributeName="opacity" '
            f'to="1" '
            f'dur="0.01s" '
            f'begin="{t:.3f}s" '
            f'fill="freeze"/>'

            f'</text>'
        )

        prefix_width = (
            len(prompt_prefix)
            * char_width
        )

        cmd_start_x = (
            prefix_x
            + prefix_width
        )

        command_start_time = t

        cursor.move_to(
            command_start_time,
            cmd_start_x,
            row_top_y,
        )

        # ====================================================
        # TYPE COMMAND
        # ====================================================

        for i, ch in enumerate(
            cmd_text
        ):

            char_time = (
                command_start_time
                + i * char_dur
            )

            cx = (
                cmd_start_x
                + i * char_width
            )

            display_ch = (
                ch
                if ch != " "
                else "\u00a0"
            )

            body_parts.append(
                f'<text '
                f'x="{cx:.2f}" '
                f'y="{prompt_baseline_y}" '
                f'font-family="{esc(font_family)}" '
                f'font-size="{font_size}" '
                f'fill="{command_color}" '
                f'opacity="0">'

                f'{esc(display_ch)}'

                f'<animate '
                f'attributeName="opacity" '
                f'to="1" '
                f'dur="0.01s" '
                f'begin="{char_time:.3f}s" '
                f'fill="freeze"/>'

                f'</text>'
            )

            cursor.move_to(
                char_time,
                cx + char_width,
                row_top_y,
            )

        type_end_time = (
            command_start_time
            + len(cmd_text)
            * char_dur
        )

        t = (
            type_end_time
            + (
                api_delay
                if cmd.get("api_delay")
                else enter_pause
            )
        )

        y += line_height

        # ====================================================
        # OUTPUT
        # ====================================================

        for line in output_lines:

            ltype = line.get(
                "type",
                "text",
            )

            line_time = t

            line_y = y

            row_top = (
                line_y
                - font_size
                + 3
            )

            ensure_visible(
                row_top,
                line_y + 3,
                line_time,
            )

            draw_gutter(
                line_y,
                line_time,
            )

            # =================================================
            # BADGE
            # =================================================

            if ltype == "badge":

                label = str(
                    line.get(
                        "label",
                        "",
                    )
                )

                text = str(
                    line.get(
                        "text",
                        "",
                    )
                )

                badge_bg = (
                    line.get(
                        "label_color"
                    )
                    or badges.get(
                        label,
                        badge_default,
                    )
                )

                label_text_color = (
                    line.get(
                        "label_text_color"
                    )
                    or bg
                )

                desc_color = (
                    line.get(
                        "text_color"
                    )
                    or output_color
                )

                pad_x = cfg.get(
                    "badge_pad_x",
                    8,
                )

                badge_h = (
                    font_size + 8
                )

                badge_w = (
                    len(label)
                    * char_width
                    * 0.62
                    + pad_x * 2
                )

                rect_y = (
                    row_top - 2
                )

                badge_cx = (
                    left_pad
                    + badge_w / 2
                )

                label_y = (
                    rect_y
                    + badge_h / 2
                    + font_size * 0.35
                )

                desc_svg = (
                    (
                        f'<text '
                        f'x="{left_pad + badge_w + 10:.2f}" '
                        f'y="{line_y}" '
                        f'font-family="{esc(font_family)}" '
                        f'font-size="{font_size}" '
                        f'fill="{desc_color}">'
                        f'{esc(text)}'
                        f'</text>'
                    )
                    if text
                    else ""
                )

                body_parts.append(
                    f'<g opacity="0">'

                    f'<rect '
                    f'x="{left_pad}" '
                    f'y="{rect_y:.2f}" '
                    f'width="{badge_w:.2f}" '
                    f'height="{badge_h}" '
                    f'rx="4" '
                    f'fill="{badge_bg}"/>'

                    f'<text '
                    f'x="{badge_cx:.2f}" '
                    f'y="{label_y:.2f}" '
                    f'text-anchor="middle" '
                    f'font-family="{esc(font_family)}" '
                    f'font-size="{font_size}" '
                    f'font-weight="700" '
                    f'fill="{label_text_color}">'
                    f'{esc(label)}'
                    f'</text>'

                    f'{desc_svg}'

                    f'<animate '
                    f'attributeName="opacity" '
                    f'to="1" '
                    f'dur="0.03s" '
                    f'begin="{line_time:.3f}s" '
                    f'fill="freeze"/>'

                    f'</g>'
                )

                t += line_delay

                y += line_height

                continue

            # =================================================
            # IMAGE
            # =================================================

            elif ltype == "image":

                image_line_time = (
                    t
                    + image_delay
                )

                src = str(
                    line.get(
                        "src",
                        "",
                    )
                )

                img_w = line.get(
                    "width",
                    96,
                )

                img_h = line.get(
                    "height",
                    96,
                )

                radius = line.get(
                    "radius",
                    (
                        img_w / 2
                        if line.get("circle")
                        else 10
                    ),
                )

                img_x = left_pad

                img_y = (
                    row_top - 2
                )

                ensure_visible(
                    img_y,
                    img_y + img_h,
                    image_line_time,
                )

                clip_id = (
                    f"imgclip{len(body_parts)}"
                )

                body_parts.append(
                    f'<clipPath '
                    f'id="{clip_id}">'

                    f'<rect '
                    f'x="{img_x}" '
                    f'y="{img_y:.2f}" '
                    f'width="{img_w}" '
                    f'height="{img_h}" '
                    f'rx="{radius}"/>'

                    f'</clipPath>'

                    f'<g opacity="0">'

                    f'<image '
                    f'href="{esc(src)}" '
                    f'xlink:href="{esc(src)}" '
                    f'x="{img_x}" '
                    f'y="{img_y:.2f}" '
                    f'width="{img_w}" '
                    f'height="{img_h}" '
                    f'clip-path="url(#{clip_id})" '
                    f'preserveAspectRatio="xMidYMid slice"/>'

                    f'<rect '
                    f'x="{img_x}" '
                    f'y="{img_y:.2f}" '
                    f'width="{img_w}" '
                    f'height="{img_h}" '
                    f'rx="{radius}" '
                    f'fill="none" '
                    f'stroke="{border}" '
                    f'stroke-width="1"/>'

                    f'<animate '
                    f'attributeName="opacity" '
                    f'to="1" '
                    f'dur="0.3s" '
                    f'begin="{image_line_time:.3f}s" '
                    f'fill="freeze"/>'

                    f'</g>'
                )

                t = (
                    image_line_time
                    + line_delay
                )

                y += (
                    img_h
                    + 10
                )

                continue

            # =================================================
            # PATH
            # =================================================

            elif ltype == "path":

                text = str(
                    line.get(
                        "text",
                        "",
                    )
                )

                color = (
                    line.get(
                        "color"
                    )
                    or path_color
                )

                content = (
                    f'<tspan '
                    f'fill="{color}">'
                    f'{esc(text)}'
                    f'</tspan>'
                )

            # =================================================
            # LINE
            # =================================================

            elif ltype == "line":

                ts = line.get(
                    "timestamp"
                )

                text = str(
                    line.get(
                        "text",
                        "",
                    )
                )

                text_color = (
                    line.get(
                        "text_color"
                    )
                    or output_color
                )

                href = (
                    line.get("href")
                    or line.get("link")
                )

                link_match = (
                    line.get(
                        "link_match"
                    )
                    or line.get(
                        "link_text"
                    )
                )

                text_content = make_content(
                    text,
                    text_color,
                    href,
                    link_match,
                    line.get(
                        "hover_color"
                    ),
                )

                if ts:

                    content = (
                        f'<tspan '
                        f'fill="{timestamp_color}">'
                        f'[{esc(ts)}]'
                        f'</tspan>'

                        f'<tspan '
                        f'fill="{text_color}">'
                        f'  '
                        f'</tspan>'

                        f'{text_content}'
                    )

                else:
                    content = text_content

            # =================================================
            # PLAIN TEXT
            # =================================================

            else:

                text = str(
                    line.get(
                        "text",
                        "",
                    )
                )

                color = (
                    line.get(
                        "color"
                    )
                    or output_color
                )

                href = (
                    line.get("href")
                    or line.get("link")
                )

                link_match = (
                    line.get(
                        "link_match"
                    )
                    or line.get(
                        "link_text"
                    )
                )

                content = make_content(
                    text,
                    color,
                    href,
                    link_match,
                    line.get(
                        "hover_color"
                    ),
                )

            # =================================================
            # NORMAL OUTPUT LINE
            # =================================================

            body_parts.append(
                f'<text '
                f'x="{left_pad}" '
                f'y="{line_y}" '
                f'font-family="{esc(font_family)}" '
                f'font-size="{font_size}" '
                f'opacity="0">'

                f'{content}'

                f'<animate '
                f'attributeName="opacity" '
                f'to="1" '
                f'dur="0.03s" '
                f'begin="{line_time:.3f}s" '
                f'fill="freeze"/>'

                f'</text>'
            )

            t += line_delay

            y += line_height

        # ====================================================
        # COMMAND GAP
        # ====================================================

        t += command_gap

        for _ in range(
            command_gap_lines
        ):
            line_number += 1
            y += line_height

    # ========================================================
    # IDLE PROMPT
    # ========================================================

    if show_idle_cursor:

        idle_baseline_y = y

        idle_row_top = (
            y
            - font_size
            + 3
        )

        ensure_visible(
            idle_row_top,
            y + 3,
            t,
        )

        draw_gutter(
            idle_baseline_y,
            t,
        )

        body_parts.append(
            f'<text '
            f'x="{left_pad}" '
            f'y="{idle_baseline_y}" '
            f'font-family="{esc(font_family)}" '
            f'font-size="{font_size}" '
            f'fill="{prompt_color}" '
            f'opacity="0">'

            f'{esc(prompt_prefix)}'

            f'<animate '
            f'attributeName="opacity" '
            f'to="1" '
            f'dur="0.01s" '
            f'begin="{t:.3f}s" '
            f'fill="freeze"/>'

            f'</text>'
        )

        idle_x = (
            left_pad
            + len(prompt_prefix)
            * char_width
        )

        cursor.move_to(
            t,
            idle_x,
            idle_row_top,
        )

        y += line_height

    # ========================================================
    # FINAL DIMENSIONS
    # ========================================================

    content_height = int(
        y + BOTTOM_PAD
    )

    # The SVG itself stays this height; only the content scrolls.
    total_height = int(
        viewport_height
    )

    cursor_w = (
        font_size
        * CURSOR_WIDTH_RATIO
    )

    cursor_h = (
        font_size
        * CURSOR_HEIGHT_RATIO
    )

    # ========================================================
    # HEADER DOTS
    # ========================================================

    dots = (
        f'<circle '
        f'cx="26" '
        f'cy="{HEADER_HEIGHT / 2:.1f}" '
        f'r="6" '
        f'fill="{dot_red}"/>'

        f'<circle '
        f'cx="46" '
        f'cy="{HEADER_HEIGHT / 2:.1f}" '
        f'r="6" '
        f'fill="{dot_yellow}"/>'

        f'<circle '
        f'cx="66" '
        f'cy="{HEADER_HEIGHT / 2:.1f}" '
        f'r="6" '
        f'fill="{dot_green}"/>'
    )

    # ========================================================
    # WINDOW TITLE
    # ========================================================

    title_text = (
        f'<text '
        f'x="{design_width / 2:.1f}" '
        f'y="{HEADER_HEIGHT / 2 + 4:.1f}" '
        f'text-anchor="middle" '
        f'font-family="{esc(font_family)}" '
        f'font-size="12" '
        f'fill="{command_color}">'

        f'{esc(window_title)}'

        f'</text>'
    )

    # ========================================================
    # GUTTER DIVIDER
    # ========================================================

    gutter_divider_svg = ""

    if show_line_numbers:

        gutter_divider_svg = (
            f'<line '
            f'x1="{gutter_width:.2f}" '
            f'y1="{HEADER_HEIGHT}" '
            f'x2="{gutter_width:.2f}" '
            f'y2="{total_height}" '
            f'stroke="{gutter_divider_color}" '
            f'stroke-width="1"/>'
        )

    # ========================================================
    # EMBED CUSTOM FONT
    # ========================================================

    font_face_css = ""

    if font_data:

        font_face_css = f"""
        @font-face {{
            font-family: "WhiteRabbitCustom";
            src: url(data:font/woff2;base64,{font_data}) format("woff2");
            font-weight: 100 900;
            font-style: normal;
            font-display: block;
        }}
        """

        # Replace the configured font family with the embedded
        # custom font as the first choice.
        svg_font_family = (
            '"WhiteRabbitCustom", '
            + font_family
        )

    else:
        svg_font_family = font_family

    # ========================================================
    # SCROLL ANIMATION
    # ========================================================

    scroll_svg = ""

    if scroll_moves:
        # One timeline avoids overlapping SMIL animations when several
        # consecutive output lines reach the bottom quickly.
        scroll_times = [0.0]
        scroll_offsets = [0.0]

        for move_time, _previous_offset, new_offset in scroll_moves:
            if move_time <= scroll_times[-1] + 0.0001:
                # Keep the latest offset for the same timestamp.
                scroll_offsets[-1] = new_offset
            else:
                scroll_times.append(move_time)
                scroll_offsets.append(new_offset)

        animation_end = max(
            t,
            scroll_times[-1] + scroll_duration,
            0.001,
        )

        # SVG keyTimes are normalized to the animation duration.
        key_times = [
            min(
                1.0,
                max(0.0, time_value / animation_end),
            )
            for time_value in scroll_times
        ]

        # If the first scroll happens at t=0, the first keyframe is already
        # the scrolled position. Otherwise the initial zero-offset frame
        # remains in place until the first scroll point.
        values = ";".join(
            f"0 {-offset:.2f}"
            for offset in scroll_offsets
        )

        scroll_svg = (
            f'<animateTransform '
            f'attributeName="transform" '
            f'type="translate" '
            f'values="{values}" '
            f'keyTimes="{";".join(f"{value:.6f}" for value in key_times)}" '
            f'begin="0s" '
            f'dur="{animation_end:.3f}s" '
            f'calcMode="linear" '
            f'fill="freeze"/>'
        )

    # ========================================================
    # FINAL SVG
    #
    # IMPORTANT:
    #
    # The outer SVG keeps a fixed viewport height. The terminal body is
    # clipped to that viewport and translated upward as new rows appear.
    # The complete generated content can therefore be arbitrarily long
    # without making the README image taller.
    # ========================================================

    svg = f"""<svg
width="100%"
viewBox="0 0 {design_width} {total_height}"
preserveAspectRatio="xMidYMin meet"
xmlns="http://www.w3.org/2000/svg"
xmlns:xlink="http://www.w3.org/1999/xlink">

<defs>

    <clipPath id="winclip">
        <rect
            x="0"
            y="0"
            width="{design_width}"
            height="{total_height}"
            rx="10"/>
    </clipPath>

    <clipPath id="bodyclip">
        <rect
            x="0"
            y="{HEADER_HEIGHT}"
            width="{design_width}"
            height="{max(1, total_height - HEADER_HEIGHT)}"/>
    </clipPath>

    <style>
        {font_face_css}

        .terminal-text {{
            font-family: {esc(svg_font_family)};
        }}

        .term-link {{
            cursor: pointer;
            text-decoration: underline;
            text-decoration-color: currentColor;
            text-decoration-thickness: 1px;
            text-underline-offset: 2px;
            transition: fill 0.15s ease;
        }}

        .term-link:hover {{
            fill: var(--link-hover) !important;
        }}
    </style>

</defs>

<g clip-path="url(#winclip)">

    <rect
        x="0"
        y="0"
        width="{design_width}"
        height="{total_height}"
        fill="{bg}"/>

    <rect
        x="0"
        y="0"
        width="{design_width}"
        height="{HEADER_HEIGHT}"
        fill="{header_bg}"/>

    <rect
        x="0.5"
        y="0.5"
        width="{design_width - 1}"
        height="{total_height - 1}"
        rx="10"
        fill="none"
        stroke="{border}"/>

    {dots}

    {title_text}

    {gutter_divider_svg}

    <g clip-path="url(#bodyclip)">
        <g>
            {''.join(body_parts)}

            {cursor.to_svg(
                cursor_color,
                cursor_w,
                cursor_h
            )}

            {scroll_svg}
        </g>
    </g>

</g>

</svg>
"""

    return svg


# ============================================================
# MAIN
# ============================================================

def main():

    config_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "terminal.config.json"
    )

    output_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else os.path.join(
            "assets",
            "terminal.svg",
        )
    )

    # --------------------------------------------------------
    # Load config
    # --------------------------------------------------------

    cfg = load_config(
        config_path
    )

    # --------------------------------------------------------
    # Find custom font
    #
    # Your current file:
    #
    # assets/wr.woff2
    #
    # This works whether the generator is executed from
    # the repository root.
    # --------------------------------------------------------

    configured_font_path = cfg.get(
        "font_file",
        "assets/wr.woff2",
    )

    if not os.path.isabs(
        configured_font_path
    ):
        configured_font_path = os.path.abspath(
            configured_font_path
        )

    font_data = load_font_base64(
        configured_font_path
    )

    # --------------------------------------------------------
    # Generate SVG
    # --------------------------------------------------------

    svg = build_svg(
        cfg,
        font_data,
    )

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    os.makedirs(
        os.path.dirname(output_path)
        or ".",
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Write SVG
    # --------------------------------------------------------

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(svg)

    print(
        f"Wrote {output_path} "
        f"({len(svg)} bytes)"
    )

    if font_data:
        print(
            f"Embedded custom font: "
            f"{configured_font_path}"
        )
    else:
        print(
            "Custom font was NOT embedded."
        )


if __name__ == "__main__":
    main()
