"""Run with Python Playwright and its Chromium browser installed."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(root)))
Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
names = ('register', 'prelims', 'bq', 'model3d', 'earth')
failures = []
def check(name, ok, details=''):
    print(('PASS' if ok else 'FAIL') + ': ' + name + (' ' + str(details) if details else ''), flush=True)
    if not ok: failures.append(name)

def assert_landing(page, width, name, label):
    tab = page.locator('#t-' + name)
    image = page.locator('#p-' + name + ' figure img')
    rect = image.bounding_box()
    viewport = page.viewport_size
    visible = rect is not None and rect['y'] < viewport['height'] - 60 and rect['y'] + rect['height'] > 90
    check(f'{width} {label} {name}: correct tab and visible image', tab.get_attribute('aria-selected') == 'true' and visible, rect)
    check(f'{width} {label} {name}: matching image file', image.get_attribute('src') == f'assets/products/shot-{name}.webp')
    check(f'{width} {label} {name}: distinct destination', page.url.endswith('#p-' + name), page.url)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width in (390, 1440):
        page = browser.new_page(viewport={'width':width,'height':800}, is_mobile=(width==390), has_touch=(width==390), reduced_motion='reduce')
        page.goto(url, wait_until='networkidle')
        for name in names:
            page.evaluate('window.scrollTo(0,0)')
            if width == 390:
                page.locator('.menu-btn').click()
            page.locator('.has-mega > button').click()
            page.locator(f'.mega [data-tab="{name}"]').click()
            page.wait_for_timeout(100)
            assert_landing(page, width, name, 'menu')
            if width == 390: check(f'{width} {name}: mobile menu closes', page.locator('.menu-btn').get_attribute('aria-expanded') == 'false')
            page.locator(f'footer [data-tab="{name}"]').click(); page.wait_for_timeout(100)
            assert_landing(page, width, name, 'footer')
        for name in ('register','prelims'):
            page.locator(f'.mini[data-tab="{name}"]').click(); page.wait_for_timeout(100)
            assert_landing(page, width, name, 'card')
        page.goto(url + '#p-earth', wait_until='networkidle'); page.wait_for_timeout(100)
        assert_landing(page, width, 'earth', 'direct')
        page.reload(wait_until='networkidle'); page.wait_for_timeout(100)
        assert_landing(page, width, 'earth', 'reload')
        page.locator('footer [data-tab="bq"]').click(); page.wait_for_timeout(100)
        page.go_back(); page.wait_for_timeout(100)
        assert_landing(page, width, 'earth', 'back')
        page.go_forward(); page.wait_for_timeout(100)
        assert_landing(page, width, 'bq', 'forward')
        for name in names:
            page.goto(url + '#p-' + name, wait_until='networkidle'); page.wait_for_timeout(100)
            assert_landing(page, width, name, 'direct')
        page.locator('#t-register').click()
        page.locator('#t-register').press('ArrowRight')
        check(f'{width} keyboard selection updates product link', page.locator('#t-prelims').get_attribute('aria-selected') == 'true' and page.url.endswith('#p-prelims'))
        page.close()
    browser.close()
server.shutdown()
print('Failures:', failures)
raise SystemExit(bool(failures))
