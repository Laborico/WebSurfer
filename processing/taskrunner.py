import threading


class TaskRunner:
    def __init__(self, tab):
        self.tab = tab
        self.tasks = []
        self.condition = threading.Condition()
        self.needs_quit = False
        self.main_thread = threading.Thread(
                target=self.run,
                name='Main Thread'
                )
        self.needs_quit = False

    def schedule_task(self, task):
        self.condition.acquire(blocking=True)
        self.tasks.append(task)
        self.condition.notify_all()
        self.condition.release()

    def run(self):
        while True:
            self.condition.acquire(blocking=True)
            needs_quit = self.needs_quit

            self.condition.release()

            if needs_quit:
                self.handle_quit()
                return

            task = None
            self.condition.acquire(blocking=True)
            if len(self.tasks) > 0:
                task = self.tasks.pop(0)
            self.condition.release()

            if task:
                task.run()

            self.condition.acquire(blocking=True)
            if len(self.tasks) == 0 and not self.needs_quit:
                self.condition.wait()
            self.condition.release()

    def start_thread(self):
        self.main_thread.start()

    def set_needs_quit(self):
        self.condition.acquire(blocking=True)
        self.needs_quit = True
        self.condition.notify_all()
        self.condition.release()

    def clear_pending_tasks(self):
        self.condition.acquire(blocking=True)
        self.tasks.clear()
        self.condition.release()

    def handle_quit(self):
        pass
