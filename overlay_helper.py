import os
import sys
import time
import pyautogui
import tkinter as tk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_FILE = os.path.join(BASE_DIR, 'temp_screenshot.png')

class FloatingScreenshotApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('浮动截图')
        self.root.geometry('70x70+100+100')
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.configure(bg='#4169E1')
        self.root.attributes('-alpha', 0.85)  # 85% 不透明度
        self._offset_x = 0
        self._offset_y = 0

        self.button = tk.Button(self.root, text='📷', command=self.take_screenshot,
                                bg='#4169E1', fg='white', bd=0, font=('Arial', 12), 
                                activebackground='#1E90FF', activeforeground='white', 
                                relief=tk.FLAT, padx=0, pady=0)
        self.button.place(x=1, y=1, width=70, height=70)

        self.button.bind('<ButtonPress-1>', self.start_move)
        self.button.bind('<B1-Motion>', self.on_move)

    def start_move(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def on_move(self, event):
        x = self.root.winfo_x() + event.x - self._offset_x
        y = self.root.winfo_y() + event.y - self._offset_y
        self.root.geometry(f'+{x}+{y}')

    def take_screenshot(self):
        self.root.withdraw()
        self.root.update()
        time.sleep(0.25)
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(TEMP_FILE)
            self.root.deiconify()
            self.root.lift()
            self.root.after(100, lambda: messagebox.showinfo('截图完成', '已截取整屏并保存为临时文件。'))
        except Exception as ex:
            self.root.deiconify()
            self.root.lift()
            messagebox.showerror('截图失败', str(ex))

    def close_window(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = FloatingScreenshotApp()
    app.run()
