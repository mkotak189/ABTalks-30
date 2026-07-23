import requests
from bs4 import BeautifulSoup
import re
import os

os.makedirs("raw_text", exist_ok=True)

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def scrape_page(url, output_filename):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove scripts, styles, nav, footer clutter
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = clean_text(text)

    with open(f"raw_text/{output_filename}", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved raw_text/{output_filename} ({len(text)} characters)")

# Clean FAQ page
scrape_page(
    "https://www.heart.org/en/health-topics/consumer-healthcare/why-is-health-insurance-important/faqs-about-health-insurance",
    "faq_clean.txt"
)

# Messy fact-sheet index page
scrape_page(
    "https://www.cms.gov/marketplace/resources/fact-sheets-faqs",
    "faq_messy.txt"
)