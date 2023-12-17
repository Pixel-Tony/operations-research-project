import time as t

class Timer:
    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.start_ts = 0

    def __enter__(self):
        self.start_ts = t.perf_counter()

    def __exit__(self, *_):
        dur = self.delay - (t.perf_counter() - self.start_ts)
        if dur > 0:
            t.sleep(dur)