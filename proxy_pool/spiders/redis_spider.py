from scrapy import Spider
from scrapy import signals
from scrapy_redis import connection
from scrapy.exceptions import DontCloseSpider


class RedisSpider(Spider):
    def __init__(self, **kwargs):
        super(RedisSpider, self).__init__(**kwargs)

    def setup_redis(self, crawler):
        self.server = connection.from_settings(crawler.settings)
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)

    def start_requests(self):
        return self.next_requests()

    def next_requests(self):
        """ Returns a request to be scheduled or none. """
        return

    def spider_idle(self):
        """ Schedules a request if available, otherwise waits. """
        requests = self.next_requests()
        if requests:
            for req in requests:
                self.crawler.engine.crawl(req, spider=self)
        raise DontCloseSpider
