from app.collector.base import Collector


class CollectorScheduler:
    def __init__(self, collectors: list[Collector]):
        self.collectors = collectors

    async def run_once(self):
        payloads = []
        for collector in self.collectors:
            payloads.extend(await collector.collect())
        return payloads

