from collections import deque
import csv
from datetime import datetime
import os
import time
from typing import Deque, Optional, Set
from urllib.parse import urljoin, urlparse
import re
import random
import requests

# Module-level constant for headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 University project (xbukovina@stuba.sk)',
    'Connection': 'keep-alive',
}

REQUEST_DELAY = 15  # seconds (inclusive)
DOWNLOAD_LOG_FILE = "download_log.csv"
DOWNLOAD_QUEUE_FILE = "download_queue.txt"


class Crawler:
    def __init__(self, base_url: str, save_dir: str, max_pages: int = 5, request_delay=REQUEST_DELAY):

        self.base_url = base_url
        self.save_dir = save_dir
        self.html_dir = os.path.join(save_dir, 'html_output')
        self.max_pages = max_pages
        self.request_delay = request_delay
        self.disallowed_routes = []
        self.base_domain = urlparse(base_url).netloc
        # Using a requests.Session() object is more efficient for multiple requests
        # to the same domain as it reuses the underlying TCP connection.
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        self._ensure_log_file_header()  # Ensure CSV header exists

        self.url_queue: Deque[str] = deque()
        self.visited_urls: Set[str] = set()

        self._ensure_log_file_header()
        self._load_queue_from_file()
        if not self.url_queue:
            self.url_queue.append(base_url)
        print(
            f"Crawler initialized. Queue size: {len(self.url_queue)}, Disallowed routes: {self.disallowed_routes}")

    # Internal method to ensure the save directory exists.
    def _setup_directory(self):

        try:
            os.makedirs(self.save_dir, exist_ok=True)
            print(f"Directory '{self.save_dir}' is ready.")

            os.makedirs(self.html_dir, exist_ok=True)
            print(f"Directory '{self.html_dir}' is ready.")

        except OSError as e:
            print(f"Error creating directory {self.save_dir}: {e}")
            raise

    def _ensure_log_file_header(self):
        log_filepath = os.path.join(self.save_dir, DOWNLOAD_LOG_FILE)
        if not os.path.exists(log_filepath):
            # Ensure dir exists for log file
            os.makedirs(os.path.dirname(log_filepath), exist_ok=True)
            with open(log_filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ['url', 'downloaded_at', 'filesize_bytes', 'filepath_saved'])

    def _load_queue_from_file(self):
        queue_filepath = os.path.join(self.save_dir, DOWNLOAD_QUEUE_FILE)
        if os.path.exists(queue_filepath):
            with open(queue_filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and url not in self.visited_urls and url not in self.url_queue:
                        self.url_queue.append(url)
            print(
                f"Loaded {len(self.url_queue)} URLs from '{queue_filepath}' into memory queue.")
        else:
            print(
                f"No existing queue file found at '{queue_filepath}'. Starting fresh.")

    def _load_robots(self):
        robots_path = os.path.join(self.save_dir, 'robots.txt')

        if not os.path.exists(robots_path):

            print("--- Downloading robots.txt ---")
            robots_url = self.base_url.rstrip('/') + '/robots.txt'
            response = self._fetch_page(robots_url)

            if not response:
                print("Failed to download robots.txt")
                return

            try:
                with open(robots_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"Saved robots.txt to {robots_path}")
            except IOError as e:
                print(f"Could not save robots.txt: {e}")

        # Read back the saved file and continue processing with that content
        try:
            with open(robots_path, 'r', encoding='utf-8') as f:
                robots_text = f.read()
        except IOError:
            # Fallback to response content if file read fails
            robots_text = response.text

        match_pattern = r"(?s)User-agent: \*\s*(.*?)(?:(User-agent:)|#|^\n)"
        string_match = re.search(match_pattern, robots_text)

        if string_match:
            # Get the captured block (group 1)
            star_block_content = string_match.group(1).strip()
            print("Content under 'User-agent: *' block:")
            print(star_block_content)
            print("\n--- Now extracting individual rules ---")

            # Regex to find all Disallow/Crawl-delay lines within this block
            rules = re.findall(
                r"^(Disallow:|Crawl-delay:)\s*(.*)$", star_block_content, re.MULTILINE)

            for rule_type, rule_value in rules:
                if rule_type.strip().lower() == 'crawl-delay:':
                    try:
                        self.request_delay = int(float(rule_value.strip()))
                    except ValueError:
                        pass
                    continue

                val = rule_value.strip()
                if val:
                    self.disallowed_routes.append(val)

            print(f'Parsed crawler delay: {self.request_delay}')
            print(f'Disallowed routes: {self.disallowed_routes}')

        else:
            print("Could not find 'User-agent: *' block.")

    def _fetch_page(self, url: str) -> Optional[requests.Response]:
        delay = random.randint(self.request_delay,
                               self.request_delay+5)
        time.sleep(delay)
        print(f"Downloading page: {url} [delay: {delay}]")
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            print(f"Could not download page {url}. Error: {e}")
            return None

    def _save_page(self, url: str, response: requests.Response) -> Optional[tuple[str, int]]:

        parsed_url = urlparse(url)
        # We want the path part of the URL, e.g., '/random/subpage.html'
        # If the path is just '/', we might want to name it 'index.html' or similar.
        # For simplicity, let's use a hashed name for the root if path is empty,
        # or use the path directly.
        relative_path_segment = parsed_url.path.lstrip('/')
        if not relative_path_segment or relative_path_segment.endswith('/'):
            # If path is empty (e.g., 'www.example.com') or ends with a slash
            # create a default file name like 'index.html'
            # or hash the full URL for uniqueness if you prefer
            relative_path_segment = os.path.join(
                relative_path_segment, "index.html")

        # Join with domain to create unique folders (optional, but good for large crawls)
        # e.g., 'data/html/www.xyz/random/subpage.html'
        # Or just use the 'save_base_dir' directly if you want all in one flat structure
        # For your request, we want /random/subpage.html part, so we'll use just the path

        # Construct the full path
        # save_path_within_base = os.path.join(parsed_url.netloc, relative_path_segment) # For domain-specific folders
        # For saving directly under base_dir based on URL path
        save_path_within_base = relative_path_segment

        full_filepath = os.path.join(self.html_dir, save_path_within_base)

        # Ensure parent directories exist (e.g., data/html/random/)
        os.makedirs(os.path.dirname(full_filepath), exist_ok=True)

        try:
            with open(full_filepath, 'w', encoding='utf-8') as f:
                f.write(response.text)

            filesize = len(response.text.encode('utf-8'))  # Get size in bytes
            print(
                f"Successfully saved '{url}' to '{full_filepath}' ({filesize} bytes)")

            # Return the path relative to save_base_dir for logging clarity
            return save_path_within_base, filesize

        except IOError as e:
            print(f"Could not save page content for '{url}'. Error: {e}")
            return None

    def _log_download_info(self, url: str, downloaded_at: datetime, filesize_bytes: int, filepath_saved: str):
        log_filepath = os.path.join(self.save_dir, DOWNLOAD_LOG_FILE)
        try:
            with open(log_filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([url, downloaded_at.isoformat(),
                                filesize_bytes, filepath_saved])
            print(f"Logged download info for {url}")
        except IOError as e:
            print(f"Error logging download info for {url}: {e}")

    def _find_relative_links(self, current_page_url: str, html_content: str):
        # Regex to find href attributes.
        # It tries to be specific to 'a' tags but might still catch other 'href's.
        # It captures the URL part (group 1)
        href_pattern = r'<a\s+(?:[^>]*?\s+)?href=["\'](?!#)([^"\' >]+)["\']'

        found_links = re.findall(href_pattern, html_content, re.IGNORECASE)

        for href in found_links:
            # 1. Normalize and make absolute (urljoin is essential here)
            absolute_url = urljoin(current_page_url, href).split('#')[
                0]  # Remove fragments
            parsed_absolute_url = urlparse(absolute_url)

            # 2. Filter out external domains
            if parsed_absolute_url.netloc != self.base_domain:
                continue

            # 3. Filter out disallowed routes using the URL path
            is_disallowed = False
            for route in self.disallowed_routes:
                # route might be '/whsorg-admin/' or '/api/'
                # Check if the URL path starts with any disallowed route
                if parsed_absolute_url.path.startswith(route):
                    is_disallowed = True
                    break

            if is_disallowed:
                continue

            # 4. Add to queue if not already visited or in queue
            if absolute_url not in self.visited_urls and absolute_url not in self.url_queue:
                self.url_queue.append(absolute_url)

    def _save_queue_to_file(self):
        """Saves the current state of the in-memory queue to the download queue file."""
        queue_filepath = os.path.join(self.save_dir, DOWNLOAD_QUEUE_FILE)
        try:
            with open(queue_filepath, 'w', encoding='utf-8') as f:
                for url in self.url_queue:
                    f.write(url + '\n')
            print(f"Saved {len(self.url_queue)} URLs to '{queue_filepath}'.")
        except IOError as e:
            print(f"Error saving queue to file: {e}")

    def run(self):
        print("--- Setup directory ---")
        self._setup_directory()

        print("--- Loading robots.txt rules ---")
        self._load_robots()  # Loads rules into self.disallowed_routes

        pages_fetched = 0

        print(f"--- Starting crawl loop (Max pages: {self.max_pages}) ---")
        while self.url_queue and pages_fetched < self.max_pages:
            print("-" * 20)

            # 1. Dequeue URL
            current_url = self.url_queue.popleft()

            # 2. Check if already visited
            if current_url in self.visited_urls:
                print(f"Skipping already visited URL: {current_url}")
                continue

            # 3. Check if disallowed by robots.txt rules
            parsed_url = urlparse(current_url)
            is_disallowed = False
            for route in self.disallowed_routes:
                # Use the raw string 'route' from _load_robots
                if parsed_url.path.startswith(route):
                    is_disallowed = True
                    break

            if is_disallowed:
                print(
                    f"Skipping URL '{current_url}' (Disallowed by robots.txt)")
                # Mark as visited to avoid re-queueing
                self.visited_urls.add(current_url)
                continue

            # 4. Fetch the page
            response = self._fetch_page(current_url)

            if response:
                # 5. Process successful download
                pages_fetched += 1
                self.visited_urls.add(current_url)  # Mark as visited

                # 6. Save the page
                save_info = self._save_page(current_url, response)

                # 7. Log download info
                if save_info:
                    relative_filepath, filesize = save_info
                    self._log_download_info(
                        current_url, datetime.now(), filesize, relative_filepath
                    )

                # 8. Find new links and add to queue
                self._find_relative_links(current_url, response.text)

            else:
                # 9. Handle failed download
                print(f"Failed to fetch {current_url}. Skipping.")
                # Mark as visited to avoid retrying
                self.visited_urls.add(current_url)

            # 10. Save remaining queue and continue
            self._save_queue_to_file()

            if pages_fetched % 10 == 0:
                print("\n" + "=" * 30)
                print("--- Crawler finished its work ---")
                print(f"Total pages fetched: {pages_fetched}")
                print(f"Total unique URLs visited: {len(self.visited_urls)}")
                print(
                    f"Remaining URLs in queue (saved to file): {len(self.url_queue)}")
                print("=" * 30)
