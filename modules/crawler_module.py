import os
import time
from typing import Optional
import requests
import re

# Module-level constant for headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 University project (xbukovina@stuba.sk)',
    'Connection': 'keep-alive',
}

REQUEST_DELAY = 20  # seconds as the source page specificies limit of 15


class Crawler:
    def __init__(self, base_url: str, save_dir: str, max_pages: int = 5, request_delay=REQUEST_DELAY):

        self.base_url = base_url
        self.save_dir = save_dir
        self.max_pages = max_pages
        self.request_delay = request_delay
        self.disallowed_routes = []
        # Using a requests.Session() object is more efficient for multiple requests
        # to the same domain as it reuses the underlying TCP connection.
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # Internal method to ensure the save directory exists.
    def _setup_directory(self):
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            print(f"Directory '{self.save_dir}' is ready.")
        except OSError as e:
            print(f"Error creating directory {self.save_dir}: {e}")
            raise

    def _fetch_and_process_robots(self):
        response = self._fetch_page(self.base_url + '/robots.txt')

        match_patern = r"(?s)User-agent: \*\s*(.*?)(?:(User-agent:)|#|^\n)"

        string_match = re.search(match_patern, response.text)

        if string_match:
            # Get the captured block (group 1)
            star_block_content = string_match.group(1).strip()
            print("Content under 'User-agent: *' block:")
            print(star_block_content)
            print("\n--- Now extracting individual rules ---")

            # Regex to find all Disallow/Crawl-delay lines within this block
            # It looks for lines starting with "Disallow:" or "Crawl-delay:"
            rules_pattern = r"^(Disallow:|Crawl-delay:)\s*(.*)$"

            # Use re.findall with re.MULTILINE flag to match ^ at the start of each line
            rules = re.findall(rules_pattern, star_block_content, re.MULTILINE)

            for rule_type, rule_value in rules:
                if (rule_type.strip() == 'Crawl-delay:'):
                    # Addition delay reserve of 5 seconds to be safe
                    self.request_delay = int(rule_value.strip()) + 5
                    continue

                self.disallowed_routes.append(re.escape(rule_value.strip()))

            print(f'Parsed crawler delay: {self.request_delay}')
            print(f'Disallowed routes: {self.disallowed_routes}')
            self._fetch_links_from_sitemap()

        else:
            print("Could not find 'User-agent: *' block.")

    def _fetch_links_from_sitemap(self):
        response = """<url>
<loc>http://worldheritagesite.org/new/whc-sessions/1980/</loc>
<lastmod>2025-07-05</lastmod>
</url>
<url>
<loc>http://worldheritagesite.org/whc-sessions/1981/</loc>
<lastmod>2025-07-05</lastmod>
</url>
<url>
<loc>http://worldheritagesite.org/data/whc-sessions/1982/</loc>
"""
        disallowed_pattern = f"(?!.*{'|'.join(self.disallowed_routes)})"

        link_pattern = r"(?:<loc>)" + (disallowed_pattern if len(
            self.disallowed_routes) > 0 else '') + r"(.+)(?:<\/loc>)"

        routes = re.findall(link_pattern, response, re.MULTILINE)

        print(routes)

    def _fetch_page(self, url: str) -> Optional[requests.Response]:
        time.sleep(self.request_delay)
        print(f"Downloading page: {url}")
        try:
            response = self.session.get(url, timeout=REQUEST_DELAY)
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            print(f"Could not download page {url}. Error: {e}")
            return None

    def _save_page(self, response: requests.Response, page_number: int):
        filename = os.path.join(self.save_dir, f"page_{page_number}.html")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Successfully saved to '{filename}'")
        except IOError as e:
            print(f"Could not save page content. Error: {e}")

    def run(self):
        print("--- Downloading robots.txt ---")
        self._fetch_and_process_robots()
        print("--- Starting Crawler ---")
        self._setup_directory()

        # current_url = self.base_url
        # pages_fetched = 0
        # print("-" * 20)

        # response = self._fetch_page(current_url)

        # if response:
        #     pages_fetched += 1
        #     self._save_page(response, pages_fetched)
        #     # current_url = self._find_next_page_url(response)

        #     # if current_url and pages_fetched < self.max_pages:
        #     #     print(f"Sleeping for {self.request_delay:.2f} seconds...")
        #     #     time.sleep(self.request_delay)
        # else:
        #     print("Stopping crawler due to a download error.")
        #     # break

        # # while current_url and pages_fetched < self.max_pages:

        # print("\n--- Crawler finished its work ---")
        # if not current_url:
        #     print("Reached the last page.")
        # if pages_fetched >= self.max_pages:
        #     print(f"Reached the max page limit of {self.max_pages}.")
