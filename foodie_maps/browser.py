"""Selenium adapter: bounded scrolling, explicit waits and fail-closed blocking."""
import time
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from .parsing import parse_place, place_key


class Blocked(RuntimeError):
    pass


def make_driver(headless=False, binary=None, no_sandbox=False, profile_dir=None):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    if no_sandbox:
        options.add_argument("--no-sandbox")
    if profile_dir:
        from pathlib import Path
        options.add_argument("--user-data-dir=" + str(Path(profile_dir).resolve()))
    if binary:
        options.binary_location = binary
    options.add_argument("--window-size=1440,1100")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)
    driver.set_script_timeout(30)
    return driver


class MapsBrowser:
    def __init__(self, driver, language="fr", delay=2.0, timeout=20):
        self.driver, self.language, self.delay = driver, language, delay
        self.wait = WebDriverWait(driver, timeout)

    def check_block(self):
        url = self.driver.current_url
        body = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        if "/sorry/" in url or any(t in body for t in ("unusual traffic", "trafic inhabituel", "not a robot", "n'êtes pas un robot")):
            raise Blocked("Google requested verification. Collection stopped; progress is saved. Retry later in a visible browser.")

    def navigate(self, url):
        self.driver.get(url)
        time.sleep(self.delay)
        self.check_block()
        # Reject optional cookies without changing account settings.
        for button in self.driver.find_elements(By.CSS_SELECTOR, "button"):
            if button.text.strip().lower() in {"reject all", "tout refuser", "alle ablehnen"}:
                button.click()
                time.sleep(self.delay)
                break
        if urlsplit(self.driver.current_url).hostname == "consent.google.com":
            raise Blocked("Google consent page could not be dismissed. Run with a visible browser to inspect it.")
        self.check_block()

    def discover(self, search, max_results=120, max_scrolls=40):
        self.navigate(search.url)
        self.wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, '[role="feed"], h1.DUwDvf') or
                        "aucun résultat" in d.find_element(By.TAG_NAME, "body").text.lower() or
                        "no results found" in d.find_element(By.TAG_NAME, "body").text.lower())
        feeds = self.driver.find_elements(By.CSS_SELECTOR, '[role="feed"]')
        if not feeds:
            if self.driver.find_elements(By.CSS_SELECTOR, "h1.DUwDvf"):
                return [self.driver.current_url], "single_place"
            return [], "no_results"
        urls, stagnant = {}, 0
        for _ in range(max_scrolls):
            self.check_block()
            feed = self.driver.find_element(By.CSS_SELECTOR, '[role="feed"]')
            before = len(urls)
            for link in feed.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]'):
                url = link.get_attribute("href")
                urls.setdefault(place_key(url), url)
            if len(urls) >= max_results:
                return list(urls.values())[:max_results], "result_limit"
            if any(t in feed.text.lower() for t in ("you've reached the end", "vous êtes arrivé à la fin", "vous avez atteint la fin")):
                return list(urls.values()), "end_of_feed"
            stagnant = stagnant + 1 if len(urls) == before else 0
            if stagnant >= 4:
                return list(urls.values()), "stalled"
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
            time.sleep(self.delay)
        return list(urls.values()), "scroll_limit"

    def extract(self, url):
        separator = "&" if "?" in url else "?"
        self.navigate(url + separator + "hl=" + self.language)
        self.wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, 'h1.DUwDvf'))
        # Wait for details beyond the title; do not silently mark a skeleton page done.
        self.wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, '[data-item-id="address"], button[jsaction*="category"]'))
        # Scroll the place panel to load summary sections below the fold.
        title = self.driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf')
        panel = self.driver.execute_script('''let e=arguments[0];
            while(e && e !== document.body) {
                const s=getComputedStyle(e);
                if(e.scrollHeight>e.clientHeight+100 && /auto|scroll/.test(s.overflowY)) return e;
                e=e.parentElement;
            } return null;''', title)
        snapshots = [parse_place(self.driver.page_source, self.driver.current_url, self.language)]
        for _ in range(4):
            if panel is None:
                break
            try:
                self.driver.execute_script("arguments[0].scrollTop += 650", panel)
                time.sleep(self.delay)
                self.check_block()
                snapshots.append(parse_place(self.driver.page_source, self.driver.current_url, self.language))
            except StaleElementReferenceException:
                break
        result = snapshots[-1]
        all_ai = {s["text"]: s for snapshot in snapshots for s in snapshot["ai_summaries"]}
        result["ai_summaries"] = list(all_ai.values())
        if all_ai:
            result["ai_summary_status"] = "found"
        return result

    def evidence(self, directory, name):
        from pathlib import Path
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / (name + ".html")).write_text(self.driver.page_source, encoding="utf-8")
        self.driver.save_screenshot(str(directory / (name + ".png")))
