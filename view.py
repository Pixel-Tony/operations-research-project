import tkinter as tk
from model import Model
import time as t

FPS = 60

class View:
    def __init__(self,
                 title: str,
                 width: int,
                 height: int,
                 center: bool,
                 model: Model
                 ) -> None:
        self._init_window(title, width, height, center)
        self._init_ui()

    def _init_window(self, title: str, width: int, height: int, center):
        root = tk.Tk()
        root.title(title)
        root.geometry(f'{width}x{height}'
                      f'+{(root.winfo_screenwidth() - width) // 2}'
                      f'+{(root.winfo_screenheight() - height) // 2}')
        self.root = root

    def _init_ui(self):
        self.labels = [
            tk.Label(self.root)
            for _ in range(4)
        ]
        pass

    def mainloop(self):
        time = t.perf_counter()
        try:
            while True:
                self.root.update()
                self.root.update_idletasks()

                second_time = t.perf_counter()
                frame_time_left = 1/FPS - (second_time - time)
                time = second_time

                if frame_time_left > 0:
                    t.sleep(frame_time_left)

        except KeyboardInterrupt:
            return

