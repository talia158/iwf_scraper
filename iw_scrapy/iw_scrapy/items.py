import scrapy


class PlantItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    common_name = scrapy.Field()
    scientific_name = scrapy.Field()
    sections = scrapy.Field()
    image_urls = scrapy.Field()
