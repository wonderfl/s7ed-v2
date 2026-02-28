import time

class StopWatch:

    def __init__(self):
        self.stime = time.perf_counter()
        self.etime = self.stime
        self.elapsed = 0        

    def start(self):
        ctime = time.perf_counter()
        self.stime = ctime
        self.etime = ctime
        self.elapsed = 0

    def stop(self):
        ctime = time.perf_counter()
        self.etime = ctime
        self.elapsed = self.etime - self.stime
        return self.elapsed

    def elapsed():
        return self.elapsed