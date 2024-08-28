from time import time
from numpy import mean, std
from redis import StrictRedis
from proxy_pool.settings import *
from scrapy_redis import connection


class ScoreEvaluator(object):
    def __init__(self, server=None, crawler=None):
        if server:
            self.server = server
        elif not server and crawler:
            self.server = connection.from_settings(crawler.settings)
        else:
            self.server = StrictRedis()

    def update_proxies(self):
        import threading
        # @todo: 多线程
        if self.server.zcard(PROXY_LAST_UPDATE_TIME):
            for proxy_url in (item[0] for item in self.server.zscan_iter(PROXY_LAST_UPDATE_TIME)):
                ip_port = self.server.hget(PROXY_URL_KEY, proxy_url).decode('utf-8')
                self.update_single_proxy(proxy_url, ip_port, time())

    def update_single_proxy(self, proxy_url, ip_port, timestamp):
        print('计算分数中...')
        # Preparations
        key_name = PROXY_VALIDATE_RECORDS % ip_port
        expire_cycle = PROXY_EXPIRE_CYCLE * 60
        min_criteria = timestamp - expire_cycle * 60
        record_list = self.server.zrangebyscore(key_name, min_criteria, timestamp, withscores=True)

        # 处理仍未进行第一次检测的新代理
        if not record_list:
            return self.server.zadd(PROXY_SCORE, {proxy_url: 0})

        record_list.reverse()
        records = [eval(record[0])[0] for record in record_list]

        # Calculations
        consecutive_success, confidence, success_rate = self._cal_record_related(proxy_url, records)
        survival_time = self._cal_survival_time(proxy_url, record_list, records, expire_cycle)
        last_update = self._cal_last_update(proxy_url, timestamp)
        speed, stability = self._cal_latencies(ip_port, min_criteria, timestamp)
        proxy_score = sum([consecutive_success, confidence, success_rate, survival_time, last_update, speed, stability])

        self.server.zadd(PROXY_SCORE, {proxy_url: proxy_score})
        print(
            f'######scores: \nconsecutive_success={consecutive_success}\nconfidence={confidence}\nsuccess_rate={success_rate}\nsurvival_time={survival_time}\nlast_update={last_update}\nspeed={speed}\nstability={stability}\nscore={proxy_score}')

    def _cal_record_related(self, proxy_url, records):
        """ Calculate score for record-related indexes """
        max_value = PROXY_EXPIRE_CYCLE * 60 / DEFAULT_VALIDATE_CYCLE
        consecutive_success = self._cal_consecutive_success(records, proxy_url) / max_value * BASE_SCORE
        confidence = len(records) / max_value * BASE_SCORE
        success_rate = records.count(1) / len(records) * BASE_SCORE
        return consecutive_success, confidence, success_rate

    def _cal_survival_time(self, proxy_url, record_list, records, expire_cycle):
        """ Calculate score for survival time """
        obtained_time = self.server.hget(PROXY_OBTAINED_TIME, proxy_url)
        if obtained_time:
            # Latest success timestamp - earliest success timestamp
            survival_time = (record_list[records.index(1)][1] - float(obtained_time)) / 60
            survival_time = survival_time if survival_time < expire_cycle else expire_cycle
            return survival_time / expire_cycle * BASE_SCORE
        return 0

    def _cal_last_update(self, proxy_url, timestamp):
        """ Calculate score for last update time """
        expire_cycle = DEFAULT_VALIDATE_CYCLE * 60
        last_update = (timestamp - self.server.zscore(PROXY_LAST_UPDATE_TIME, proxy_url))
        last_update = last_update if last_update <= expire_cycle else expire_cycle
        return (1 - last_update / expire_cycle) * BASE_SCORE

    def _cal_latencies(self, ip_port, min_criteria, timestamp):
        """ Calculate score for latencies """
        key_name = PROXY_LATENCY % ip_port
        latencies = [float(latency) for latency in self.server.zrangebyscore(key_name, min_criteria, timestamp)]
        if latencies:
            speed = (1 - mean(latencies) / DEFAULT_PROXY_DOWNLOAD_TIMEOUT) * BASE_SCORE
            stability = (1 - std(latencies) / (DEFAULT_PROXY_DOWNLOAD_TIMEOUT / 2)) * BASE_SCORE
            return speed, stability
        return 0, 0

    def _cal_consecutive_success(self, records, proxy_url):
        consecutive_success = 0
        # 最近一次检测是成功的
        if records[0]:
            for record in records:
                if record:
                    consecutive_success += 1
                else:
                    break
        else:
            for record in records:
                if not record:
                    consecutive_success -= 1
                else:
                    break
        self.server.zadd(PROXY_CONSECUTIVE_SUCCESS, {proxy_url: consecutive_success})
        return consecutive_success
