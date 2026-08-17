import random
import time
import threading
import tkinter as tk
import ctypes
from ctypes import wintypes
from pynput import keyboard

user32 = ctypes.windll.user32

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.POINTER(wintypes.ULONG)),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [('mi', MOUSEINPUT)]
    _anonymous_ = ('_input',)
    _fields_ = [
        ('type', wintypes.DWORD),
        ('_input', _INPUT),
    ]

def send_click(x, y):
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    
    nx = int(x * 65535 / screen_width)
    ny = int(y * 65535 / screen_height)
    
    inputs = (INPUT * 3)()
    
    inputs[0].type = INPUT_MOUSE
    inputs[0].mi.dx = nx
    inputs[0].mi.dy = ny
    inputs[0].mi.mouseData = 0
    inputs[0].mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    inputs[0].mi.time = 0
    inputs[0].mi.dwExtraInfo = None
    
    inputs[1].type = INPUT_MOUSE
    inputs[1].mi.dx = 0
    inputs[1].mi.dy = 0
    inputs[1].mi.mouseData = 0
    inputs[1].mi.dwFlags = MOUSEEVENTF_LEFTDOWN
    inputs[1].mi.time = 0
    inputs[1].mi.dwExtraInfo = None
    
    inputs[2].type = INPUT_MOUSE
    inputs[2].mi.dx = 0
    inputs[2].mi.dy = 0
    inputs[2].mi.mouseData = 0
    inputs[2].mi.dwFlags = MOUSEEVENTF_LEFTUP
    inputs[2].mi.time = 0
    inputs[2].mi.dwExtraInfo = None
    
    user32.SendInput(3, ctypes.byref(inputs), ctypes.sizeof(INPUT))

class DraggableDot:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'white')
        
        self.canvas = tk.Canvas(self.root, width=40, height=40, bg='white', highlightthickness=0)
        self.canvas.pack()
        
        self.dot = self.canvas.create_oval(5, 5, 35, 35, fill='red', outline='darkred', width=2)
        
        self.offset_x = 0
        self.offset_y = 0
        
        self.canvas.bind('<Button-1>', self.start_drag)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.stop_drag)
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f'+{screen_width//2}+{screen_height//2}')
        
        self.dragging = False
        
    def start_drag(self, event):
        self.dragging = True
        self.offset_x = event.x
        self.offset_y = event.y
        self.canvas.itemconfig(self.dot, fill='orange')
        
    def drag(self, event):
        x = self.root.winfo_x() + event.x - self.offset_x
        y = self.root.winfo_y() + event.y - self.offset_y
        self.root.geometry(f'+{x}+{y}')
        
    def stop_drag(self, event):
        self.dragging = False
        self.canvas.itemconfig(self.dot, fill='red')
        
    def get_position(self):
        x = self.root.winfo_x() + 20
        y = self.root.winfo_y() + 20
        return x, y
        
    def set_active(self, active):
        if active:
            self.canvas.itemconfig(self.dot, fill='green')
        else:
            self.canvas.itemconfig(self.dot, fill='red')

class AutoClicker:
    def __init__(self, dot):
        self.dot = dot
        self.running = False
        self.base_interval = 1.0
        self.random_range = 0.5
        self.thread = None
        self._stop_event = threading.Event()
        
    def set_interval(self, base, random_range):
        self.base_interval = base
        self.random_range = random_range
        
    def get_random_interval(self):
        random_delay = random.uniform(-self.random_range, self.random_range)
        return max(0.1, self.base_interval + random_delay)
    
    def _run(self):
        self.running = True
        self._stop_event.clear()
        self.dot.set_active(True)
        
        print(f"\n开始自动点击...")
        print(f"基础间隔: {self.base_interval}秒")
        print(f"随机范围: ±{self.random_range}秒")
        print(f"实际间隔: {self.base_interval - self.random_range:.2f} ~ {self.base_interval + self.random_range:.2f}秒")
        print("-" * 50)
        
        click_count = 0
        while self.running and not self._stop_event.is_set():
            if not self.dot.dragging:
                x, y = self.dot.get_position()
                send_click(x, y)
                click_count += 1
                print(f"点击次数: {click_count} - 位置: ({x}, {y})")
            
            interval = self.get_random_interval()
            
            if self._stop_event.wait(interval):
                break
            
    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.dot.set_active(False)
        print("\n自动点击已停止")
        
    def toggle(self):
        if self.running:
            self.stop()
        else:
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run)
            self.thread.daemon = False
            self.thread.start()

def main():
    print("=" * 50)
    print("自动点击器 - 可拖动圆点版 (游戏兼容)")
    print("=" * 50)
    
    print("\n请设置点击参数:")
    try:
        base_interval = float(input("请输入基础间隔时间(秒, 默认1.0): ") or "1.0")
        random_range = float(input("请输入随机范围(秒, 默认0.5): ") or "0.5")
        
        if random_range > base_interval:
            print("警告: 随机范围大于基础间隔, 已自动调整")
            random_range = base_interval * 0.9
    except ValueError:
        print("输入无效, 使用默认值")
        base_interval = 1.0
        random_range = 0.5
    
    dot = DraggableDot()
    clicker = AutoClicker(dot)
    clicker.set_interval(base_interval, random_range)
    
    print("\n" + "=" * 50)
    print("使用说明:")
    print("  1. 拖动红色圆点到要点击的位置")
    print("  2. 按 F6 开始/停止自动点击")
    print("  3. 圆点变绿表示正在点击")
    print("  4. 按 ESC 退出程序")
    print("=" * 50)
    print("\n程序已启动...")
    
    def on_press(key):
        try:
            if key == keyboard.Key.f6:
                clicker.toggle()
            elif key == keyboard.Key.esc:
                clicker.stop()
                dot.root.quit()
                return False
        except AttributeError:
            pass
        return True
    
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    
    try:
        dot.root.mainloop()
    except:
        pass
    
    clicker.stop()
    listener.stop()
    print("\n程序已退出")

if __name__ == "__main__":
    main()
