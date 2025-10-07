# VINF-webscrapper
Simple webscrapper project using python

## Inštalácia

**Požiadavky:**
* Python 3.8+

**Inštalácia knižníc:**
```bash
pip install requests beautifulsoup4
```

# Crawler.py

## Použitie

Skript sa spúšťa z príkazového riadka. Konfigurácia a spustenie crawlera sa vykonáva v bloku `if __name__ == "__main__":` na konci súboru.

**1. Nastavenie parametrov:**
Upravte premenné `CRAWL_URL`, `SAVE_PATH` a `MAX_PAGES` podľa potreby.

**2. Spustenie skriptu:**

```bash
python crawler_class.py
```

**Príklad použitia:**

```python
if __name__ == "__main__":
    # --- Konfigurácia ---
    CRAWL_URL = "[https://gohistoric.com/world-heritage/](https://gohistoric.com/world-heritage/)"
    SAVE_PATH = os.path.join("data", "html", "gohistoric_lists")
    MAX_PAGES = 5

    # Vytvorenie inštancie a spustenie crawlera
    crawler = Crawler(base_url=CRAWL_URL, save_dir=SAVE_PATH, max_pages=MAX_PAGES)
    crawler.run()
```

-----

## Konfigurácia

Trieda `Crawler` sa inicializuje s nasledujúcimi parametrami:

  * **`base_url` (str)**: Počiatočná URL adresa, z ktorej crawler začne sťahovanie.
  * **`save_dir` (str)**: Cesta k lokálnemu adresáru, kam budú ukladané stiahnuté HTML súbory.
  * **`max_pages` (int)**: Maximálny počet stránok, ktoré má crawler stiahnuť. Slúži ako limit pre testovanie alebo čiastočné sťahovanie.

-----

## Výstup

Po úspešnom zbehnutí skript vytvorí adresárovú štruktúru a uloží do nej stiahnuté HTML súbory.

**Štruktúra výstupu:**

```
/projekt
|
|-- crawler_class.py
|-- data/
|   |-- html/
|       |-- gohistoric_lists/
|           |-- page_1.html
|           |-- page_2.html
|           |-- ...
```

```
```