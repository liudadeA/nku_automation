import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ==================== 画布初始化 ====================
fig, ax = plt.subplots(figsize=(14, 10), dpi=120)
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.set_axis_off()
fig.patch.set_facecolor('white')

# ==================== 工具函数 ====================
def draw_box(x, y, w, h, label, fontsize=12, linestyle='-'):
    """绘制矩形模块：白底黑边，文字居中加粗"""
    rect = patches.Rectangle(
        (x, y), w, h,
        edgecolor='black', facecolor='white',
        linewidth=1.2, linestyle=linestyle
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, label,
            ha='center', va='center',
            fontsize=fontsize, fontfamily='SimHei', fontweight='bold')


def draw_arrow(start, end, label=None, linestyle='-', fontsize=9, label_offset=(0, 0.15)):
    """绘制单向箭头"""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='->', linestyle=linestyle,
                                color='black', linewidth=1.1))
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=fontsize, fontfamily='SimHei',
                bbox=dict(facecolor='white', edgecolor='none', pad=1))


def draw_double_arrow(start, end, label=None, fontsize=9, label_offset=(0, 0.15)):
    """绘制双向箭头"""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='<->', color='black', linewidth=1.1))
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=fontsize, fontfamily='SimHei',
                bbox=dict(facecolor='white', edgecolor='none', pad=1))


# ==================== 模块坐标定义 ====================
# 严格网格：4行 × 3列，所有方框同行同高、同列对齐
#
#          |  Col1(左侧)   |   Col2(中间)    |  Col3(右侧)   |
# Row1(顶) |               |   定位模块(GPS) |   近端设备    |
# Row2     |  加速度传感器  |                 |   蓝牙(BT)    |
# Row3     |  数据采集模块  |                 |   远距离通信   |
# Row4(底) |               |   存储模块(SD)  |   远端服务器   |

# ---- 行坐标（每行统一高度，行间留间隙） ----
R1_Y, ROW_H = 7.2, 0.8       # 顶部行
R2_Y           = 5.9         # 第二行
R3_Y           = 4.55        # 第三行
R4_Y           = 3.15        # 底部行

# ---- 列坐标（统一宽度，居中对齐） ----
C1_X, C1_W = 1.8, 2.4      # 左列（右移缩短SPI箭头）
C2_X, C2_W = 5.2, 3.2       # 中列（较宽，容纳主控）
C3_X, C3_W = 9.2, 2.8       # 右列

# ---- 各模块坐标（按网格定位） ----
# 主控单元（跨 Row2+Row3，居中列）
MCU_X, MCU_Y, MCU_W, MCU_H = C2_X, R3_Y, C2_W, (R2_Y + ROW_H) - R3_Y
# 实时时钟（主控内部底部）
RTC_X, RTC_Y, RTC_W, RTC_H = C2_X + 0.55, MCU_Y + 0.12, 2.1, 0.55
# 定位模块（Row1, Col2）
GPS_X, GPS_Y, GPS_W, GPS_H = C2_X, R1_Y, C2_W, ROW_H
# 加速度传感器（Row2, Col1）
ACC_X, ACC_Y, ACC_W, ACC_H = C1_X, R2_Y, C1_W, ROW_H
# 数据采集模块（Row3, Col1）—— SPI箭头拉长到3倍
DAC_X, DAC_Y, DAC_W, DAC_H = C1_X, R3_Y, C1_W, ROW_H
# 存储模块（Row4, Col2）
SD_X, SD_Y, SD_W, SD_H = C2_X, R4_Y, C2_W, ROW_H
# 蓝牙（Row2, Col3）
BT_X, BT_Y, BT_W, BT_H = C3_X, R2_Y, C3_W, ROW_H
# 近端设备（Row1, Col3）
NEAR_X, NEAR_Y, NEAR_W, NEAR_H = C3_X, R1_Y, C3_W, ROW_H
# 远距离通信（Row3, Col3）
LR_X, LR_Y, LR_W, LR_H = C3_X, R3_Y, C3_W, ROW_H
# 远端服务器（Row4, Col3）
SRV_X, SRV_Y, SRV_W, SRV_H = C3_X, R4_Y, C3_W, ROW_H

# ==================== 绘制所有模块 ====================
# 主控单元（文字偏上加粗，给 RTC 留出底部空间）
rect = patches.Rectangle(
    (MCU_X, MCU_Y), MCU_W, MCU_H,
    edgecolor='black', facecolor='white', linewidth=1.2
)
ax.add_patch(rect)
ax.text(MCU_X + MCU_W / 2, MCU_Y + MCU_H * 0.7, '主控单元\n',
        ha='center', va='center', fontsize=14, fontfamily='SimHei', fontweight='bold')
# 实时时钟（主控内部小方框）
draw_box(RTC_X, RTC_Y, RTC_W, RTC_H, '实时时钟\n', fontsize=10)
# 定位模块
draw_box(GPS_X, GPS_Y, GPS_W, GPS_H, '定位模块\n', fontsize=12)
# 加速度传感器
draw_box(ACC_X, ACC_Y, ACC_W, ACC_H, '加速度传感器', fontsize=12)
# 数据采集模块
draw_box(DAC_X, DAC_Y, DAC_W, DAC_H, '数据采集模块', fontsize=12)
# 存储模块
draw_box(SD_X, SD_Y, SD_W, SD_H, '存储模块\n', fontsize=12)
# 第一通信单元（蓝牙）
draw_box(BT_X, BT_Y, BT_W, BT_H, '第一通信单元\n', fontsize=11)
# 近端设备（虚线框表示外部设备）
draw_box(NEAR_X, NEAR_Y, NEAR_W, NEAR_H, '近端设备', fontsize=12, linestyle='--')
# 第二通信单元（远距离低功耗）
draw_box(LR_X, LR_Y, LR_W, LR_H, '第二通信单元\n', fontsize=10)
# 远端服务器（虚线框表示外部设备）
draw_box(SRV_X, SRV_Y, SRV_W, SRV_H, '远端服务器', fontsize=12, linestyle='--')

# ==================== 绘制连接线与接口标注 ====================
# ---- 顶部：定位模块 → 主控单元（UART 单向） ----
draw_arrow((C2_X + C2_W / 2, GPS_Y), (C2_X + C2_W / 2, MCU_Y + MCU_H),
           label='UART', label_offset=(-0.5, 0))

# ---- 左侧：加速度传感器 → 数据采集模块（模拟信号，垂直向下，同行对齐） ----
draw_arrow((C1_X + C1_W / 2, ACC_Y), (C1_X + C1_W / 2, DAC_Y + ROW_H),
           label='模拟信号', label_offset=(0.6, 0))

# ---- 左侧：数据采集模块 ↔ 主控单元（SPI 双向，跨列拉长约3倍） ----
draw_double_arrow((DAC_X + DAC_W, R3_Y + ROW_H * 0.6), (MCU_X, R3_Y + ROW_H * 0.6),
                  label='SPI', label_offset=(0, 0.12))

# ---- 左侧：主控单元 → 数据采集模块（CONVST/BUSY 控制信号） ----
draw_arrow((MCU_X, R3_Y + ROW_H * 0.35), (DAC_X + DAC_W, R3_Y + ROW_H * 0.35),
           label='CONVST/BUSY', label_offset=(0, -0.18))

# ---- 底部：存储模块 ↔ 主控单元（SDIO 双向） ----
draw_double_arrow((C2_X + C2_W / 2, MCU_Y), (C2_X + C2_W / 2, SD_Y + ROW_H),
                  label='SDIO', label_offset=(-0.5, 0))

# ---- 右侧上方：蓝牙 ↔ 主控单元（USART 双向） ----
draw_double_arrow((MCU_X + MCU_W, R2_Y + ROW_H / 2), (BT_X, R2_Y + ROW_H / 2),
                  label='USART', label_offset=(0, 0.12))
# 蓝牙 → 近端设备（向上）
draw_arrow((BT_X + BT_W / 2, BT_Y + BT_H), (NEAR_X + NEAR_W / 2, NEAR_Y))

# ---- 右侧下方：远距离通信 ↔ 主控单元（USART 双向） ----
draw_double_arrow((MCU_X + MCU_W, R3_Y + ROW_H / 2), (LR_X, R3_Y + ROW_H / 2),
                  label='USART', label_offset=(0, 0.12))
# 远距离通信 → 远端服务器（向下）
draw_arrow((LR_X + LR_W / 2, LR_Y), (SRV_X + SRV_W / 2, SRV_Y + SRV_H))

# ---- 主控内部：实时时钟 → MCU 核心（虚线箭头，闹钟唤醒中断） ----
draw_arrow((RTC_X + RTC_W / 2, RTC_Y + RTC_H),
           (RTC_X + RTC_W / 2, MCU_Y + MCU_H * 0.6),
           label='闹钟唤醒中断', linestyle='--',
           label_offset=(1.0, 0))

# ==================== 数据流向说明（图注） ====================
ax.text(C2_X + C2_W / 2, 2.0,
        '数据流向说明：加速度信号经采集模块进入主控单元，经双缓冲机制写入存储模块；\n'
        '上传时从存储模块读取数据，与定位信息封装后经通信单元发送。',
        ha='center', va='center', fontsize=9, fontfamily='SimHei',
        bbox=dict(facecolor='white', edgecolor='black', pad=6, linestyle='--'))

# ==================== 输出 ====================
plt.tight_layout()
plt.savefig('hardware_block_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
plt.show()
