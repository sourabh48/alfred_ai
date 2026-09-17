"""Additional checks against disposable synthetic native-runtime accounts."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from pathlib import Path
import time


def verify_extended(base, session, scenario, data, passed):
    import requests
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from tests.user_acceptance_scenario import PASSWORD

    users = [get_user_model().objects.create_user(username=f"concurrent_{index}", password=PASSWORD)
             for index in range(12)]

    def exercise(index):
        user = users[index]
        client = requests.Session()
        client.trust_env = False
        durations = []
        with client:
            client.get(base + "/login/", timeout=30).raise_for_status()
            response = client.post(base + "/login/", data={"username": user.username, "password": PASSWORD},
                                   headers={"X-CSRFToken": client.cookies["csrftoken"]},
                                   allow_redirects=False, timeout=30)
            assert response.status_code == 302, (index, response.status_code)
            headers = {"X-CSRFToken": client.cookies["csrftoken"]}
            for number in range(5):
                started = time.monotonic()
                response = client.post(base + "/api/expenses/", headers=headers, json={
                    "amount": 1000 + index, "category": "income", "classification": "other",
                    "direction": "credit", "description": f"Concurrent salary {index}/{number}",
                    "transaction_date": timezone.localdate().isoformat(),
                }, timeout=90)
                durations.append(time.monotonic() - started)
                assert response.status_code == 201, (index, response.status_code, response.text[:200])
            started = time.monotonic()
            payload = client.get(base + "/api/expenses/dashboard/", timeout=90).json()
            durations.append(time.monotonic() - started)
            assert Decimal(str(payload["summary"]["current_month_income"])) == 5 * (1000 + index), payload["summary"]
            response = client.get(base + "/api/expenses/", timeout=30)
            response.raise_for_status()
            rows = response.json()
            rows = rows if isinstance(rows, list) else rows["results"]
            assert len(rows) == 5 and all(row["user"] == user.pk for row in rows), (index, rows)
        return durations

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=12) as pool:
        durations = sorted(value for group in pool.map(exercise, range(12)) for value in group)
    passed("twelve_concurrent_users_isolated_writes_and_correct_totals", {
        "users": 12, "writes": 60, "timed_requests": len(durations), "errors": 0,
        "p95_seconds": round(durations[int((len(durations) - 1) * .95)], 3),
        "total_seconds": round(time.monotonic() - started, 2),
    })

    axe_path = Path(__file__).resolve().parents[1] / "artifacts" / "tools" / "package" / "axe.min.js"
    if not axe_path.is_file():
        raise RuntimeError("Download the official axe-core 4.13.0 npm package into artifacts/tools/package first")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    browser = webdriver.Chrome(options=options)
    findings = {"axe_version": "4.13.0", "layouts": [], "accessibility": []}
    try:
        browser.set_script_timeout(90)
        browser.get(base + "/login/")
        for cookie in session.cookies:
            browser.add_cookie({"name": cookie.name, "value": cookie.value, "path": "/"})
        wait = WebDriverWait(browser, 60)
        for width in (360, 390, 768, 1440):
            browser.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
                "width": width, "height": 900, "deviceScaleFactor": 1, "mobile": width < 768})
            for page in ("dashboard", "expenses", "settings", "documents", "loans"):
                browser.get(f"{base}/{page}/")
                wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                if page == "dashboard":
                    wait.until(lambda driver: "80,000" in driver.find_element(By.ID, "dashboardSummaryCards").text)
                # Audit the settled page, after entry fades have completed.
                wait.until(lambda driver: driver.execute_script(
                    "return document.getAnimations().filter(a => a.effect.getTiming().iterations !== Infinity)"
                    ".every(a => a.playState === 'finished' || a.playState === 'idle');"))
                overflow = browser.execute_script(
                    "return {width:innerWidth, scroll:document.documentElement.scrollWidth, "
                    "body:document.body.scrollWidth};")
                findings["layouts"].append({"page": page, **overflow,
                                             "passed": max(overflow["scroll"], overflow["body"]) <= width + 1})
                if width in (390, 1440):
                    browser.execute_script(axe_path.read_text(encoding="utf-8"))
                    result = browser.execute_async_script("""
                        const done = arguments[arguments.length - 1];
                        axe.run(document, {runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21aa']}})
                          .then(r => done({violations:r.violations.map(v => ({
                            id:v.id, impact:v.impact, description:v.description,
                            nodes:v.nodes.map(n => ({target:n.target, summary:n.failureSummary}))
                          })), incomplete:r.incomplete.map(v=>v.id)}))
                          .catch(e => done({error:String(e)}));
                    """)
                    assert not result.get("error"), result
                    findings["accessibility"].append({"page": page, "width": width, **result})
                    browser.save_screenshot(str(data / f"{page}-{width}.png"))
        # Actual keyboard focus can reach the main content without a pointer.
        browser.get(base + "/dashboard/")
        browser.execute_script("document.querySelector('.alfred-skip-link').focus();")
        from selenium.webdriver import ActionChains
        ActionChains(browser).send_keys(Keys.TAB).key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
        findings["skip_link_keyboard_target"] = browser.switch_to.active_element.get_attribute("outerHTML")
        assert "alfred-skip-link" in findings["skip_link_keyboard_target"], findings["skip_link_keyboard_target"]
        browser.switch_to.active_element.send_keys(Keys.ENTER)
        wait.until(lambda driver: driver.switch_to.active_element.get_attribute("id") == "alfredMainScroll")
        findings["skip_link_focuses_main"] = True
    finally:
        browser.quit()
        (data / "mobile-accessibility.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    assert all(item["passed"] for item in findings["layouts"]), "Responsive overflow: see mobile-accessibility.json"
    passed("responsive_layouts", {"pages": 5, "widths": [360, 390, 768, 1440]})
    serious = [item for item in findings["accessibility"]
               if any(v["impact"] in ("serious", "critical") for v in item["violations"])]
    assert not serious, "Accessibility findings: see mobile-accessibility.json"
    passed("automated_wcag_audit", {"pages": 5, "widths": [390, 1440], "serious_or_critical": 0,
                                   "scope": "Automated checks; manual screen-reader audit remains separate"})
