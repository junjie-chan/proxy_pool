from scrapy import Request
from .redis_spider import RedisSpider
from time import time
from json import dumps


class Validator(RedisSpider):
    name = 'validator'
    custom_settings = {  # 'HTTPPROXY_ENABLED': True,
        'DOWNLOADER_MIDDLEWARES': {'proxy_pool.middlewares.UserAgentMiddleware': 500,
                                   'proxy_pool.middlewares.RequestHandlerMiddleware': 550,
                                   # Default middlewares
                                   'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
                                   'scrapy.downloadermiddlewares.retry.RetryMiddleware': None}}

    # 'scrapy.downloadermiddlewares.ajaxcrawl.AjaxCrawlMiddleware': None,
    # 'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': None,
    # 'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None}}

    def __init__(self, crawler, **kwargs):
        super(Validator, self).__init__(**kwargs)
        self.crawler = crawler
        self._initialize_variables()

    def _initialize_variables(self):
        var_names = ['NEW_PROXIES', 'PROXY_SCORE', 'VALID_PROXIES', 'PROXY_URL_KEY', 'DEFAULT_PROXY_DOWNLOAD_TIMEOUT',
                     'PROXY_LATENCY', 'PROXY_OBTAINED_TIME', 'PROXY_LAST_UPDATE_TIME', 'PROXY_CONSECUTIVE_SUCCESS',
                     'URL_FOR_VALIDATE', 'DEFAULT_VALIDATE_CYCLE', 'PROXY_VALIDATE_RECORDS']
        for var_name in var_names:
            exec(f"self.{var_name.lower()} = self.crawler.settings.get('{var_name}')")

    @classmethod
    def from_crawler(cls, crawler, **kwargs):
        instance = cls(crawler=crawler, **kwargs)
        instance.setup_redis(crawler)
        return instance

    def start_requests(self):  # todo:测试完后删除！！
        proxy = '47.106.162.218:8080'
        proxy_url = dumps({'http': f'http://{proxy}'})
        self.server.sadd(self.new_proxies, proxy)
        self.server.hset(self.proxy_url_key, proxy_url, proxy)
        self.server.zadd(self.proxy_last_update_time, {proxy_url: 0})
        return self.next_requests()

    def next_requests(self):
        print('next requests working')
        # 先检测新获取的代理, 然后在检测旧的
        urls_1 = self.server.zrangebyscore(self.proxy_last_update_time, 0, 0)
        urls_2 = self.server.zrangebyscore(self.proxy_last_update_time, 1, time() - self.default_validate_cycle * 60)
        requests_1 = self._validate_urls(urls_1, self.validate_new_proxies)
        requests_2 = self._validate_urls(urls_2, self.validate_proxies)
        for requests in [requests_1, requests_2]:
            yield from requests

    def _validate_urls(self, urls, callback):
        if urls:
            for url in urls:
                meta = {'timeout': self.default_proxy_download_timeout, 'proxy': url}
                yield Request(self.url_for_validate, meta=meta, callback=callback)

    def validate_new_proxies(self, response):
        print('validate new proxies...')
        if response.meta.get('result'):
            proxy_url, ip_port = self._get_proxy_details(response)
            self.server.hset(self.proxy_obtained_time, proxy_url, time())
            self.server.sadd(self.valid_proxies, ip_port)
            self.server.srem(self.new_proxies, ip_port)
        print('jump to validate proxies...')
        self.validate_proxies(response)

    def validate_proxies(self, response):
        timestamp = time()
        result = response.meta.get('result')
        proxy_url, ip_port = self._get_proxy_details(response)

        if result == -1:
            return self.reject_proxy(proxy_url, ip_port)

        # 代理连接成功
        if result:
            # 代理为高匿
            if result == ip_port.split(':')[0]:
                self.server.zadd(self.proxy_latency % ip_port, {str(response.meta.get('latency')): timestamp})
                status = 1
            else:
                return self.reject_proxy(proxy_url, ip_port)
        # 代理连接失败
        else:
            status = 0
        self.server.zadd(self.proxy_last_update_time, {proxy_url: timestamp})
        self.server.zadd(self.proxy_validate_records % ip_port, {f'({status}, {timestamp})': timestamp})
        print('完成！！')

    def _get_proxy_details(self, response):
        proxy_url = response.meta.get('proxy')
        return proxy_url, self.server.hget(self.proxy_url_key, proxy_url).decode('utf-8')

    def reject_proxy(self, proxy_url, ip_port):
        proxy = self.server.hget(self.proxy_url_key, proxy_url)
        self.server.srem(self.new_proxies, proxy)
        self.server.srem(self.valid_proxies, proxy)
        self.server.zrem(self.proxy_score, proxy_url)
        self.server.hdel(self.proxy_url_key, proxy_url)
        self.server.delete(self.proxy_latency % ip_port)
        self.server.hdel(self.proxy_obtained_time, proxy_url)
        self.server.zrem(self.proxy_last_update_time, proxy_url)
        self.server.delete(self.proxy_validate_records % ip_port)
        self.server.zrem(self.proxy_consecutive_success, proxy_url)
        print(f'Proxy {proxy} is not elite, rejected from queue.')
