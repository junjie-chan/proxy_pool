from scrapy_redis import connection
from scrapy.utils.misc import load_object


class RedisScheduler(object):
    """ Redis-based scheduler.

        Settings:
        ---------
        SCHEDULER_IDLE_BEFORE_CLOSE : int (default: 0)
            How many seconds to wait before closing if no message is received.
        SCHEDULER_QUEUE_CLASS : str (default: 'scrapy_redis.queue.PriorityQueue')
            Scheduler queue class.
        """

    def __init__(self, server, idle_before_close=0):
        """ Initialize scheduler.

            :param server (Redis): The redis server instance.
            :param idle_before_close (int) Timeout before giving up.
        """
        if idle_before_close < 0:
            raise TypeError("idle_before_close cannot be negative")

        self.stats = None
        self.server = server
        self.idle_before_close = idle_before_close
        self.queue_cls = 'scrapy_redis.queue.PriorityQueue'

    def __len__(self):
        return len(self.queue)

    @classmethod
    def from_settings(cls, settings):
        kwargs = {'idle_before_close': settings.getint('SCHEDULER_IDLE_BEFORE_CLOSE')}

        # If the SCHEDULER_QUEUE_CLASS is missing, use defaults
        value = settings.get('SCHEDULER_QUEUE_CLASS')
        if value:
            kwargs['queue_cls'] = value

        server = connection.from_settings(settings)
        return cls(server=server, **kwargs)

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls.from_settings(crawler.settings)
        instance.stats = crawler.stats
        return instance

    def open(self, spider):
        self.spider = spider
        try:
            self.queue = load_object(self.queue_cls)(self.server, spider, f'{spider.name}:requests')
        except TypeError as e:
            raise ValueError("Failed to instantiate queue class '%s': %s", self.queue_cls, e)

    def close(self, reason):
        pass

    def enqueue_request(self, request):
        if self.stats:
            self.stats.inc_value('scheduler/enqueued/redis', spider=self.spider)
        self.queue.push(request)
        return True

    def next_request(self):
        block_pop_timeout = self.idle_before_close
        request = self.queue.pop(block_pop_timeout)
        if request and self.stats:
            self.stats.inc_value('scheduler/dequeued/redis', spider=self.spider)
        return request

    def has_pending_requests(self):
        return len(self) > 0
