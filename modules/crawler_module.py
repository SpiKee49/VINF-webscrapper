import os
import time
from typing import Optional
import requests
from bs4 import BeautifulSoup

# Module-level constant for headers 
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,sk;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Connection': 'keep-alive',
}

REQUEST_DELAY = 20 #seconds as the source page specificies limit of 15

class Crawler:
    def __init__(self, base_url: str, save_dir: str, max_pages: int = 5, request_delay = REQUEST_DELAY):

        self.base_url = base_url
        self.save_dir = save_dir
        self.max_pages = max_pages
        self.request_delay = request_delay
        # Using a requests.Session() object is more efficient for multiple requests
        # to the same domain as it reuses the underlying TCP connection.
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    #Internal method to ensure the save directory exists.
    def _setup_directory(self):
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            print(f"Directory '{self.save_dir}' is ready.")
        except OSError as e:
            print(f"Error creating directory {self.save_dir}: {e}")
            raise

    def _fetch_page(self, url: str) -> Optional[requests.Response]:
        print(f"Downloading page: {url}")
        try:
            response = self.session.get(url, timeout=15)
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

    def _find_next_page_url(self, response: requests.Response) -> Optional[str]:
        soup = BeautifulSoup(response.text, 'html.parser')
        next_page_link = soup.select_one('a.next.page-numbers')
        if next_page_link and 'href' in next_page_link.attrs:
            return next_page_link['href']
        return None


    #  The main public method to start the crawling process.
    def run(self):
        print("--- Starting Crawler ---")
        self._setup_directory()

        current_url = self.base_url
        pages_fetched = 0

        while current_url and pages_fetched < self.max_pages:
            print("-" * 20)
            
            response = self._fetch_page(current_url)
            
            if response:
                pages_fetched += 1
                self._save_page(response, pages_fetched)
                current_url = self._find_next_page_url(response)

                if current_url and pages_fetched < self.max_pages:
                    print(f"Sleeping for {self.request_delay:.2f} seconds...")
                    time.sleep(self.request_delay)
            else:
                print("Stopping crawler due to a download error.")
                break
        
        print("\n--- Crawler finished its work ---")
        if not current_url:
            print("Reached the last page.")
        if pages_fetched >= self.max_pages:
            print(f"Reached the max page limit of {self.max_pages}.")


