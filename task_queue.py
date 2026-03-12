
import queue
import threading

class TaskQueue:

    def __init__(self):
        self.q = queue.Queue()

    def submit(self, task):
        self.q.put(task)

    def get(self):
        return self.q.get()

    def task_done(self):
        self.q.task_done()


class Worker(threading.Thread):

    def __init__(self, name, task_queue, handler):
        super().__init__(daemon=True)
        self.name = name
        self.task_queue = task_queue
        self.handler = handler

    def run(self):

        while True:

            task = self.task_queue.get()

            try:
                self.handler(task)

            except Exception as e:
                print(f"[WORKER ERROR] {self.name}: {e}")

            self.task_queue.task_done()
