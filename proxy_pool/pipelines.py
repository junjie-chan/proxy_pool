from json import dumps
from re import search, findall
from scrapy_redis import connection
from scrapy.exceptions import DropItem

# A function to extract scheme from a string
get_scheme = lambda string: findall('HTTPS?|https?|Https?', string)


class CrawlerPipeline:
    def __init__(self, crawler, server):
        self.crawler = crawler
        self.server = server
        self.new_proxies = crawler.settings.get('NEW_PROXIES')
        self.valid_proxies = crawler.settings.get('VALID_PROXIES')
        self.proxy_url_key = crawler.settings.get('PROXY_URL_KEY')
        self.proxy_last_update_time = crawler.settings.get('PROXY_LAST_UPDATE_TIME')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler=crawler, server=connection.from_settings(crawler.settings))

    def process_item(self, item, spider):
        for scheme, raw_data in item.items():
            scheme = None if scheme == 'None' else get_scheme(scheme)
            # To avoid scheme check for every row of data
            if scheme is None:
                for row in raw_data:
                    extract_scheme = get_scheme(row)
                    self._extract_proxy_details(row, extract_scheme if extract_scheme else None)
            else:
                for row in raw_data:
                    self._extract_proxy_details(row, scheme)
        return DropItem()

    def _extract_proxy_details(self, row, scheme):
        proxy = search('(\d{1,3}\.){3}\d{1,3}:\d{1,5}', row)
        if proxy:
            proxy = proxy.group()
        else:
            ip = search('(\d{1,3}\.){3}\d{1,3}', row).group()
            port = search('>\d{1,5}<', row).group()
            proxy = f'{ip}:{port}'

        # Check if the proxy already exists to decide the next action
        if self.server.sismember(self.valid_proxies, proxy) or self.server.sismember(self.new_proxies, proxy):
            return

        self._prepare_to_validate(proxy, self._construct_proxy_url(proxy, scheme))

    @staticmethod
    def _construct_proxy_url(proxy, scheme=None):
        scheme = scheme if scheme else ['http', 'https']
        return {s.lower(): f'{s.lower()}://{proxy}' for s in scheme}

    def _prepare_to_validate(self, proxy, proxy_url):
        proxy_url = dumps(proxy_url)
        self.server.sadd(self.new_proxies, proxy)
        self.server.hset(self.proxy_url_key, proxy_url, proxy)
        self.server.zadd(self.proxy_last_update_time, {proxy_url: 0})
