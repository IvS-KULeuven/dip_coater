import threading
import asyncio


class StoppableThreadTimer:
    def __init__(self, interval, function):
        self.interval = interval  # time in seconds between calls
        self.function = function  # function to call
        self.timer = None

    def _run(self):
        self.function()
        self.start()  # reschedule the timer

    def start(self):
        if self.timer is not None:
            self.stop()  # ensure no previous timer is running
        self.timer = threading.Timer(self.interval, self._run)
        self.timer.start()

    def stop(self):
        if self.timer is not None:
            self.timer.cancel()  # stop the timer
            self.timer = None


class AsyncioStoppableTimer:
    def __init__(self, interval, coro, loop=None):
        self.interval = interval  # time in seconds between calls
        self.coro = coro  # asyncio coroutine to call
        self.loop = loop or asyncio.get_event_loop()
        self.task = None

    async def _run(self):
        while True:
            await asyncio.sleep(self.interval)
            await self.coro()  # execute the coroutine

    def start(self):
        if self.task is None:
            self.task = asyncio.ensure_future(self._run(), loop=self.loop)

    def stop(self):
        if self.task is not None:
            self.task.cancel()
            self.task = None