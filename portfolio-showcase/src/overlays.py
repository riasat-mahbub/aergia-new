"""Non-production visual overlays used only in recorded showcase pages."""

from __future__ import annotations

import asyncio

from playwright.async_api import Page


OVERLAY_CSS = """
#aergia-showcase-overlay {
  position: fixed;
  inset: 0;
  z-index: 2147483647;
  pointer-events: none;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
}
#aergia-showcase-caption {
  position: absolute;
  left: 24px;
  top: 22px;
  max-width: 420px;
  border: 1px solid rgba(255,255,255,.20);
  border-radius: 999px;
  padding: 8px 14px;
  color: #f8fafc;
  background: rgba(15,23,42,.82);
  box-shadow: 0 8px 24px rgba(15,23,42,.20);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .04em;
  opacity: 0;
  transform: translateY(-8px);
  transition: opacity 180ms ease, transform 180ms ease;
}
#aergia-showcase-caption[data-visible="true"] {
  opacity: 1;
  transform: translateY(0);
}
#aergia-showcase-card {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 48px;
  color: #2f4550;
  background:
    radial-gradient(circle at 18% 18%, rgba(218,255,239,.96) 0%, rgba(218,255,239,0) 38%),
    radial-gradient(circle at 86% 78%, rgba(5,150,105,.16) 0%, rgba(5,150,105,0) 34%),
    linear-gradient(135deg, #fcfffd 0%, #f3fff9 54%, #daffef 100%);
  opacity: 0;
  transition: opacity 220ms ease;
}
#aergia-showcase-card[data-visible="true"] { opacity: 1; }
#aergia-showcase-card-inner { max-width: 860px; text-align: center; }
#aergia-showcase-card-kicker {
  margin-bottom: 16px;
  color: #059669;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: .16em;
  text-transform: uppercase;
}
#aergia-showcase-card-title {
  margin: 0;
  color: #2f4550;
  font-size: clamp(34px, 5vw, 68px);
  line-height: 1.04;
  letter-spacing: -.04em;
}
#aergia-showcase-card-subtitle {
  margin: 22px auto 0;
  max-width: 660px;
  color: #41658a;
  font-size: 19px;
  line-height: 1.5;
}
#aergia-showcase-cursor {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 18px;
  height: 18px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #0f766e;
  box-shadow: 0 0 0 3px rgba(15,118,110,.22), 0 3px 10px rgba(15,23,42,.34);
  transform: translate(-50%, -50%);
  transition: left 60ms linear, top 60ms linear;
}
#aergia-showcase-cursor[data-pulse="true"] {
  animation: aergia-showcase-cursor-pulse 460ms ease-out;
}
#aergia-showcase-click-ring {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 42px;
  height: 42px;
  border: 3px solid #2dd4bf;
  border-radius: 50%;
  opacity: 0;
  transform: translate(-50%, -50%) scale(.25);
}
#aergia-showcase-click-ring[data-pulse="true"] {
  animation: aergia-showcase-click-ring 520ms cubic-bezier(.2,.7,.2,1);
}
#aergia-showcase-overlay[data-card-visible="true"] #aergia-showcase-cursor,
#aergia-showcase-overlay[data-card-visible="true"] #aergia-showcase-click-ring {
  visibility: hidden;
}
@keyframes aergia-showcase-cursor-pulse {
  0% { box-shadow: 0 0 0 3px rgba(15,118,110,.22), 0 3px 10px rgba(15,23,42,.34); }
  45% { box-shadow: 0 0 0 12px rgba(20,184,166,.28), 0 3px 10px rgba(15,23,42,.34); }
  100% { box-shadow: 0 0 0 3px rgba(15,118,110,.22), 0 3px 10px rgba(15,23,42,.34); }
}
@keyframes aergia-showcase-click-ring {
  0% { opacity: .95; transform: translate(-50%, -50%) scale(.25); }
  70% { opacity: .55; }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(1.25); }
}
"""


async def install_overlay(page: Page) -> None:
    """Install the cursor, caption, and title-card layer in the page DOM."""

    await page.add_style_tag(content=OVERLAY_CSS)
    await page.evaluate(
        """() => {
          if (document.getElementById('aergia-showcase-overlay')) return;
          const overlay = document.createElement('div');
          overlay.id = 'aergia-showcase-overlay';
          overlay.innerHTML = `
            <div id="aergia-showcase-caption" data-visible="false"></div>
            <div id="aergia-showcase-card" data-visible="false">
              <div id="aergia-showcase-card-inner">
                <div id="aergia-showcase-card-kicker"></div>
                <h1 id="aergia-showcase-card-title"></h1>
                <p id="aergia-showcase-card-subtitle"></p>
              </div>
            </div>
            <div id="aergia-showcase-cursor" data-pulse="false"></div>
            <div id="aergia-showcase-click-ring" data-pulse="false"></div>
          `;
          document.body.appendChild(overlay);
          const cursor = overlay.querySelector('#aergia-showcase-cursor');
          const ring = overlay.querySelector('#aergia-showcase-click-ring');
          document.addEventListener('mousemove', (event) => {
            cursor.style.left = `${event.clientX}px`;
            cursor.style.top = `${event.clientY}px`;
            ring.style.left = `${event.clientX}px`;
            ring.style.top = `${event.clientY}px`;
          });
        }""",
    )


async def set_caption(page: Page, text: str | None) -> None:
    await page.evaluate(
        """(value) => {
          const caption = document.getElementById('aergia-showcase-caption');
          if (!caption) return;
          caption.textContent = value || '';
          caption.dataset.visible = value ? 'true' : 'false';
        }""",
        text,
    )


async def show_card(page: Page, title: str, subtitle: str, kicker: str = "Aergia") -> None:
    await page.evaluate(
        """({kicker, title, subtitle}) => {
          const card = document.getElementById('aergia-showcase-card');
          if (!card) return;
          document.getElementById('aergia-showcase-card-kicker').textContent = kicker;
          document.getElementById('aergia-showcase-card-title').textContent = title;
          document.getElementById('aergia-showcase-card-subtitle').textContent = subtitle;
          document.getElementById('aergia-showcase-overlay').dataset.cardVisible = 'true';
          card.dataset.visible = 'true';
        }""",
        {"kicker": kicker, "title": title, "subtitle": subtitle},
    )


async def hide_card(page: Page) -> None:
    await page.evaluate(
        """() => {
          const card = document.getElementById('aergia-showcase-card');
          if (card) card.dataset.visible = 'false';
          const overlay = document.getElementById('aergia-showcase-overlay');
          if (overlay) overlay.dataset.cardVisible = 'false';
        }""",
    )


async def move_cursor(page: Page, x: float, y: float, *, steps: int = 18) -> None:
    """Move Playwright's pointer so the synthetic cursor follows it."""

    await page.mouse.move(x, y, steps=max(1, steps))
    # Browser-generated mousemove events are normally enough, but explicitly
    # pin the overlay to the final coordinates so video capture and the real
    # click target can never drift apart.
    await page.evaluate(
        """({x, y}) => {
          for (const id of ['aergia-showcase-cursor', 'aergia-showcase-click-ring']) {
            const element = document.getElementById(id);
            if (!element) continue;
            element.style.left = `${x}px`;
            element.style.top = `${y}px`;
          }
        }""",
        {"x": x, "y": y},
    )


async def pulse_cursor(page: Page) -> None:
    """Show a capture-friendly click ripple at the current cursor position."""

    await page.evaluate(
        """() => {
          for (const id of ['aergia-showcase-cursor', 'aergia-showcase-click-ring']) {
            const element = document.getElementById(id);
            if (!element) continue;
            element.dataset.pulse = 'false';
            void element.offsetWidth;
            element.dataset.pulse = 'true';
          }
        }""",
    )


async def pause(milliseconds: int) -> None:
    await asyncio.sleep(milliseconds / 1_000)
