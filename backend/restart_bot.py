import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import time

class RestartHandler(FileSystemEventHandler):
    def __init__(self, command):
        self.command = command
        self.process = None
        self.start_bot()

    def start_bot(self):
        if self.process:
            self.process.kill()
        print("Перезапуск бота...")
        self.process = subprocess.Popen(self.command, shell=True)

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            self.start_bot()

command = "python main.py"
event_handler = RestartHandler(command)
observer = Observer()
observer.schedule(event_handler, ".", recursive=True)
observer.start()
print("Следим за изменениями в файлах...")

try:
    while True:
        time.sleep(1)
except:
    observer.stop()
    event_handler.process.kill()
observer.join()
