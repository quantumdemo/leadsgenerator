import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

class WebsiteCrawlerService:
    @staticmethod
    def check_and_extract(url: str) -> dict:
        """
        Step 4: Check business website availability and extract public email addresses.
        Returns website status and list of found email addresses.
        """
        if not url:
            return {
                "status": "No website listed",
                "accessible": False,
                "emails": [],
                "error": None
            }

        # Format URL properly
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            resp = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
            if resp.status_code >= 400:
                return {
                    "status": "Website unavailable or inaccessible",
                    "accessible": False,
                    "emails": [],
                    "error": f"HTTP {resp.status_code}"
                }

            # Search homepage content for emails
            emails = set(re.findall(EMAIL_REGEX, resp.text))

            # Crawl contact/about pages if found
            soup = BeautifulSoup(resp.text, "html.parser")
            contact_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                if "contact" in href or "about" in href or "reach" in href:
                    full_link = urllib.parse.urljoin(url, a["href"])
                    contact_links.append(full_link)

            for link in contact_links[:2]:  # Limit deep crawl to top 2 links
                try:
                    sub_resp = requests.get(link, headers=headers, timeout=5)
                    if sub_resp.status_code == 200:
                        sub_emails = re.findall(EMAIL_REGEX, sub_resp.text)
                        emails.update(sub_emails)
                except Exception:
                    pass

            # Filter out common invalid/placeholder emails
            valid_emails = [
                e for e in emails
                if not any(e.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.svg', '.gif', 'example.com', 'domain.com', 'wixpress.com'])
            ]

            return {
                "status": "Website listed",
                "accessible": True,
                "emails": list(valid_emails),
                "error": None
            }

        except Exception as e:
            return {
                "status": "Website unavailable or inaccessible",
                "accessible": False,
                "emails": [],
                "error": str(e)
            }
