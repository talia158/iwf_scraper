# IWF Scraper

IWF Scraper is a containerized Scrapy project for crawling IWF plant detail pages and exporting structured JSONL data.

- **Crawler**: Python 3 + Scrapy  
- **Output**: JSON Lines (`plants.jsonl`)  
- **Infrastructure**: Docker

---

## Prerequisites

- **Docker Desktop** (or Docker Engine)

---

## Installation / Run

```bash
git clone https://github.com/talia158/iwf_scraper.git
cd iwf_scraper/iw_scrapy
mkdir -p data
docker build -t iw-scrapy .
docker run --rm -v $(pwd)/data:/data iw-scrapy
```

Output file:

```bash
iwf_scraper/iw_scrapy/data/plants.jsonl
```

---

## One-Page Test

```bash
cd iwf_scraper/iw_scrapy
docker run --rm -v $(pwd)/data:/data iw-scrapy \
  scrapy crawl plants \
  -a start_url='https://www.illinoiswildflowers.info/prairie/plantx/pf_foxglovex.htm' \
  -a single_page=1 \
  -O /data/plants_one.jsonl
```

---

## Notes

- The spider emits plant detail pages under `/plantx/`.
- No images are downloaded; only `image_urls` are stored.
- Output is written to `/data` inside the container (mounted from host).
