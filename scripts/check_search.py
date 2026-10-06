#!/usr/bin/env python3
"""Browser regression tests for delayed search, retries and modal focus."""
import argparse
import json
import shutil
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:8876")
parser.add_argument("--chrome", default=shutil.which("google-chrome"))
args = parser.parse_args()
INDEX = [{"title": "Seraphina hotfire", "text": "October 4 test data", "location": "Seraphina/oct-4-hotfire/"},
         {"title": "Sponsors", "text": "MACH partners", "location": "sponsors/"}]
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.chrome, args=["--no-sandbox"])
    context = browser.new_context()
    page = context.new_page()
    pending = []
    page.route("**/search.json", lambda route: pending.append(route))
    page.goto(args.url + "/team/", wait_until="domcontentloaded")
    page.locator("[data-mach-search-open]").click()
    query = page.locator("[data-mach-search-input]")
    query.fill("Seraphina")
    page.wait_for_timeout(50)
    query.fill("")
    assert len(pending) == 1
    pending[0].fulfill(json=INDEX)
    page.wait_for_timeout(150)
    assert page.locator("[data-mach-search-status]").inner_text() == "Type to search"
    assert page.locator("[data-mach-search-results] li").count() == 0
    query.fill("Sponsors")
    page.wait_for_function('()=>document.querySelector("[data-mach-search-status]").textContent === "1 result"')
    assert page.locator("[data-mach-search-results] a").inner_text().startswith("Sponsors")
    page.keyboard.press("Escape")
    assert page.locator("[data-mach-search-open]").evaluate("e=>e===document.activeElement")
    context.close()

    context = browser.new_context()
    page = context.new_page()
    requests = []
    def serve(route):
        requests.append(route)
        route.fulfill(status=503, body="Temporary failure") if len(requests) == 1 else route.fulfill(json=INDEX)
    page.route("**/search.json", serve)
    page.goto(args.url + "/team/", wait_until="domcontentloaded")
    page.locator("[data-mach-search-open]").click()
    page.locator("[data-mach-search-input]").fill("Seraphina")
    page.wait_for_function('()=>document.querySelector("[data-mach-search-status]").textContent.startsWith("Search is unavailable")')
    page.keyboard.press("Escape")
    page.locator("[data-mach-search-open]").click()
    page.locator("[data-mach-search-input]").fill("Seraphina")
    page.wait_for_function('()=>document.querySelector("[data-mach-search-status]").textContent === "1 result"')
    assert len(requests) == 2
    assert page.locator("[data-mach-search-results] a").get_attribute("href") == "/Seraphina/oct-4-hotfire/"
    context.close()

    # Closing a modal during its pending request must not leave stale content.
    context = browser.new_context()
    page = context.new_page()
    pending = []
    page.route("**/search.json", lambda route: pending.append(route))
    page.goto(args.url + "/team/", wait_until="domcontentloaded")
    page.locator("[data-mach-search-open]").click()
    page.locator("[data-mach-search-input]").fill("Seraphina")
    page.wait_for_timeout(50)
    page.keyboard.press("Escape")
    pending[0].fulfill(json=INDEX)
    page.wait_for_timeout(150)
    assert page.locator("[data-mach-search-results] li").count() == 0
    page.locator("[data-mach-search-open]").click()
    page.locator("[data-mach-search-input]").fill("Sponsors")
    page.wait_for_function('()=>document.querySelector("[data-mach-search-results] a")?.textContent.startsWith("Sponsors")')
    context.close()
    browser.close()
print(json.dumps({"search": "delayed clearing, new queries, transient retry, close/reopen and focus passed"}))
