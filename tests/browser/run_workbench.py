"""Opt-in real-browser acceptance lane; missing prerequisites are failures.

Run from an installed checkout: python tests/browser/run_workbench.py --output DIR
Install test-only tooling with pip install '.[browser]' and playwright install.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import threading
from pathlib import Path

from playwright.sync_api import BrowserType, Dialog, Page, expect, sync_playwright
from playwright.sync_api import Error as PlaywrightError

import core
from core.demo_server import DemoHandler, DemoServer
from core.project import parse_project


def source_hashes() -> dict[str, str]:
    root = Path(core.__file__).resolve().parent
    paths = sorted([*root.rglob("*.py"), *root.rglob("*.json")])
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def checked_download(page: Page, label: str, destination: Path) -> Path:
    with page.expect_download() as pending:
        page.get_by_role("link", name=label).click()
    download = pending.value
    assert download.failure() is None
    download.save_as(destination)
    assert destination.is_file() and destination.stat().st_size > 0
    return destination


def check_browser(browser_type: BrowserType, url: str, output: Path, require_kernel: bool) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    browser = browser_type.launch()
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    checks: list[str] = []
    try:
        page.goto(url)
        expect(page.locator("#status")).to_contain_text("Validated source is ready")
        expect(page.locator("#editPanel")).to_be_visible()
        original_source = page.locator("#source").input_value()
        original = checked_download(page, "Save project · revision 1", output / "original.json")
        initial = parse_project(original.read_text())
        assert initial.revision == 1
        checks.append("real project download parses and retains revision 1")

        # A genuine server error must not destroy the last valid project or downloads.
        page.get_by_label("One explicit edit", exact=True).fill("set wall thickness to 40 mm")
        page.get_by_role("button", name="Review proposed edit", exact=True).click()
        expect(page.locator("#status")).to_contain_text("Edit not applied")
        expect(page.locator("#editInstruction")).to_have_attribute("aria-invalid", "true")
        assert page.locator("#source").input_value() == original_source
        expect(page.get_by_role("link", name="Save project · revision 1")).to_be_visible()
        checks.append("invalid edit retains valid project and downloads")

        page.get_by_label("One explicit edit", exact=True).fill("set wall thickness to 2.4 mm")
        page.get_by_label("Reason (optional)", exact=True).fill("browser acceptance shell revision")
        # Keyboard activation and post-validation focus are part of the real journey.
        page.get_by_role("button", name="Review proposed edit", exact=True).focus()
        page.keyboard.press("Enter")
        expect(page.locator("#editChanges")).to_contain_text("wall_mm: 2 → 2.4")
        assert page.locator("#source").input_value() == original_source
        expect(page.locator("#applyEdit")).to_be_focused()
        page.keyboard.press("Enter")
        expect(page.locator("#projectSummary")).to_contain_text("revision 2")
        expect(page.locator("#compile")).to_be_focused()
        edited = parse_project(page.locator("#source").input_value())
        assert edited.revision == 2 and edited.spec.wall_mm == 2.4
        assert edited.source_text == initial.source_text
        assert edited.changes[-1].reason == "browser acceptance shell revision"
        saved = checked_download(page, "Save project · revision 2", output / "revised.json")
        assert parse_project(saved.read_text()).to_dict() == edited.to_dict()
        checks.append("keyboard review/confirm, canonical semantic revision, real project save")

        # Decline replacement: no file gets read into the current project.
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.locator("#projectFile").set_input_files(original)
        expect(page.locator("#projectFile")).to_have_value("")
        assert parse_project(page.locator("#source").input_value()).revision == 2
        checks.append("declined replacement retains unsaved revision")

        # Accept a malformed file: validation fails atomically, existing output remains.
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#projectFile").set_input_files({"name": "bad.json", "mimeType": "application/json", "buffer": b"{}"})
        expect(page.locator("#status")).to_contain_text("Project not opened")
        assert parse_project(page.locator("#source").input_value()).revision == 2
        checks.append("invalid real file import preserves the project")

        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#projectFile").set_input_files(saved)
        expect(page.locator("#status")).to_contain_text("Opened project")
        assert parse_project(page.locator("#source").input_value()).to_dict() == edited.to_dict()
        checks.append("real file import preserves revised geometry and history")

        # Inject a kernel outage at the HTTP boundary, then recover with the real
        # server below. Source downloads must survive an unsuccessful compilation.
        page.route("**/api/generate", lambda route: route.fulfill(
            status=503, content_type="application/json", body='{"error":"OpenSCAD was not found"}',
        ))
        page.get_by_role("button", name="Compile verified mesh & download STL", exact=True).click()
        expect(page.locator("#status")).to_contain_text("Previous validated output retained")
        retained = checked_download(page, "Save project · revision 2", output / "after-kernel-outage.json")
        assert parse_project(retained.read_text()).to_dict() == edited.to_dict()
        page.unroute("**/api/generate")
        checks.append("injected kernel outage retains usable source downloads; real server restored")

        mesh_hashes = {}
        if require_kernel:
            with page.expect_response(lambda response: response.url.endswith("/api/generate"), timeout=120000) as response:
                page.get_by_role("button", name="Compile verified mesh & download STL", exact=True).click()
            compiled = response.value.json()
            assert response.value.ok, compiled
            expect(page.locator("#status")).to_contain_text("Compiled mesh verified", timeout=120000)
            assert compiled["spec"]["wall_mm"] == 2.4
            assert compiled["evaluation"]["kernel_validity"] is True
            for part, artifact in compiled["mesh_artifacts"].items():
                label = f"Download {part} STL (SHA-256 {artifact['sha256'][:12]}…)"
                path = checked_download(page, label, output / f"{part}.stl")
                mesh_hashes[part] = hashlib.sha256(path.read_bytes()).hexdigest()
                assert mesh_hashes[part] == artifact["sha256"]
                assert artifact["verification"]["enclosure_features"]["valid"]
            checks.append("real revised body/lid kernel compilation and byte-verified browser STL downloads")

        for width in (320, 390, 768, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"overflow at {width}px"
            expect(page.locator("#previewEdit")).to_be_visible()
            page.screenshot(path=str(output / f"width-{width}.png"), full_page=True)
        checks.append("320/390/768/1440px layouts: no horizontal page overflow, controls present")
        page.evaluate("document.documentElement.style.zoom = '2'")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(output / "css-zoom-200.png"), full_page=True)
        page.evaluate("document.documentElement.style.zoom = ''")
        checks.append("200% CSS zoom layout; not a substitute for native zoom/screen-reader review")

        # Invalidating source must remove both compiled artifacts and semantic editing.
        page.locator("#source").fill("{}")
        expect(page.locator("#downloads")).to_be_empty()
        expect(page.locator("#editPanel")).to_be_hidden()
        expect(page.locator("#saveState")).to_contain_text("Unsaved work")
        page.locator("#source").press("Control+Enter")
        expect(page.locator("#status")).to_have_attribute("role", "alert")
        expect(page.locator("#result")).to_have_attribute("aria-busy", "false")
        checks.append("source invalidation removes stale outputs; keyboard validation recovers from errors")
        dialogs = []

        def keep_unsaved_work(dialog: Dialog) -> None:
            dialogs.append(dialog.type)
            dialog.dismiss()

        page.once("dialog", keep_unsaved_work)
        try:
            page.reload(timeout=10000)
        except PlaywrightError:
            # A dismissed beforeunload aborts navigation; assert the cause below.
            pass
        assert dialogs == ["beforeunload"], "Expected a real leave-page warning after editing"
        assert page.locator("#source").input_value() == "{}"
        checks.append("real beforeunload warning: dismissing reload retains the unsaved draft")
        assert not errors, errors
        return {"browser": browser_type.name, "version": browser.version, "checks": checks, "mesh_sha256": mesh_hashes}
    finally:
        page.screenshot(path=str(output / "final-state.png"), full_page=True)
        context.tracing.stop(path=str(output / "trace.zip"))
        context.close()
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=["all", "chromium", "firefox", "webkit"], default="all")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-kernel", action="store_true")
    args = parser.parse_args()
    if args.require_kernel and shutil.which("openscad") is None:
        parser.error("--require-kernel needs OpenSCAD; this acceptance lane cannot silently skip it")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output directory must be new or empty; previous acceptance evidence is never overwritten")
    args.output.mkdir(parents=True, exist_ok=True)
    sources_before = source_hashes()
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    server = DemoServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        with sync_playwright() as playwright:
            for name in (["chromium", "firefox", "webkit"] if args.browser == "all" else [args.browser]):
                results.append(check_browser(
                    getattr(playwright, name), f"http://127.0.0.1:{server.server_port}", args.output / name, args.require_kernel,
                ))
                print(f"PASS {name}: {len(results[-1]['checks'])} acceptance checks", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    evidence = {
        "platform": platform.platform(), "playwright": importlib.metadata.version("playwright"),
        "kernel_required": args.require_kernel, "results": results, "core_source_sha256": sources_before,
        "acceptance_script_sha256": script_hash,
    }
    assert source_hashes() == sources_before, "Product sources changed during browser acceptance; rerun against a stable snapshot"
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == script_hash, "Acceptance script changed during execution"
    (args.output / "receipt.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
