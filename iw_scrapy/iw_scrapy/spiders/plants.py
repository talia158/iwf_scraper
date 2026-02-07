import re
from urllib.parse import urlparse

import chardet
import scrapy
from parsel import Selector

from iw_scrapy.items import PlantItem


class PlantsSpider(scrapy.Spider):
    name = "plants"
    allowed_domains = ["illinoiswildflowers.info", "www.illinoiswildflowers.info"]
    start_urls = [
        "https://www.illinoiswildflowers.info/",
        "https://www.illinoiswildflowers.info/prairie/plant_index.htm",
        "https://www.illinoiswildflowers.info/savanna/savanna_index.htm",
        "https://www.illinoiswildflowers.info/woodland/woodland_index.htm",
        "https://www.illinoiswildflowers.info/wetland/wetland_index.htm",
        "https://www.illinoiswildflowers.info/weeds/weed_index.htm",
    ]

    plant_path_markers = ("/prairie/", "/woodland/", "/wetland/", "/weedy/", "/weeds/", "/savanna/")
    media_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
        ".ico",
        ".pdf",
        ".zip",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
    }

    def __init__(self, start_url=None, single_page=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_plant_urls = set()
        if start_url:
            self.start_urls = [start_url]
        self.single_page = str(single_page).lower() in {"1", "true", "yes"}

    def parse(self, response):
        if self.is_plant_detail_page(response.url):
            item = self.parse_plant_page(response)
            if item and item["url"] not in self.seen_plant_urls:
                self.seen_plant_urls.add(item["url"])
                yield item
            if self.single_page:
                return

        if self.single_page:
            return

        for href in response.css("a::attr(href)").getall():
            next_url = response.urljoin(href)
            if self.should_follow(next_url):
                yield response.follow(next_url, callback=self.parse)

    def should_follow(self, url):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False

        if parsed.netloc not in {"illinoiswildflowers.info", "www.illinoiswildflowers.info"}:
            return False

        path = parsed.path.lower()
        for ext in self.media_extensions:
            if path.endswith(ext):
                return False

        return True

    def is_plant_detail_page(self, url):
        parsed = urlparse(url)
        path = parsed.path.lower()
        is_html_page = path.endswith(".htm") or path.endswith(".html")
        return is_html_page and "/plantx/" in path

    def parse_plant_page(self, response):
        html_text = self.decode_body(response)
        selector = Selector(text=html_text)

        page_title = self.normalize_space(selector.css("title::text").get())

        common_name, scientific_name = self.extract_names(selector, page_title)
        sections = self.extract_sections(selector)

        image_urls = []
        for src in selector.css("img::attr(src)").getall():
            absolute = response.urljoin(src)
            if absolute.startswith(("http://", "https://")):
                image_urls.append(absolute)

        item = PlantItem()
        item["url"] = response.url
        item["title"] = page_title
        item["common_name"] = common_name
        item["scientific_name"] = scientific_name
        item["sections"] = sections
        item["image_urls"] = sorted(set(image_urls))
        return item

    def decode_body(self, response):
        preferred_encoding = response.encoding
        detected = chardet.detect(response.body)
        apparent_encoding = detected.get("encoding")

        encoding = preferred_encoding or apparent_encoding or "windows-1252"

        try:
            return response.body.decode(encoding, errors="replace")
        except LookupError:
            return response.body.decode("windows-1252", errors="replace")

    def extract_names(self, selector, page_title):
        common_name = ""
        scientific_name = ""

        # Most detail pages place names in the top centered paragraph.
        common_name = self.normalize_space(
            selector.xpath("(//p[@align='center']//b)[1]//text()").get()
            or selector.xpath("(//p[@style][contains(translate(@style, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'text-align: center')]//b)[1]//text()").get()
        )
        scientific_name = self.normalize_space(selector.xpath("(//p[@align='center']//i)[1]//text()").get())

        title_common, title_scientific = self.parse_title_names(page_title)
        if not common_name:
            common_name = title_common
        if not scientific_name:
            scientific_name = title_scientific

        if not common_name and page_title:
            common_name = page_title

        return common_name, scientific_name

    def parse_title_names(self, page_title):
        common_name = ""
        scientific_name = ""
        title_text = self.normalize_space(page_title)

        match = re.match(r"^(.*?)\s*\(([^)]+)\)", title_text)
        if match:
            common_name = self.normalize_space(match.group(1))
            scientific_name = self.normalize_space(match.group(2))
        else:
            sci_match = re.search(r"\b([A-Z][a-z]+\s+[a-z][a-z\-]+)\b", title_text)
            if sci_match:
                scientific_name = sci_match.group(1)
                common_name = self.normalize_space(title_text.replace(scientific_name, ""))

        return common_name, scientific_name

    def extract_sections(self, selector):
        container = selector.xpath("//blockquote[1]")
        if container:
            sections = self.extract_sections_from_blockquote(container[0])
            if sections:
                return sections
        return self.extract_sections_fallback(selector)

    def extract_sections_from_blockquote(self, container):
        sections = []
        current_heading = "Overview"
        current_text_parts = []

        def flush_section():
            text = self.normalize_space("\n".join(current_text_parts))
            if text:
                sections.append({"heading": current_heading, "text": text})

        def add_text(value):
            text = self.normalize_space(value)
            if text:
                current_text_parts.append(text)

        def heading_text_for(elem):
            tag = (getattr(elem, "tag", "") or "").lower()
            if tag not in {"b", "strong"}:
                return ""
            heading_text = self.normalize_space(" ".join(elem.itertext()))
            if heading_text.endswith(":") and 3 <= len(heading_text) <= 80:
                return heading_text.rstrip(":")
            return ""

        def walk(elem):
            nonlocal current_heading, current_text_parts
            heading_text = heading_text_for(elem)
            if heading_text:
                flush_section()
                current_text_parts = []
                current_heading = heading_text
                return

            add_text(getattr(elem, "text", ""))
            for child in elem:
                walk(child)
                add_text(getattr(child, "tail", ""))

        walk(container.root)

        flush_section()
        return self.dedupe_sections(sections)

    def extract_sections_fallback(self, selector):
        sections = []
        current_heading = "Overview"
        current_text_parts = []
        nodes = selector.xpath("//body//*[self::p or self::li or self::td]")

        def flush_section():
            text = self.normalize_space("\n".join(current_text_parts))
            if text:
                sections.append({"heading": current_heading, "text": text})

        for node in nodes:
            text_content = self.normalize_space(" ".join(node.xpath(".//text()").getall()))
            if not text_content:
                continue

            inline_heading = self.normalize_space(
                " ".join(node.xpath("./b[1]//text() | ./strong[1]//text()").getall())
            )
            if inline_heading.endswith(":") and len(inline_heading) <= 80:
                flush_section()
                current_text_parts = []
                current_heading = inline_heading.rstrip(":")
                remaining = self.normalize_space(text_content[len(inline_heading) :].lstrip(" :.-"))
                if remaining:
                    current_text_parts.append(remaining)
            else:
                current_text_parts.append(text_content)

        flush_section()
        return self.dedupe_sections(sections)

    @staticmethod
    def dedupe_sections(sections):
        deduped = []
        seen = set()
        for section in sections:
            key = (section["heading"], section["text"])
            if key not in seen:
                seen.add(key)
                deduped.append(section)
        return deduped

    @staticmethod
    def normalize_space(value):
        if not value:
            return ""
        value = value.replace("\r", "\n")
        value = re.sub(r"\s+", " ", value)
        return value.strip()
