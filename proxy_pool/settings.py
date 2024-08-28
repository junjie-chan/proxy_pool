# Scrapy settings for proxy_pool project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'proxy_pool'

SPIDER_MODULES = ['proxy_pool.spiders']
NEWSPIDER_MODULE = 'proxy_pool.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = 'proxy_pool (+http://www.yourdomain.com)'


# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'proxy_pool.middlewares.ProxyPoolSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    'proxy_pool.middlewares.ProxyPoolDownloaderMiddleware': 543,
# }

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
# ITEM_PIPELINES = {
#    'proxy_pool.pipelines.ProxyPoolPipeline': 300,
# }

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# article_sources: is_article, links_xpath, crawl_cycle(minutes), priority, initially_apply_cycle(time()+cycle at the beginning)
# API sources: scheme
NORMAL_SOURCES = {'http://www.xsdaili.cn/': {'is_article': True,
                                             'links_xpath': '//div[@class="panel-body"]//div[@class="title"]',
                                             'crawl_cycle': 24 * 60,
                                             'priority': 0},  # @todo:need update
                  }
MULTIPAGE_SOURCES = {}

#################### Common user settings ####################
DEFAULT_CYCLE_RANGE = (0.2, 1)  # minutes
DEFAULT_VALIDATE_CYCLE = 5  # minutes
PROXY_SCORE_REFRESH_CYCLE = 10  # seconds
DEFAULT_PROXY_DOWNLOAD_TIMEOUT = 20  # seconds
MAX_SCORE = 10000
PROXY_EXPIRE_CYCLE = 3  # hours
CHECK_USELESS_CYCLE = 10  # minutes
MIN_CONSECUTIVE_SUCCESS = 60 / DEFAULT_VALIDATE_CYCLE  # proxy reject criteria
#################### Common project settings ####################
HTTPPROXY_ENABLED = False
BASE_SCORE = MAX_SCORE / 7  # There are 7 indexes
URL_FOR_VALIDATE = 'http://httpbin.org/ip'
SCHEDULER = 'proxy_pool.schedulers.redis_scheduler.RedisScheduler'

# Redis keys - crawler keys
# serialized request: serialized request(after updating meta, as to_scrape_normals key). For internal communication.
NORMALS_CRAWLER_KEY = 'crawler:to_scrape_normals'
NORMALS_CRAWLER_REQUEST_KEY = 'crawler:request_vs_request_key'
# Redis keys - validator keys
NEW_PROXIES = 'validator:new_proxies'  # set, {proxy, ...}
VALID_PROXIES = 'validator:valid_proxies'  # set, {proxy, ...}
PROXY_SCORE = 'validator:proxy_score'  # zset, {proxy_url: score}
PROXY_URL_KEY = 'validator:proxy_url_key'  # hash, {proxy_url: proxy}
PROXY_OBTAINED_TIME = 'validator:proxy_obtained_time'  # hash, {proxy_url: timestamp}
PROXY_LATENCY = 'validator:proxy_latency:%s'  # zset, proxy_url: {str(latency): timestamp}
PROXY_LAST_UPDATE_TIME = 'validator:proxy_last_update_time'  # zset, {proxy_url: timestamp}
PROXY_CONSECUTIVE_SUCCESS = 'validator:proxy_consecutive_success'  # zset, {proxy_url: times}
PROXY_VALIDATE_RECORDS = 'validator:proxy_validate_records:%s'  # zset, proxy_url: {'(success/fail, timestamp)': timestamp}

# Middlewares settings
DOWNLOADER_MIDDLEWARES = {
    # Default middlewares
    'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': None,
    'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': None,
}

# Default RedisScheduler Settings
# SCHEDULER_IDLE_BEFORE_CLOSE
# SCHEDULER_QUEUE_CLASS
