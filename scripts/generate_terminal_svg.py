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


def load_font_base64(font_path):
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
            f"<animate "
            f'attributeName="x" '
            f'to="{x}" '
            f'begin="{t}s" '
            f'dur="0.01s" '
            f'fill="freeze"/>'
            for t, x, y in self.moves
        )

        y_animates = "".join(
            f"<animate "
            f'attributeName="y" '
            f'to="{y}" '
            f'begin="{t}s" '
            f'dur="0.01s" '
            f'fill="freeze"/>'
            for t, x, y in self.moves
        )

        return (
            f"<rect "
            f'x="{x0}" '
            f'y="{y0}" '
            f'width="{width:.2f}" '
            f'height="{height:.2f}" '
            f'rx="{radius}" '
            f'fill="{color}">'
            f"<animate "
            f'attributeName="opacity" '
            f'values="1;1;0;0;1" '
            f'keyTimes="0;0.45;0.5;0.95;1" '
            f'dur="1.05s" '
            f'repeatCount="indefinite"/>'
            f"{x_animates}"
            f"{y_animates}"
            f"</rect>"
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
        rows += 1
        rows += len(
            cmd.get(
                "output",
                [],
            )
        )
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

    colors = cfg.get(
        "colors",
        {},
    )

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
        "#6814ba",
    )

    command_color = colors.get(
        "command_text",
        "#c9c9c9",
    )

    output_color = colors.get(
        "output_text",
        "#8a8a8a",
    )

    timestamp_color = colors.get(
        "timestamp",
        "#4b4b50",
    )

    cursor_color = colors.get(
        "cursor",
        "#c9c9c9",
    )

    line_number_color = colors.get(
        "line_number",
        "#4b5568",
    )

    gutter_divider_color = colors.get(
        "gutter_divider",
        border,
    )

    default_key_color = colors.get(
        "key_color",
        output_color,
    )

    default_colon_color = colors.get(
        "colon_color",
        output_color,
    )

    default_value_color = colors.get(
        "value_color",
        output_color,
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

    char_width = font_size * CHAR_WIDTH_RATIO

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
            70,
        )
        / 1000.0
    )

    enter_pause = (
        timing.get(
            "enter_pause_ms",
            900,
        )
        / 1000.0
    )

    line_delay = (
        timing.get(
            "line_reveal_delay_ms",
            40,
        )
        / 1000.0
    )

    command_gap = (
        timing.get(
            "command_gap_ms",
            1000,
        )
        / 1000.0
    )

    # ========================================================
    # GENERAL
    # ========================================================

    window_title = cfg.get(
        "window_title",
        "user@dev: ~",
    )

    show_idle_cursor = cfg.get(
        "show_idle_cursor_prompt",
        True,
    )

    commands = cfg.get(
        "commands",
        [],
    )

    shell_prompt = cfg.get(
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

    max_line_number = line_number_start + max(
        total_rows - 1,
        0,
    )

    digits = len(str(max_line_number)) if total_rows > 0 else 1

    gutter_font_size = max(
        font_size - 2,
        10,
    )

    gutter_char_width = gutter_font_size * CHAR_WIDTH_RATIO

    if show_line_numbers:

        gutter_num_width = digits * gutter_char_width

        num_right_x = GUTTER_SIDE_PAD + gutter_num_width

        gutter_width = num_right_x + GUTTER_SIDE_PAD

        left_pad = gutter_width + content_left_pad

    else:

        gutter_width = 0
        num_right_x = 0

        left_pad = cfg.get(
            "left_pad",
            32,
        )

    # ========================================================
    # WIDTH
    # ========================================================

    configured_width = cfg.get(
        "width",
        760,
    )

    design_width = (
        configured_width + gutter_width if show_line_numbers else configured_width
    )

    # ========================================================
    # FONT FAMILY
    # ========================================================

    if font_data:

        svg_font_family = '"WhiteRabbitCustom", ' + font_family

    else:

        svg_font_family = font_family

    font_attr = f'font-family="{esc(svg_font_family)}"'

    # ========================================================
    # BODY
    # ========================================================

    body_parts = []

    cursor = Cursor()

    line_number = line_number_start

    y = TOP_PAD

    t = 0.3

    # ========================================================
    # GUTTER
    # ========================================================

    def draw_gutter(
        baseline_y,
        reveal_time,
    ):
        nonlocal line_number

        if not show_line_numbers:
            line_number += 1
            return

        body_parts.append(
            f"<text "
            f'x="{num_right_x:.2f}" '
            f'y="{baseline_y}" '
            f'text-anchor="end" '
            f"{font_attr} "
            f'font-size="{gutter_font_size}" '
            f'fill="{line_number_color}" '
            f'opacity="0">'
            f"{line_number}"
            f"<animate "
            f'attributeName="opacity" '
            f'to="1" '
            f'dur="0.03s" '
            f'begin="{reveal_time:.3f}s" '
            f'fill="freeze"/>'
            f"</text>"
        )

        line_number += 1

    # ========================================================
    # ANIMATED TEXT
    # ========================================================

    def add_animated_text(
        text,
        x,
        baseline_y,
        start_time,
        color,
    ):
        for i, ch in enumerate(text):

            char_time = start_time + i * char_dur

            cx = x + i * char_width

            display_ch = ch if ch != " " else "\u00a0"

            body_parts.append(
                f"<text "
                f'x="{cx:.2f}" '
                f'y="{baseline_y}" '
                f"{font_attr} "
                f'font-size="{font_size}" '
                f'fill="{color}" '
                f'opacity="0">'
                f"{esc(display_ch)}"
                f"<animate "
                f'attributeName="opacity" '
                f'to="1" '
                f'dur="0.01s" '
                f'begin="{char_time:.3f}s" '
                f'fill="freeze"/>'
                f"</text>"
            )

        return start_time + len(text) * char_dur

    # ========================================================
    # INSTANT TEXT
    # ========================================================

    def add_instant_text(
        text,
        x,
        baseline_y,
        start_time,
        color,
    ):
        text_width = len(text) * char_width

        body_parts.append(
            f"<text "
            f'x="{x:.2f}" '
            f'y="{baseline_y}" '
            f"{font_attr} "
            f'font-size="{font_size}" '
            f'fill="{color}" '
            f'opacity="0" '
            f'textLength="{text_width:.2f}" '
            f'lengthAdjust="spacingAndGlyphs">'
            f"{esc(text)}"
            f"<animate "
            f'attributeName="opacity" '
            f'to="1" '
            f'dur="0.01s" '
            f'begin="{start_time:.3f}s" '
            f'fill="freeze"/>'
            f"</text>"
        )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    def get_timestamp(line):

        value = line.get("timestamp")

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        if not value.startswith("["):
            value = "[" + value

        if not value.endswith("]"):
            value = value + "]"

        return value

    # ========================================================
    # JSON DETECTION
    # ========================================================

    def is_json_property(line):
        return line.get(
            "type",
            "text",
        ) in (
            "key_value",
            "kv",
            "json",
        )

    def is_json_bracket(line):
        return (
            line.get(
                "type",
                "text",
            )
            == "json_bracket"
        )

    # ========================================================
    # JSON BRACKET
    # ========================================================

    def add_json_bracket(
        line,
        line_y,
        start_time,
    ):
        text = str(
            line.get(
                "text",
                "",
            )
        )

        color = line.get("color") or default_value_color

        add_instant_text(
            text,
            left_pad,
            line_y,
            start_time,
            color,
        )

        return left_pad + len(text) * char_width

    # ========================================================
    # JSON PROPERTY
    # ========================================================

    def add_key_value_line(
        line,
        line_y,
        start_time,
        trailing_comma,
    ):
        """
        Render:

          [TWO SPACES]"key": "value",

        IMPORTANT:
        The two indentation spaces are real text characters.

        The spacing after ':' remains ONE normal space.
        """

        key = str(
            line.get(
                "key",
                "",
            )
        )

        value = str(
            line.get(
                "value",
                "",
            )
        )

        key_color = line.get("key_color") or default_key_color

        colon_color = line.get("colon_color") or default_colon_color

        value_color = line.get("value_color") or default_value_color

        # ====================================================
        # EXACT JSON INDENTATION
        #
        # Two actual spaces before the key.
        # ====================================================

        indentation = "  "

        # ====================================================
        # Positions
        #
        # The indentation is part of the text flow.
        # The key itself therefore begins after the two
        # indentation spaces.
        # ====================================================

        indentation_x = left_pad

        key_x = indentation_x + 2 * char_width

        colon_x = key_x + len(key) * char_width

        value_x = colon_x + 2 * char_width

        # ====================================================
        # INDENTATION
        # ====================================================

        add_instant_text(
            indentation,
            indentation_x,
            line_y,
            start_time,
            key_color,
        )

        # ====================================================
        # KEY
        # ====================================================

        add_instant_text(
            key,
            key_x,
            line_y,
            start_time,
            key_color,
        )

        # ====================================================
        # COLON
        # ====================================================

        add_instant_text(
            ":",
            colon_x,
            line_y,
            start_time,
            colon_color,
        )

        # ====================================================
        # VALUE
        # ====================================================

        add_instant_text(
            value,
            value_x,
            line_y,
            start_time,
            value_color,
        )

        # ====================================================
        # COMMA
        #
        # Every property except the final one gets a comma.
        # ====================================================

        if trailing_comma:

            comma_x = value_x + len(value) * char_width

            add_instant_text(
                ",",
                comma_x,
                line_y,
                start_time,
                value_color,
            )

        # Cursor ends after the rendered line.
        rendered_width = (
            2 + len(key) + 1 + 1 + len(value) + (1 if trailing_comma else 0)
        )

        cursor_x = left_pad + rendered_width * char_width

        return cursor_x

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
        # SHELL COMMAND
        # ====================================================

        prompt_baseline_y = y

        row_top_y = y - font_size + 3

        draw_gutter(
            prompt_baseline_y,
            t,
        )

        prefix_x = left_pad

        add_instant_text(
            shell_prompt,
            prefix_x,
            prompt_baseline_y,
            t,
            prompt_color,
        )

        prefix_width = len(shell_prompt) * char_width

        cmd_start_x = prefix_x + prefix_width

        command_start_time = t

        cursor.move_to(
            command_start_time,
            cmd_start_x,
            row_top_y,
        )

        type_end_time = add_animated_text(
            cmd_text,
            cmd_start_x,
            prompt_baseline_y,
            command_start_time,
            command_color,
        )

        for i in range(len(cmd_text) + 1):

            char_time = command_start_time + i * char_dur

            cursor.move_to(
                char_time,
                cmd_start_x + i * char_width,
                row_top_y,
            )

        # ====================================================
        # ENTER
        # ====================================================

        t = type_end_time + enter_pause

        y += line_height

        # ====================================================
        # OUTPUT
        # ====================================================

        output_index = 0

        while output_index < len(output_lines):

            line = output_lines[output_index]

            line_type = line.get(
                "type",
                "text",
            )

            # =================================================
            # JSON BRACKET
            # =================================================

            if is_json_bracket(line):

                line_y = y

                row_top = line_y - font_size + 3

                draw_gutter(
                    line_y,
                    t,
                )

                cursor_x = add_json_bracket(
                    line,
                    line_y,
                    t,
                )

                cursor.move_to(
                    t,
                    cursor_x,
                    row_top,
                )

                t += line_delay

                y += line_height

                output_index += 1

                continue

            # =================================================
            # JSON PROPERTIES
            # =================================================

            if is_json_property(line):

                # Find the end of this consecutive JSON block.
                json_end_index = output_index

                while json_end_index + 1 < len(output_lines):

                    next_line = output_lines[json_end_index + 1]

                    if not is_json_property(next_line):
                        break

                    json_end_index += 1

                # Render each property separately.
                while output_index <= json_end_index:

                    json_line = output_lines[output_index]

                    line_y = y

                    row_top = line_y - font_size + 3

                    # Final property gets no comma.
                    trailing_comma = output_index < json_end_index

                    draw_gutter(
                        line_y,
                        t,
                    )

                    cursor_x = add_key_value_line(
                        json_line,
                        line_y,
                        t,
                        trailing_comma,
                    )

                    cursor.move_to(
                        t,
                        cursor_x,
                        row_top,
                    )

                    # =================================================
                    # CRITICAL:
                    #
                    # Advance time after EACH JSON property.
                    # Therefore the properties do NOT all appear
                    # simultaneously.
                    # =================================================

                    t += line_delay

                    y += line_height

                    output_index += 1

                continue

            # =================================================
            # REPL INPUT
            # =================================================

            line_y = y

            row_top = line_y - font_size + 3

            draw_gutter(
                line_y,
                t,
            )

            if line_type == "input":

                repl_prompt = str(
                    line.get(
                        "prompt",
                        "> ",
                    )
                )

                repl_text = str(
                    line.get(
                        "text",
                        "",
                    )
                )

                repl_prompt_color = line.get("prompt_color") or prompt_color

                repl_text_color = line.get("color") or command_color

                input_x = left_pad

                add_instant_text(
                    repl_prompt,
                    input_x,
                    line_y,
                    t,
                    repl_prompt_color,
                )

                repl_prompt_width = len(repl_prompt) * char_width

                repl_text_x = input_x + repl_prompt_width

                cursor.move_to(
                    t,
                    repl_text_x,
                    row_top,
                )

                input_end_time = add_animated_text(
                    repl_text,
                    repl_text_x,
                    line_y,
                    t,
                    repl_text_color,
                )

                for i in range(len(repl_text) + 1):

                    char_time = t + i * char_dur

                    cursor.move_to(
                        char_time,
                        repl_text_x + i * char_width,
                        row_top,
                    )

                t = input_end_time + enter_pause

                y += line_height

                output_index += 1

                continue

            # =================================================
            # NORMAL OUTPUT
            # =================================================

            text = str(
                line.get(
                    "text",
                    "",
                )
            )

            color = line.get("color") or output_color

            timestamp = get_timestamp(line)

            if timestamp:

                timestamp_width = len(timestamp) * char_width

                gap_width = char_width * 0.75

                text_x = left_pad + timestamp_width + gap_width

                add_instant_text(
                    timestamp,
                    left_pad,
                    line_y,
                    t,
                    timestamp_color,
                )

                add_instant_text(
                    text,
                    text_x,
                    line_y,
                    t,
                    color,
                )

            else:

                add_instant_text(
                    text,
                    left_pad,
                    line_y,
                    t,
                    color,
                )

            t += line_delay

            y += line_height

            output_index += 1

        # ====================================================
        # COMMAND GAP
        # ====================================================

        t += command_gap

        y += command_gap_lines * line_height

        line_number += command_gap_lines

    # ========================================================
    # IDLE PROMPT
    # ========================================================

    if show_idle_cursor:

        idle_baseline_y = y

        idle_row_top = y - font_size + 3

        draw_gutter(
            idle_baseline_y,
            t,
        )

        add_instant_text(
            shell_prompt,
            left_pad,
            idle_baseline_y,
            t,
            prompt_color,
        )

        idle_x = left_pad + len(shell_prompt) * char_width

        cursor.move_to(
            t,
            idle_x,
            idle_row_top,
        )

        y += line_height

    # ========================================================
    # DIMENSIONS
    # ========================================================

    total_height = int(y + BOTTOM_PAD)

    cursor_w = font_size * CURSOR_WIDTH_RATIO

    cursor_h = font_size * CURSOR_HEIGHT_RATIO

    # ========================================================
    # HEADER
    # ========================================================

    dots = (
        f"<circle "
        f'cx="26" '
        f'cy="{HEADER_HEIGHT / 2:.1f}" '
        f'r="6" '
        f'fill="{dot_red}"/>'
        f"<circle "
        f'cx="46" '
        f'cy="{HEADER_HEIGHT / 2:.1f}" '
        f'r="6" '
        f'fill="{dot_yellow}"/>'
        f"<circle "
        f'cx="66" '
        f'cy="{HEADER_HEIGHT / 2:.1f}" '
        f'r="6" '
        f'fill="{dot_green}"/>'
    )

    title_text = (
        f"<text "
        f'x="{design_width / 2:.1f}" '
        f'y="{HEADER_HEIGHT / 2 + 4:.1f}" '
        f'text-anchor="middle" '
        f"{font_attr} "
        f'font-size="12" '
        f'fill="{command_color}">'
        f"{esc(window_title)}"
        f"</text>"
    )

    # ========================================================
    # GUTTER DIVIDER
    # ========================================================

    gutter_divider_svg = ""

    if show_line_numbers:

        gutter_divider_svg = (
            f"<line "
            f'x1="{gutter_width:.2f}" '
            f'y1="{HEADER_HEIGHT}" '
            f'x2="{gutter_width:.2f}" '
            f'y2="{total_height}" '
            f'stroke="{gutter_divider_color}" '
            f'stroke-width="1"/>'
        )

    # ========================================================
    # FONT EMBEDDING
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

    # ========================================================
    # SVG
    # ========================================================

    svg = f"""<svg
width="100%"
viewBox="0 0 {design_width} {total_height}"
preserveAspectRatio="xMidYMin meet"
xmlns="http://www.w3.org/2000/svg">

<defs>

    <clipPath id="winclip">
        <rect
            x="0"
            y="0"
            width="{design_width}"
            height="{total_height}"
            rx="10"/>
    </clipPath>

    <style>
        {font_face_css}
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

    {''.join(body_parts)}

    {cursor.to_svg(
        cursor_color,
        cursor_w,
        cursor_h,
    )}

</g>

</svg>
"""

    return svg


# ============================================================
# MAIN
# ============================================================


def main():

    config_path = sys.argv[1] if len(sys.argv) > 1 else "terminal.config.json"

    output_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else os.path.join(
            "assets",
            "terminal.svg",
        )
    )

    # Load configuration
    cfg = load_config(config_path)

    # --------------------------------------------------------
    # Load the SAME font file.
    # --------------------------------------------------------

    configured_font_path = cfg.get(
        "font_file",
        "assets/wr.woff2",
    )

    if not os.path.isabs(configured_font_path):

        configured_font_path = os.path.abspath(configured_font_path)

    font_data = load_font_base64(configured_font_path)

    # --------------------------------------------------------
    # Build SVG
    # --------------------------------------------------------

    svg = build_svg(
        cfg,
        font_data,
    )

    # --------------------------------------------------------
    # Ensure output directory exists.
    # --------------------------------------------------------

    os.makedirs(
        os.path.dirname(output_path) or ".",
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

    print(f"Wrote {output_path} " f"({len(svg)} bytes)")

    if font_data:

        print(f"Embedded custom font: " f"{configured_font_path}")

    else:

        print("Custom font was NOT embedded.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
