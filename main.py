import os
from modules.crawler_module import Crawler

if __name__ == "__main__":

    # Configuration
    CRAWL_URL = "https://www.worldheritagesite.org"
    SAVE_PATH = os.path.join("data")

    # 1. Create an instance of the Crawler
    my_crawler = Crawler(base_url=CRAWL_URL,
                         save_dir=SAVE_PATH, max_pages=10000)

    # 2. Run the crawler
    my_crawler.run()
