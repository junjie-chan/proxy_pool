from .redis_spider import RedisSpider
from time import time
from random import randint
from scrapy import Request
from re import finditer, sub
from scrapy_redis import picklecompat
from scrapy.linkextractors import LinkExtractor
from scrapy.utils.reqser import request_to_dict, request_from_dict


class NormalsCrawler(RedisSpider):
    name = 'normals_crawler'
    custom_settings = {'ITEM_PIPELINES': {'proxy_pool.pipelines.CrawlerPipeline': 1},
                       'DOWNLOADER_MIDDLEWARES': {'proxy_pool.middlewares.UserAgentMiddleware': 500,
                                                  'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None}}

    def __init__(self, crawler, settings, **kwargs):
        super(NormalsCrawler, self).__init__(**kwargs)
        self.crawler = crawler
        self.serializer = picklecompat
        self.normal_sources = settings.get('NORMAL_SOURCES')
        self.normals_crawler_key = settings.get('NORMALS_CRAWLER_KEY')
        self.normals_crawler_request_key = settings.get('NORMALS_CRAWLER_REQUEST_KEY')
        cycle_range = settings.get('DEFAULT_CYCLE_RANGE')
        self.default_cycle_range = (cycle_range[0] * 60, cycle_range[1] * 60)

    @classmethod
    def from_crawler(cls, crawler, **kwargs):
        instance = cls(crawler=crawler, settings=crawler.settings, **kwargs)
        instance.setup_redis(crawler)
        return instance

    def _push_request(self, url, callback, settings={}):
        request = Request(url, callback, meta=settings, priority=settings.get('priority', 0))
        key_ser_request = self.serializer.dumps(request_to_dict(request, self))
        request.meta.update({'key': key_ser_request})
        time_stamp = time() + settings.get('crawl_cycle') if settings.get('initially_apply_cycle') else time()
        value_ser_request = self.serializer.dumps(request_to_dict(request, self))
        self.server.zadd(self.normals_crawler_key, {value_ser_request: time_stamp})
        self.server.hset(self.normals_crawler_request_key, key_ser_request, value_ser_request)
        print('page pushed!')

    def _update_request(self, response):
        crawl_cycle = response.meta.get('crawl_cycle', self._get_random_cycle())
        request = self.server.hget(self.normals_crawler_request_key, response.meta.get('key'))
        next_crawl = {request: time() + crawl_cycle * 60 + randint(5, 15)}
        self.server.zadd(self.normals_crawler_key, next_crawl)
        print('page updated')

    def _remove_request(self, response):
        zkey = self.server.hget(self.normals_crawler_request_key, response.meta.get('key'))
        self.server.zrem(self.normals_crawler_key, zkey)
        self.server.hdel(self.normals_crawler_request_key, response.meta.get('key'))

    def _get_random_cycle(self):
        return randint(*self.default_cycle_range)

    def _initialize_scrape_queue(self):
        for source, settings in self.normal_sources.items():
            # 初始化多文章代理源
            if settings.get('is_article'):
                self._push_request(source, self._extract_article_urls, settings)
                print('index initialized!')

    def start_requests(self):
        # @todo: 初始化条件
        self._initialize_scrape_queue()
        print('start jump to next_requests')
        return self.next_requests()

    def next_requests(self):
        for url in self.server.zrangebyscore(self.normals_crawler_key, 0, time()):
            print(f'crawling page {url}...')
            yield request_from_dict(self.serializer.loads(url), self)

    def _extract_article_urls(self, response):
        self._update_request(response)
        links = LinkExtractor(restrict_xpaths=response.meta.get('links_xpath')).extract_links(response)
        # 每个一次性url访问间隔为默认访问周期的5倍以保证不会出现短时间内频繁访问
        for i in range(len(links)):
            response.meta.update({'initially_apply_cycle': True,
                                  'crawl_cycle': self._get_random_cycle() * 5 * (i + 1)})
            self._push_request(links[i].url, self._parse_article, response.meta)
        print('parsed article urls')

    def _parse_article(self, response):
        self._remove_request(response)
        self.parse(response)

    def parse(self, response, **kwargs):
        print(response)
        return {}
        # 净化HTML源码 (防止标签中重复出现要爬取的信息)
        # text = sub('(<[^>]*>)|([ \n\t\r])', '<>', response.text)
        # rule = '((\d{1,3}\.){3}\d{1,3})(:|[\s\S]{0,50})\d{1,5}([\s\S]{0,150}(HTTPS?|https?|Https?))?'
        # return {response.meta.get('scheme', 'None'): [i.group() for i in finditer(rule, text)]}  # Raw data
        # @todo: 考虑情况：接口传入scheme
        # @todo: def construct_proxy_url, HttpbinValidator(校验器)
