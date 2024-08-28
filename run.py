from time import sleep
from docker import from_env
from multiprocessing import Pool
from twisted.internet import reactor
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from proxy_pool.spiders.validator import Validator
from scrapy.utils.project import get_project_settings
from proxy_pool.spiders.normals_crawler import NormalsCrawler
from score_evaluator import ScoreEvaluator
from proxy_pool.settings import *


def run():
    settings = get_project_settings()
    configure_logging(settings)
    runner = CrawlerRunner(settings)
    runner.crawl(Validator)
    d = runner.join()
    d.addBoth(lambda _: reactor.stop())
    reactor.run()


evaluator = ScoreEvaluator()


def regular_score_refresh():
    # @todo: 多线程计算？
    try:
        while True:
            evaluator.update_proxies()
            sleep(PROXY_SCORE_REFRESH_CYCLE)
    except KeyboardInterrupt:
        print('Regular proxy score evaluation process has been aborted.')


def regular_useless_check():
    """ Regularly capture and handle useless proxies """
    try:
        while True:
            # @todo: useless check method
            sleep(CHECK_USELESS_CYCLE * 60)
    except KeyboardInterrupt:
        print('Regular useless proxies check has been aborted.')


from redis import StrictRedis


def t():
    server = StrictRedis()
    for proxy_url in server.zrangebyscore(PROXY_CONSECUTIVE_SUCCESS, -20, -MIN_CONSECUTIVE_SUCCESS):
        proxy = server.hget(PROXY_URL_KEY, proxy_url)
        if server.sismember(NEW_PROXIES, proxy_url):
            server.srem(NEW_PROXIES, proxy)
        else:
            server.srem(VALID_PROXIES, proxy)
            # #todo: 保存所有数据
            key_name = PROXY_LATENCY % proxy
            latency = {record[1]: float(record[0]) for record in server.zrevrange(key_name, 0, -1, withscores=True)}
            obtained_time = server.hget(PROXY_OBTAINED_TIME, proxy_url)
            last_update = server.zscore(PROXY_LAST_UPDATE_TIME, proxy_url)
            key_name = PROXY_VALIDATE_RECORDS % proxy
            records = {record[1]: eval(record[0])[0] for record in server.zrevrange(key_name, 0, -1, withscores=True)}
            proxy, proxy_url, latency, obtained_time, last_update, records
        server.zrem(PROXY_SCORE, proxy_url)
        server.hdel(PROXY_URL_KEY, proxy_url)
        server.delete(PROXY_LATENCY % proxy)
        server.hdel(PROXY_OBTAINED_TIME, proxy_url)
        server.zrem(PROXY_LAST_UPDATE_TIME, proxy_url)
        server.delete(PROXY_VALIDATE_RECORDS % proxy)
        server.zrem(PROXY_CONSECUTIVE_SUCCESS, proxy_url)


def deactivate_all_docker_containers():
    client = from_env()
    containers = client.containers.list()
    [c.stop() for c in containers]


def main():
    print('Initializing...')
    # system('docker run -d -p 80:80 kennethreitz/httpbin')  # activate httpbin
    # print('httpbin has been activated')
    pool = Pool()
    processes = [pool.apply_async(run), pool.apply_async(regular_score_refresh)]
    # processes = [pool.apply_async(t), pool.apply_async(run)]

    try:
        while True:
            sleep(0.5)
            if all([r.ready() for r in processes]):
                break
    except KeyboardInterrupt:
        pool.terminate()
        pool.join()
        print('program ended!')


if __name__ == '__main__':
    main()
    print('完成')
