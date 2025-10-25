import csv
import re
from pathlib import Path
from typing import List, Dict


class Extractor:

    def __init__(self, html_dir: str, output_csv_path: str, base_domain: str):
        self.html_dir = Path(html_dir)
        self.output_csv_path = Path(output_csv_path)
        self.base_domain = base_domain.rstrip('/')

        # Define regex patterns for extraction
        # (re.DOTALL allows '.' to match newlines)
        self.patterns = {
            "name": re.compile(r"(?:<h1 class=\"primary_title\">)(.+)(?:<\/h1>)"),
            "full_name": re.compile(r"<title>(.*?)</title>"),
            "votes": re.compile(r"(?:<div class=\"site-rating\")(?:.+data-votes=\")(.*?)(?:\".*?>)"),
            "whs_rating": re.compile(r"(?:<div class=\"site-rating\")(?:.+data-rating=\")(.*?)(?:\".*?>)"),
            "average_rating": re.compile(r"(?:<div class=\"site-rating\")(?:.+data-average=\")(.*?)(?:\".*?>)"),
            "description": re.compile(r"(?:<div class=\"intro-text text-lead\">)(.*)(?:<\/div)"),

        }

        # Ensure output directory exists
        self.output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    def _traverse_files(self):
        print(f"Starting traversal of '{self.html_dir}'...")
        # Use rglob to recursively find all 'index.html' files
        for file_path in self.html_dir.rglob('index.html'):
            yield file_path

    def _path_to_url(self, file_path: Path) -> str:
        """
        Converts a local file path back into its corresponding website URL.

        e.g., 'data/html_output/list/coloseum/index.html' 
        -> 'https://domain.com/list/coloseum'

        e.g., 'data/html_output/index.html' 
        -> 'https://domain.com/'

        Args:
            file_path (Path): The Path object for the 'index.html' file.

        Returns:
            str: The fully qualified URL.
        """
        # Get the path relative to the base HTML directory
        relative_path = file_path.relative_to(self.html_dir)

        # Get the parent directory of 'index.html' (e.g., 'list/coloseum')
        url_path = str(relative_path.parent)

        # Handle Windows vs. Linux paths
        url_path = url_path.replace('\\', '/')

        # Handle the root directory case
        if url_path == '.':
            url_path = ''

        return f"{self.base_domain}/{url_path}"

    def _extract_data_from_html(self, html_content: str) -> Dict[str, str]:

        extracted = {}
        for key, pattern in self.patterns.items():
            match = pattern.search(html_content)
            if match:
                # Get the first captured group and clean up whitespace
                data = match.group(1).strip()
                # Further clean up by removing internal newlines/tabs
                data = re.sub(r'\s+', ' ', data)
                extracted[key] = data
            else:
                extracted[key] = ""  # Return empty string if not found

        return extracted

    def _write_to_csv(self, all_data: List[Dict[str, str]]):
        """
        Writes the list of extracted data dictionaries to the output CSV file.

        Args:
            all_data (List[Dict[str, str]]): A list where each item is a
                                             dictionary of extracted data.
        """
        if not all_data:
            print("No data extracted. CSV file will not be created.")
            return

        # Define headers based on the keys of the first item
        # Ensure 'url' is the first column
        headers = ['url'] + [key for key in all_data[0].keys() if key != 'url']

        try:
            with open(self.output_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(all_data)
            print(
                f"\nSuccessfully saved extracted data to '{self.output_csv_path}'")
        except IOError as e:
            print(f"Error writing CSV file: {e}")

    def run(self):
        """
        Orchestrates the full extraction process:
        1. Traverses files.
        2. Converts paths to URLs.
        3. Reads HTML content.
        4. Extracts data.
        5. Saves all data to a single CSV.
        """
        all_extracted_data = []
        file_count = 0

        for file_path in self._traverse_files():
            file_count += 1
            print(f"Processing: {file_path}")

            # 1. Convert path to URL
            url = self._path_to_url(file_path)

            # 2. Read HTML content
            try:
                html_content = file_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"  -> Error reading file: {e}. Skipping.")
                continue

            # 3. Extract data
            data = self._extract_data_from_html(html_content)

            # 4. Add the URL
            data['url'] = url

            all_extracted_data.append(data)

        print(f"\nTraversal complete. Processed {file_count} files.")

        # 5. Write all data to CSV
        self._write_to_csv(all_extracted_data)


# --- Main execution block ---
# This allows the script to be run directly from the command line
if __name__ == "__main__":

    # --- Configuration ---
    # The directory where the Crawler saved its 'html_output'
    HTML_SOURCE_DIR = "data/html_output"

    # The domain you crawled (from your Crawler's base_url)
    BASE_DOMAIN = "https://www.worldheritagesite.org"

    # The final CSV file
    OUTPUT_CSV = "data/extracted_data.csv"

    # ---------------------

    print("--- Starting Extractor ---")

    # 1. Create an instance of the Extractor
    extractor = Extractor(
        html_dir=HTML_SOURCE_DIR,
        output_csv_path=OUTPUT_CSV,
        base_domain=BASE_DOMAIN
    )

    # 2. Run the extraction process
    extractor.run()

    print("--- Extractor finished. ---")
