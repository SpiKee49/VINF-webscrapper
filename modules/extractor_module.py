import csv
import os
import re
from pathlib import Path
from typing import List, Dict


class Extractor:

    def __init__(self, downloaded_history: str, data_dir: str, output_csv_path: str):
        self.downloaded_history = Path(downloaded_history)
        self.data_dir = Path(data_dir)
        self.output_csv_path = Path(output_csv_path)

        # Define regex patterns for extraction
        self.patterns = {
            "name": re.compile(r"(?:<h1 class=\"primary_title\">)(.+)(?:<\/h1>)"),
            "full_name": re.compile(r"<dt.*>Full Name<\/dt>\s*<dd.*>\s*(.*?)\s*<small>"),
            "votes": re.compile(r"(?:<div class=\"site-rating\")(?:.+data-votes=\")(.*?)(?:\".*?>)"),
            "whs_rating": re.compile(r"(?:<div class=\"site-rating\")(?:.+data-rating=\")(.*?)(?:\".*?>)"),
            "average_rating": re.compile(r"(?:<div class=\"site-rating\")(?:.+data-average=\")(.*?)(?:\".*?>)"),
            "description": re.compile(r"(?:<div class=\"intro-text text-lead\">)((.|\s)*?)(?:\s*<\/div)"),
            "contry": re.compile(r"<dt.*>\s*(?:Country|Countries)\s*<\/dt>\s*<dd .*>(?:\s*?(?:<a.*?>)(.+)<\/a>)*(?:\s*<\/dd>)"),
            "status": re.compile(r"<dt.*>\s*Status\s*<\/dt>\s*<dd .*>\s*(.*)\s*<span"),
            "type": re.compile(r"<dt.*>\s*Type\s*<\/dt>\s*<dd.*>\s*(.*)\s*<i"),
        }

        # Ensure output directory exists
        self.output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    def _extract_data_from_html(self, html_content: str) -> Dict[str, str]:

        extracted = {}
        for key, pattern in self.patterns.items():
            match = pattern.search(html_content)
            if match:
                # Get the first captured group and clean up whitespace
                data = match.group(1).strip()

                if key == 'description':
                    # Source: https://stackoverflow.com/a/4869782
                    data = re.sub('<[^<]+?>', '', data)
                extracted[key] = data
            else:
                extracted[key] = ""  # Return empty string if not found

        return extracted

    def _write_to_csv(self, all_data: List[Dict[str, str]]):

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
        all_extracted_data = []
        file_count = 0
        file_path = ''

        with open(self.downloaded_history, 'r', encoding='utf-8') as downloaded_data:

            # row = {url,downloaded_at,filesize_bytes,filepath_saved}
            for row in csv.reader(downloaded_data):
                url = row[0]
                file_path = row[3]

                is_mathing = re.match(re.compile(
                    r"^(list|tentative|former-tentative|in-danger).+\/index.html"), file_path)

                if url == 'url' or not is_mathing:
                    continue

                try:
                    html_content = Path(os.path.join(
                        self.data_dir, file_path)).read_text(encoding='utf-8')
                except Exception as e:
                    print(f"  -> Error reading file: {e}. Skipping.")
                    continue

                data = self._extract_data_from_html(html_content)
                data['url'] = url

                all_extracted_data.append(data)

                file_count += 1

        print(f"\nTraversal complete. Extracted data from {file_count} files.")

        # Write all data to CSV
        self._write_to_csv(all_extracted_data)


# --- Main execution block ---
# This allows the script to be run directly from the command line
if __name__ == "__main__":

    HTML_SOURCE_DIR = "data/html_output"
    DOWNLOAD_LOG_FILE = "data/download_log.csv"
    OUTPUT_CSV = "data/extracted_data.csv"

    print("[i] Starting Extractor")

    # 1. Create an instance of the Extractor
    extractor = Extractor(
        downloaded_history=DOWNLOAD_LOG_FILE,
        data_dir=HTML_SOURCE_DIR,
        output_csv_path=OUTPUT_CSV,
    )

    # 2. Run the extraction process
    extractor.run()

    print("--- Extractor finished. ---")
