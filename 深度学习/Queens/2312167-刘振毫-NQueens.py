import tkinter as tk
from tkinter import scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import math

matplotlib.rcParams['font.sans-serif'] = ['SimHei']  
matplotlib.rcParams['axes.unicode_minus'] = False  

def solve_n_queens(n):
    def search(row, col_used, diag1_used, diag2_used, solution, solutions):
        if row == n:
            solutions.append(solution.copy())
            return
        
        for col in range(n):
            d1 = row + col
            d2 = row - col + n - 1
            if not col_used[col] and not diag1_used[d1] and not diag2_used[d2]:
                solution[row] = col
                col_used[col] = diag1_used[d1] = diag2_used[d2] = True
                search(row + 1, col_used, diag1_used, diag2_used, solution, solutions)
                col_used[col] = diag1_used[d1] = diag2_used[d2] = False
    
    solutions = []
    search(0, [False]*n, [False]*(2*n-1), [False]*(2*n-1), [0]*n, solutions)
    return solutions

def draw_solution(solution, n, title=""):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_title(title, fontsize=12)
    
    for i in range(n + 1):
        ax.axvline(i, color='black', lw=1)
        ax.axhline(i, color='black', lw=1)
    
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_xticks([])
    ax.set_yticks([])
    
    for row, col in enumerate(solution):
        ax.scatter(col + 0.5, n - 0.5 - row, s=200, color='red', zorder=5)
        ax.text(col + 0.5, n - 0.5 - row, "Q", color='white', 
                ha='center', va='center', fontweight='bold')
    
    return fig

def draw_manual_board(n, queens, conflicts=None):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_title("手动放置皇后 (点击格子放置/移除皇后)", fontsize=12)
    
    for i in range(n + 1):
        ax.axvline(i, color='black', lw=1)
        ax.axhline(i, color='black', lw=1)
    
    # 标记冲突位置
    if conflicts:
        for row, col in conflicts:
            ax.add_patch(plt.Rectangle((col, n-1-row), 1, 1, 
                                     facecolor='lightcoral', alpha=0.5))  # 浅红色标记被攻击位置
    
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_xticks([])
    ax.set_yticks([])
    
    # 绘制皇后
    for row, col in queens:
        ax.scatter(col + 0.5, n - 0.5 - row, s=200, color='red', zorder=5)
        ax.text(col + 0.5, n - 0.5 - row, "Q", color='white', 
                ha='center', va='center', fontweight='bold')
    
    return fig

class NQueensApp:
    def __init__(self, root):
        self.root = root
        self.root.title("N皇后问题")
        self.solutions = []
        self.n = 8
        self.current_canvas = None
        self.current_fig = None
        self.manual_mode = False
        self.queens = []  
        self.click_handler = None  # 点击事件处理器
        
        self.setup_ui()
    
    def setup_ui(self):
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=5)
        
        tk.Label(control_frame, text="N值:").pack(side=tk.LEFT)
        self.n_entry = tk.Entry(control_frame, width=5)
        self.n_entry.pack(side=tk.LEFT, padx=5)
        self.n_entry.insert(0, "8")
        
        tk.Button(control_frame, text="求解", command=self.solve).pack(side=tk.LEFT, padx=5)
        
        tk.Label(control_frame, text="解编号:").pack(side=tk.LEFT, padx=(10, 0))
        self.slider = tk.Scale(control_frame, from_=1, to=1, orient=tk.HORIZONTAL, 
                              length=150, command=self.show_solution)
        self.slider.pack(side=tk.LEFT, padx=5)
        
        tk.Label(control_frame, text="跳转到:").pack(side=tk.LEFT, padx=(10, 0))
        self.jump_entry = tk.Entry(control_frame, width=5)
        self.jump_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="跳转", command=self.jump_to_solution).pack(side=tk.LEFT, padx=5)
        
        self.manual_button = tk.Button(control_frame, text="手动放置", command=self.toggle_manual_mode)
        self.manual_button.pack(side=tk.LEFT, padx=10)
        
        content_frame = tk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area = scrolledtext.ScrolledText(content_frame, width=40, height=15)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.plot_frame = tk.Frame(content_frame, width=400, height=400)
        self.plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    def solve(self):
        try:
            self.n = int(self.n_entry.get())
            if self.n < 4:
                self.text_area.config(state=tk.NORMAL)
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, f"N={self.n} 皇后问题无解\n")
                self.text_area.config(state=tk.DISABLED)
                self.solutions = []
                self.slider.config(from_=1, to=1)
                if self.current_canvas:
                    self.current_canvas.get_tk_widget().pack_forget()
                    self.current_canvas = None
                return
        except:
            return
        
        if self.manual_mode:
            self.toggle_manual_mode()
        
        self.solutions = solve_n_queens(self.n)
        
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, f"N={self.n} 皇后问题，共找到 {len(self.solutions)} 个解\n\n")
        
        for i, sol in enumerate(self.solutions, 1):
            self.text_area.insert(tk.END, f"解 {i}: {sol}\n")
        
        self.text_area.config(state=tk.DISABLED)
        self.slider.config(from_=1, to=len(self.solutions))
        self.slider.set(1)
        self.show_solution()
    
    def show_solution(self, event=None):
        if not self.solutions:
            return
        
        idx = self.slider.get() - 1
        solution = self.solutions[idx]
        
        if self.current_canvas:
            self.current_canvas.get_tk_widget().pack_forget()
        
        self.current_fig = draw_solution(solution, self.n, f"解 {idx + 1}")
        self.current_canvas = FigureCanvasTkAgg(self.current_fig, self.plot_frame)
        self.current_canvas.draw()
        self.current_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def jump_to_solution(self):
        if not self.solutions:
            return
            
        try:
            target = int(self.jump_entry.get())
            if 1 <= target <= len(self.solutions):
                self.slider.set(target)
                self.show_solution()
            else:
                messagebox.showerror("错误", f"解编号必须在 1 到 {len(self.solutions)} 之间")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def toggle_manual_mode(self):
        new_mode = not self.manual_mode
        if new_mode == self.manual_mode:
            return
        self.manual_mode = new_mode
        
        if self.manual_mode:
            try:
                self.n = int(self.n_entry.get())
                if self.n < 4:
                    messagebox.showwarning("警告", "N值必须大于等于4")
                    self.manual_mode = False
                    return
            except:
                messagebox.showwarning("警告", "请输入有效的N值")
                self.manual_mode = False
                return
            
            self.queens = []
            self.manual_button.config(text="退出手动", bg="lightyellow")
          #debug_msg = f"【调试】手动模式激活，当前N值：{self.n}\n"
            #print(debug_msg)
            self.text_area.config(state=tk.NORMAL)
            self.text_area.delete(1.0, tk.END)
           # self.text_area.insert(tk.END, debug_msg)
            self.text_area.config(state=tk.DISABLED)
            self.show_manual_board()
            
        else:
            self.queens = []
            self.manual_button.config(text="手动放置", bg="SystemButtonFace")
            
            if self.click_handler is not None:
                self.current_canvas.mpl_disconnect(self.click_handler)
                self.click_handler = None
            
            if self.solutions:
                self.show_solution()
            else:
                if self.current_canvas:
                    self.current_canvas.get_tk_widget().pack_forget()
                    self.current_canvas = None
    
    def show_manual_board(self):
        if self.current_canvas:
            self.current_canvas.get_tk_widget().pack_forget()
        
        # 计算冲突位置（被攻击的格子）
        conflicts = self.calculate_conflicts()
        
        self.current_fig = draw_manual_board(self.n, self.queens, conflicts)
        self.current_canvas = FigureCanvasTkAgg(self.current_fig, self.plot_frame)
        self.current_canvas.draw()
        self.current_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        if self.click_handler is not None:
            self.current_canvas.mpl_disconnect(self.click_handler)
        self.click_handler = self.current_canvas.mpl_connect('button_press_event', self.on_click)
        
      #debug_msg = "【调试】点击事件已绑定，可点击棋盘格子\n"
        #print(debug_msg)
        self.text_area.config(state=tk.NORMAL)
        #self.text_area.insert(tk.END, debug_msg)
        self.text_area.config(state=tk.DISABLED)
    
    def calculate_conflicts(self):
        """计算所有被现有皇后攻击的位置（冲突位置）"""
        conflicts = set()
        
        for row, col in self.queens:
            # 同一行
            for c in range(self.n):
                if c != col:
                    conflicts.add((row, c))
            
            # 同一列
            for r in range(self.n):
                if r != row:
                    conflicts.add((r, col))
            
            # 主对角线
            r, c = row-1, col-1
            while r >= 0 and c >= 0:
                conflicts.add((r, c))
                r -= 1
                c -= 1
                
            r, c = row+1, col+1
            while r < self.n and c < self.n:
                conflicts.add((r, c))
                r += 1
                c += 1
            
            # 副对角线
            r, c = row-1, col+1
            while r >= 0 and c < self.n:
                conflicts.add((r, c))
                r -= 1
                c += 1
                
            r, c = row+1, col-1
            while r < self.n and c >= 0:
                conflicts.add((r, c))
                r += 1
                c -= 1
        
        return conflicts
    
    def on_click(self, event):
      #debug_msg = f"\n【调试】点击事件触发：\n"
      #debug_msg += f" - 原始x坐标（event.xdata）: {event.xdata}\n"
      #debug_msg += f" - 原始y坐标（event.ydata）: {event.ydata}\n"
      #debug_msg += f" - 当前N值：{self.n}\n"
      #debug_msg += f" - 手动模式状态：{self.manual_mode}\n"
        
        if not self.manual_mode:
          #debug_msg += "【调试】未处于手动模式，忽略点击\n"
           # print(debug_msg)
            self.text_area.config(state=tk.NORMAL)
            #self.text_area.insert(tk.END, debug_msg)
            self.text_area.config(state=tk.DISABLED)
            return
        
        if event.xdata is None or event.ydata is None:
          #debug_msg += "【调试】点击位置在棋盘外，忽略操作\n"
           # print(debug_msg)
            self.text_area.config(state=tk.NORMAL)
            #self.text_area.insert(tk.END, debug_msg)
            self.text_area.config(state=tk.DISABLED)
            return
        
        # 计算行列坐标
        x_floor = math.floor(event.xdata)
        col = int(x_floor)
        y_floor = math.floor(event.ydata)
        row = (self.n - 1) - int(y_floor)
        
      #debug_msg += f"\n【调试】坐标转换过程：\n"
      #debug_msg += f" - 列（col）计算：xdata={event.xdata:.4f} floor={x_floor} 最终col={col}\n"
      #debug_msg += f" - 行（row）计算：ydata={event.ydata:.4f} floor={y_floor} 映射后row={row}\n"
        
        # 检查坐标有效性
        if not (0 <= row < self.n and 0 <= col < self.n):
          #debug_msg += f"【调试】坐标无效！row={row}（需0~{self.n-1}），col={col}（需0~{self.n-1}）\n"
           # print(debug_msg)
            self.text_area.config(state=tk.NORMAL)
           # self.text_area.insert(tk.END, debug_msg)
            self.text_area.config(state=tk.DISABLED)
            self.show_manual_board()
            return
        
        queen_pos = (row, col)
        # 计算当前冲突位置
        conflicts = self.calculate_conflicts()
        
        # 判断是否为冲突位置
        if queen_pos in conflicts:
            # 冲突位置，禁止放置
          #debug_msg += f"【调试】位置{(row, col)}被其他皇后攻击，无法放置！\n"
            messagebox.showinfo("提示", f"位置({row+1}, {col+1})被其他皇后攻击，无法放置！") 
        else:
            # 非冲突位置，正常添加/移除皇后
          #debug_msg += f"【调试】坐标有效（row={row}, col={col}），开始处理皇后\n"
            if queen_pos in self.queens:
                self.queens.remove(queen_pos)
              #debug_msg += f"【调试】移除皇后：位置{(row, col)}，当前皇后列表：{self.queens}\n"
            else:
                self.queens.append(queen_pos)
              #debug_msg += f"【调试】添加皇后：位置{(row, col)}，当前皇后列表：{self.queens}\n"
        
      #debug_msg += f"【调试】当前皇后总数：{len(self.queens)}，列表：{self.queens}\n"
        
        #print(debug_msg)
        self.text_area.config(state=tk.NORMAL)
        #self.text_area.insert(tk.END, debug_msg)
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)
        
        self.show_manual_board()

if __name__ == "__main__":
    root = tk.Tk()
    app = NQueensApp(root)
    root.geometry("900x600")
    
    def on_closing():
        plt.close('all')
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()