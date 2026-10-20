import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def render_carousel():
    base_dir = Path(r"c:\Users\kekc85\IvanOS\workspace\carousel\kofe")
    html_path = base_dir / "preview" / "index.html"
    slides_dir = base_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Устанавливаем точный размер вьюпорта для слайда
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.wait_for_timeout(1000) # Даем подгрузиться шрифтам Google Fonts
        
        for i in range(1, 8):
            slide_id = f"#slide-{i}"
            slide_locator = page.locator(slide_id)
            output_file = slides_dir / f"slide-{i}.png"
            slide_locator.screenshot(path=str(output_file))
            print(f"Rendered: {output_file} ({output_file.stat().st_size} bytes)")
            
        browser.close()
        print("All 7 slides rendered successfully!")

if __name__ == "__main__":
    render_carousel()
