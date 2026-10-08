import requests
from bs4 import BeautifulSoup

API_ENDPOINT = "http://127.0.0.1:8000/projects"

# Sample target source data payload representing scraped content
MOCK_SCRAPED_DATA = [
    {
        "title": "Autonomous Agricultural Monitoring Drone System",
        "original_url": "https://example.com/projects/agri-drone-v1",
        "description": "ESP32 based field telemetry and computer vision crop health analyzer."
    },
    {
        "title": "Smart Retail Inventory Tracking Pipeline",
        "original_url": "https://example.com/projects/retail-inventory-ai",
        "description": "Automated stock prediction, reorder alerts, and PostgreSQL real-time tracking."
    }
]

def run_scraper():
    print("Starting automated scraping pipeline...")
    for item in MOCK_SCRAPED_DATA:
        try:
            res = requests.post(API_ENDPOINT, json=item)
            if res.status_code == 201:
                print(f"[SUCCESS] Scraped & Inserted: {item['title']}")
            elif res.status_code == 400:
                print(f"[SKIPPED] Duplicate record exists: {item['title']}")
            else:
                print(f"[ERROR] Failed with status code {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    run_scraper()