#!/usr/bin/env python3

import asyncio
import io
import os
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

FPS = 15
CAPTURE_INTERVAL = 1.0 / FPS

# How long the GIF should run.
# 0 = automatically calculate from the SVG.
GIF_DURATION_SECONDS = 0

# GIF optimization.
GIF_COLORS = 256


async def render_gif(svg_path, gif_path):
    svg_path = Path(svg_path).resolve()
    gif_path = Path(gif_path).resolve()

    if not svg_path.exists():
        raise FileNotFoundError(f"SVG not found: {svg_path}")

    if not os.path.exists(CHROME_PATH):
        raise FileNotFoundError(
            f"Chrome not found at:\n{CHROME_PATH}"
        )

    gif_path.parent.mkdir(parents=True, exist_ok=True)

    svg_url = svg_path.as_uri()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=[
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
            ],
        )

        page = await browser.new_page(
            viewport={"width": 1200, "height": 1000},
            device_scale_factor=1,
        )

        await page.goto(svg_url, wait_until="load")

        # Wait until the SVG has actually loaded.
        await page.wait_for_timeout(500)

        dimensions = await page.evaluate(
            """
            () => {
                const svg = document.documentElement;

                return {
                    width: svg.viewBox.baseVal.width || svg.width.baseVal.value,
                    height: svg.viewBox.baseVal.height || svg.height.baseVal.value
                };
            }
            """
        )

        width = int(round(dimensions["width"]))
        height = int(round(dimensions["height"]))

        # Resize browser viewport to match the SVG exactly.
        await page.set_viewport_size(
            {
                "width": max(width, 1),
                "height": max(height, 1),
            }
        )

        await page.goto(svg_url, wait_until="load")
        await page.wait_for_timeout(100)

        # Find the longest animation timing in the SVG.
        animation_info = await page.evaluate(
            """
            () => {
                const svg = document.documentElement;

                let maxTime = 0;

                const all = svg.querySelectorAll("*");

                for (const el of all) {
                    for (const attr of ["begin", "dur"]) {
                        const value = el.getAttribute(attr);

                        if (!value) continue;

                        const matches = value.match(/([0-9.]+)s/g);

                        if (!matches) continue;

                        for (const match of matches) {
                            const seconds = parseFloat(match);

                            if (!Number.isNaN(seconds)) {
                                maxTime = Math.max(maxTime, seconds);
                            }
                        }
                    }
                }

                return {
                    width: svg.viewBox.baseVal.width || svg.width.baseVal.value,
                    height: svg.viewBox.baseVal.height || svg.height.baseVal.value,
                    maxTime
                };
            }
            """
        )

        width = int(round(animation_info["width"]))
        height = int(round(animation_info["height"]))

        # Add a small amount after the last animation event so
        # the final idle cursor state is visible.
        duration = (
            GIF_DURATION_SECONDS
            if GIF_DURATION_SECONDS > 0
            else max(animation_info["maxTime"] + 2.0, 5.0)
        )

        print(f"SVG size: {width}x{height}")
        print(f"Animation duration: {duration:.2f}s")
        print(f"FPS: {FPS}")
        print(f"Frames: {int(duration * FPS)}")

        frames = []

        total_frames = int(duration * FPS)

        for frame_number in range(total_frames):
            target_time = frame_number / FPS

            # Reload the SVG for every frame and manually seek the
            # animation timeline. This makes the resulting GIF
            # deterministic.
            await page.goto(svg_url, wait_until="load")

            await page.wait_for_timeout(50)

            await page.evaluate(
                """
                (targetTime) => {
                    const svg = document.documentElement;

                    if (svg.pauseAnimations) {
                        svg.pauseAnimations();
                    }

                    if (svg.setCurrentTime) {
                        svg.setCurrentTime(targetTime);
                    }
                }
                """,
                target_time,
            )

            await page.wait_for_timeout(30)

            png = await page.screenshot(
                type="png",
                omit_background=False,
            )

            image = Image.open(io.BytesIO(png)).convert("RGB")

            # Ensure exact SVG dimensions.
            if image.size != (width, height):
                image = image.resize(
                    (width, height),
                    Image.Resampling.LANCZOS,
                )

            # Convert to palette mode for GIF.
            image = image.quantize(
                colors=GIF_COLORS,
                method=Image.Quantize.MEDIANCUT,
            )

            frames.append(image)

            if frame_number % FPS == 0:
                print(
                    f"Captured {frame_number}/{total_frames} "
                    f"({target_time:.1f}s)"
                )

        await browser.close()

    if not frames:
        raise RuntimeError("No frames were captured.")

    print("Saving GIF...")

    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=True,
        disposal=2,
    )

    print(f"Done: {gif_path}")
    print(f"Size: {gif_path.stat().st_size / 1024:.1f} KB")


def main():
    svg_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "assets/terminal.svg"
    )

    gif_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "assets/terminal.gif"
    )

    asyncio.run(
        render_gif(svg_path, gif_path)
    )


if __name__ == "__main__":
    main()