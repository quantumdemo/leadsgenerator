import os
import re
import urllib.parse
import requests

class GooglePlacesService:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY")

    def extract_search_query(self, input_text: str) -> str:
        """
        Step 2: Extract search query from Google Maps URL or raw text phrase.
        """
        input_text = input_text.strip()
        if not input_text:
            return ""

        # Check if URL
        if input_text.startswith("http://") or input_text.startswith("https://"):
            # Handle shortened maps links (maps.app.goo.gl)
            if "maps.app.goo.gl" in input_text or "goo.gl/maps" in input_text:
                try:
                    resp = requests.head(input_text, allow_redirects=True, timeout=5)
                    input_text = resp.url
                except Exception:
                    pass

            # Try parsing /maps/search/QUERY/
            search_match = re.search(r'/maps/search/([^/@?]+)', input_text)
            if search_match:
                extracted = urllib.parse.unquote(search_match.group(1)).replace('+', ' ')
                return extracted

            # Try parsing query parameter ?q=QUERY
            parsed = urllib.parse.urlparse(input_text)
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'q' in query_params:
                return query_params['q'][0]

            # Try parsing /maps/place/QUERY/
            place_match = re.search(r'/maps/place/([^/@?]+)', input_text)
            if place_match:
                return urllib.parse.unquote(place_match.group(1)).replace('+', ' ')

        # If not a URL, return as search phrase
        return input_text

    def fetch_business_listings(self, query: str, max_results: int = 20):
        """
        Step 3: Retrieve business listings using official Google Places API Text Search.
        Strictly raises an Error if GOOGLE_PLACES_API_KEY is missing.
        """
        if not self.api_key or self.api_key == "your_google_places_api_key_here":
            raise ValueError("Add API key to .env (GOOGLE_PLACES_API_KEY is required to fetch real Google Maps listings)")

        endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        results = []
        next_page_token = None

        while len(results) < max_results:
            params = {
                "query": query,
                "key": self.api_key
            }
            if next_page_token:
                params["pagetoken"] = next_page_token

            resp = requests.get(endpoint, params=params, timeout=10)
            data = resp.json()

            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                error_msg = data.get("error_message") or f"Google Places API error status: {data.get('status')}"
                raise RuntimeError(error_msg)

            places = data.get("results", [])
            for place in places:
                place_id = place.get("place_id")
                # Fetch Place Details for phone & website if needed
                details = self.fetch_place_details(place_id) if place_id else {}

                business = {
                    "place_id": place_id,
                    "name": place.get("name"),
                    "category": ", ".join(place.get("types", [])),
                    "address": place.get("formatted_address"),
                    "phone": details.get("formatted_phone_number") or place.get("formatted_phone_number"),
                    "website_url": details.get("website") or place.get("website"),
                    "google_maps_url": details.get("url") or f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total", 0),
                    "business_status": place.get("business_status", "OPERATIONAL")
                }
                results.append(business)
                if len(results) >= max_results:
                    break

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

            # Short sleep as required by Google Places API next_page_token availability
            import time
            time.sleep(2)

        return results

    def fetch_place_details(self, place_id: str) -> dict:
        """
        Fetches detailed fields for a specific Place ID.
        """
        if not self.api_key:
            return {}
        endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,formatted_phone_number,website,url",
            "key": self.api_key
        }
        try:
            resp = requests.get(endpoint, params=params, timeout=5)
            data = resp.json()
            if data.get("status") == "OK":
                return data.get("result", {})
        except Exception:
            pass
        return {}
