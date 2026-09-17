"""Record the portfolio storyboard with a real Aergia browser session."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, async_playwright

from .config import ShowcaseConfig
from .overlays import (
    install_overlay,
    move_cursor,
    pause,
    pulse_cursor,
    set_caption,
    show_card,
)
from .seed import SeedResult
from .storyboard import Storyboard, load_storyboard


@dataclass(frozen=True, slots=True)
class CaptureResult:
    raw_video: Path
    exported_pdf: Path


async def _login(browser: Browser, config: ShowcaseConfig, seed: SeedResult) -> dict:
    """Authenticate outside the recording context and retain cookies in memory."""

    context = await browser.new_context(
        viewport={"width": config.viewport_width, "height": config.viewport_height},
    )
    try:
        page = await context.new_page()
        page.set_default_timeout(15_000)
        await page.goto(f"{config.web_url}/login", wait_until="domcontentloaded")
        await page.get_by_label("Email").fill(seed.email)
        await page.get_by_label("Password").fill(seed.password)
        await page.get_by_role("button", name="Sign in", exact=True).click()
        await page.wait_for_url(re.compile(r".*/dashboard/?$"), timeout=30_000)
        await page.get_by_role("heading", name="Dashboard", exact=True).wait_for()
        return await context.storage_state()
    finally:
        await context.close()


async def _navigate(page: Page, config: ShowcaseConfig, path: str) -> None:
    await page.goto(f"{config.web_url}{path}", wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=6_000)
    except PlaywrightTimeoutError:
        # Polling or a slow preview should not hold the capture forever.
        pass
    await install_overlay(page)


async def _point_at(
    page: Page,
    locator,
    *,
    fallback_x: float = 640,
    fallback_y: float = 400,
) -> tuple[float, float]:
    target = locator.first
    try:
        await target.scroll_into_view_if_needed(timeout=3_000)
        box = await target.bounding_box()
    except Exception:  # noqa: BLE001 - visual guidance is best effort
        box = None
    if box:
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
    else:
        x, y = fallback_x, fallback_y
    await move_cursor(page, x, y)
    return x, y


async def _click_target(page: Page, locator, *, timeout: float = 5_000, after: int = 160) -> None:
    """Move to, animate, and click the exact visible center of a target."""

    target = locator.first
    await target.wait_for(state="visible", timeout=timeout)
    await _point_at(page, target)
    await pause(90)
    # Hover animations can shift a target by a few pixels. Re-measure after
    # hover settles so the visible cursor and the real mouse click stay exact.
    x, y = await _point_at(page, target)
    await pulse_cursor(page)
    await pause(70)
    await page.mouse.click(x, y, delay=50)
    await pause(after)


async def _click_if_present(page: Page, locator, *, timeout: float = 3_000) -> bool:
    try:
        await locator.first.wait_for(state="visible", timeout=timeout)
    except PlaywrightTimeoutError:
        return False
    await _click_target(page, locator, timeout=timeout)
    return True


async def _focus_and_fill(page: Page, locator, value: str, *, press_enter: bool = False) -> None:
    target = locator.first
    await _click_target(page, target, after=90)
    await target.fill(value)
    if press_enter:
        await target.press("Enter")
    await pause(220)


async def _choose_option(page: Page, locator, value: str) -> None:
    target = locator.first
    await _click_target(page, target, after=90)
    await target.select_option(value)
    await pause(300)


def _section_row(page: Page, title: str):
    return page.locator("[data-section-id]").filter(has=page.get_by_text(title, exact=True)).first


async def _show_scene(page: Page, storyboard: Storyboard, scene_id: str, locator=None) -> None:
    scene = storyboard.scene(scene_id)
    await set_caption(page, scene.caption)
    if locator is not None:
        await _point_at(page, locator)
    await pause(scene.target_milliseconds)


async def _import_existing_cv(
    page: Page,
    config: ShowcaseConfig,
    seed: SeedResult,
    storyboard: Storyboard,
) -> None:
    await _navigate(page, config, "/cvs")
    heading = page.get_by_role("heading", name="My CVs", exact=True)
    await heading.wait_for()
    await _show_scene(page, storyboard, "cv-list", heading)

    import_button = page.get_by_role("button", name="Import CV", exact=True)
    await _click_target(page, import_button)
    dialog_heading = page.get_by_role("heading", name="Import CV", exact=True)
    await dialog_heading.wait_for()
    await _show_scene(page, storyboard, "import-dialog", dialog_heading)

    await _focus_and_fill(page, page.locator("#import-title"), "Product Engineer — General")
    template = page.locator("#import-template")
    await template.locator('option[value="generic-modern"]').wait_for(state="attached", timeout=5_000)
    await _choose_option(page, template, "generic-modern")
    async with page.expect_file_chooser(timeout=5_000) as chooser_info:
        await _click_target(page, page.get_by_role("button", name="Choose PDF…", exact=True))
    chooser = await chooser_info.value
    await chooser.set_files(str(seed.source_pdf))
    await pause(350)
    await _click_target(page, page.get_by_role("button", name="Import", exact=True))
    await page.wait_for_url(re.compile(r".*/builder/[^/?]+.*"), timeout=60_000)
    await page.get_by_role(
        "heading",
        name="Product Engineer — General",
        exact=True,
        level=1,
    ).wait_for()
    await _show_scene(page, storyboard, "import-result")


async def _edit_and_customize(
    page: Page,
    storyboard: Storyboard,
) -> None:
    # Continue on the CV that was just imported so the narrative never jumps
    # between unrelated documents or templates.
    await page.get_by_role(
        "heading",
        name="Product Engineer — General",
        exact=True,
        level=1,
    ).wait_for()
    preview_heading = page.get_by_role("heading", name="Preview", exact=True)
    await _show_scene(page, storyboard, "builder", preview_heading)

    experience_row = _section_row(page, "Experience")
    await _click_target(page, experience_row.locator('[role="button"]').first)
    experience_entry = experience_row.get_by_text("Northstar Labs", exact=True)
    await _click_if_present(page, experience_entry)
    await _show_scene(page, storyboard, "edit", experience_row)

    # A small real edit makes the recording visibly demonstrate authoring.
    position = page.get_by_label("Position").first
    try:
        await position.wait_for(state="visible", timeout=4_000)
        await _focus_and_fill(page, position, "Product Engineer, Platform")
        await _click_target(page, page.get_by_role("button", name="Save", exact=True))
    except PlaywrightTimeoutError:
        # The seeded editor may keep an accordion entry closed depending on
        # the current frontend version. The rest of the showcase remains valid.
        pass

    customize_button = page.get_by_role("button", name="Customize", exact=True)
    await _click_target(page, customize_button)
    inspector = page.get_by_test_id("inspector")
    await inspector.wait_for()
    await _show_scene(page, storyboard, "customize", inspector)

    experience_card = inspector.locator("article").filter(has=page.get_by_text("Experience", exact=True)).first
    await _click_target(page, experience_card.get_by_role("button").first)
    heading_color = page.get_by_label("Heading color hex")
    await _focus_and_fill(page, heading_color, "#7C3AED", press_enter=True)
    heading_size = page.get_by_label("Heading size")
    await heading_size.wait_for(state="visible", timeout=3_000)
    await _choose_option(page, heading_size, "xl")
    appearance = experience_card.get_by_role("button", name="Appearance", exact=True)
    await _click_target(page, appearance)
    await _focus_and_fill(
        page,
        page.get_by_label("Section background hex"),
        "#F5F3FF",
        press_enter=True,
    )
    await page.get_by_label("Unsaved changes").wait_for(timeout=5_000)
    await _show_scene(page, storyboard, "design", page.locator("iframe").first)

    await _click_target(page, page.get_by_role("button", name="Content", exact=True))
    experience_row = _section_row(page, "Experience")
    add_from_library = experience_row.get_by_role("button", name="Add from library", exact=True)
    try:
        await add_from_library.wait_for(state="visible", timeout=1_500)
    except PlaywrightTimeoutError:
        await _click_target(page, experience_row.locator('[role="button"]').first)
        await add_from_library.wait_for(state="visible", timeout=5_000)
    await _click_target(page, add_from_library)

    library_dialog = page.get_by_role("heading", name="Add from library", exact=True)
    await library_dialog.wait_for(state="visible", timeout=5_000)
    await _show_scene(page, storyboard, "library", library_dialog)
    add_button = page.get_by_role("button", name="+ Add")
    if not await _click_if_present(page, add_button):
        raise RuntimeError("showcase Library picker did not contain an experience to add")
    await _show_scene(page, storyboard, "library-add")
    await _click_if_present(page, page.get_by_role("button", name="Save", exact=True))


async def _application_and_export(
    page: Page,
    seed: SeedResult,
    exported_pdf: Path,
    storyboard: Storyboard,
) -> None:
    back_button = page.get_by_role("button", name=re.compile("Back"))
    await _click_target(page, back_button)
    await page.wait_for_url(re.compile(r".*/cvs/?$"), timeout=15_000)
    await page.get_by_role("heading", name="My CVs", exact=True).wait_for()

    applications_tab = page.get_by_role("link", name="Applications", exact=True)
    await _show_scene(page, storyboard, "applications-tab", applications_tab)
    await _click_target(page, applications_tab)
    await page.wait_for_url(re.compile(r".*/applications/?$"), timeout=15_000)
    await page.get_by_role("heading", name="Applications", exact=True).wait_for()

    application_card = page.get_by_role("link", name="Northstar Systems", exact=True)
    await _show_scene(page, storyboard, "applications-list", application_card)
    view_application = page.get_by_role("link", name="View application", exact=True)
    latest_session_path = f"/api/v1/applications/{seed.application_id}/tailoring-sessions/latest"
    async with page.expect_response(
        lambda response: latest_session_path in response.url,
        timeout=15_000,
    ) as latest_session_info:
        await _click_target(page, view_application)
    latest_session_response = await latest_session_info.value
    if latest_session_response.status != 200:
        raise RuntimeError(
            "showcase application loaded without a valid tailoring session "
            f"(HTTP {latest_session_response.status})"
        )
    await page.wait_for_url(re.compile(rf".*/applications/{re.escape(seed.application_id)}/?$"), timeout=15_000)
    await page.get_by_role("heading", name="Northstar Systems", exact=True).wait_for()
    if await page.get_by_text("Tailoring session not found", exact=True).count():
        raise RuntimeError("showcase application displayed a missing tailoring session error")
    relevance = page.get_by_text(re.compile(r"Relevance|One-page fit")).first
    await _show_scene(page, storyboard, "application", relevance)

    edit_link = page.get_by_role("link", name="Open/Edit CV", exact=True)
    await _click_target(page, edit_link)
    await page.wait_for_url(re.compile(r".*/builder/[^/?]+.*"), timeout=30_000)
    await page.get_by_role("heading", name=re.compile("Northstar Systems")).wait_for()
    export_button = page.get_by_title("Export PDF")
    await _show_scene(page, storyboard, "tailored", export_button)

    exported_pdf.parent.mkdir(parents=True, exist_ok=True)
    async with page.expect_download(timeout=45_000) as download_info:
        await _click_target(page, export_button)
    download = await download_info.value
    await download.save_as(str(exported_pdf))
    await _show_scene(page, storyboard, "export", export_button)


async def capture_tour(
    config: ShowcaseConfig,
    seed: SeedResult,
    runtime_dir: Path,
    *,
    headed: bool = False,
) -> CaptureResult:
    """Record one deterministic tour and return its raw media paths."""

    raw_dir = runtime_dir / "raw-video"
    raw_dir.mkdir(parents=True, exist_ok=True)
    exported_pdf = runtime_dir / "exported" / "aergia-showcase.pdf"
    storyboard = load_storyboard(config)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not headed)
        try:
            storage_state = await _login(browser, config, seed)
            context: BrowserContext = await browser.new_context(
                viewport={"width": config.viewport_width, "height": config.viewport_height},
                screen={"width": config.viewport_width, "height": config.viewport_height},
                storage_state=storage_state,
                record_video_dir=str(raw_dir),
                record_video_size={"width": config.viewport_width, "height": config.viewport_height},
                locale="en-CA",
                timezone_id="America/Halifax",
            )
            context.set_default_timeout(15_000)
            page = await context.new_page()
            video = page.video
            if video is None:
                raise RuntimeError("Playwright did not create a recording handle")

            # Paint the opening card before the first product navigation. The
            # encoder trims this short preroll, so no blank frame or app shell
            # can appear before the finished poster.
            await page.set_content(
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<title>Aergia showcase</title></head>"
                "<body style='margin:0;background:#fcfffd'></body></html>",
                wait_until="load",
            )
            await install_overlay(page)
            await show_card(
                page,
                storyboard.scene("intro").caption,
                "A private workspace for turning reusable career material into a polished CV.",
                "Aergia",
            )
            await pause(round(config.recording_preroll_seconds * 1_000))
            await pause(storyboard.scene("intro").target_milliseconds)

            await _navigate(page, config, "/dashboard")
            await _show_scene(page, storyboard, "dashboard")

            await _import_existing_cv(page, config, seed, storyboard)
            await _edit_and_customize(page, storyboard)
            await _application_and_export(page, seed, exported_pdf, storyboard)

            await show_card(
                page,
                storyboard.scene("outro").caption,
                "Create · Reuse · Tailor · Export",
                "Aergia",
            )
            await pause(storyboard.scene("outro").target_milliseconds)

            await context.close()
            raw_video_path = Path(await video.path())
            final_raw_path = runtime_dir / "aergia-showcase.raw.webm"
            shutil.copyfile(raw_video_path, final_raw_path)
            return CaptureResult(raw_video=final_raw_path, exported_pdf=exported_pdf)
        finally:
            # Closing an already closed context is safe in Playwright, but do
            # not leave a recording context open when a scene fails.
            for context_candidate in list(browser.contexts):
                await context_candidate.close()
            await browser.close()
