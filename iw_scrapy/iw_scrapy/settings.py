BOT_NAME = "iw_scrapy"

SPIDER_MODULES = ["iw_scrapy.spiders"]
NEWSPIDER_MODULE = "iw_scrapy.spiders"

ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 1.5
CONCURRENT_REQUESTS = 1
COOKIES_ENABLED = False

USER_AGENT = (
    "iw-scrapy-bot/1.0 (+https://www.illinoiswildflowers.info; "
    "educational crawl for plant metadata)"
)

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.5
AUTOTHROTTLE_MAX_DELAY = 15
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

FEEDS = {
    "/data/plants.jsonl": {
        "format": "jsonlines",
        "encoding": "utf-8",
        "store_empty": False,
        "overwrite": True,
    }
}

LOG_LEVEL = "INFO"
