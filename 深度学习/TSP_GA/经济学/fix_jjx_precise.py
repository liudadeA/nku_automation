# 读取文件内容
with open('e:\shendu\TSP_GA\jjx.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 定位第一个公式的位置
formula1_start = content.find('在形式上，这一结构可以简化表示为：')
if formula1_start != -1:
    formula1_start += len('在形式上，这一结构可以简化表示为：')
    formula1_end = content.find('其中，', formula1_start)
    if formula1_end != -1:
        # 替换第一个公式
        content = content[:formula1_start] + '\n\n$$Y_i = A_i \cdot f\left(\sum_j \omega_{ij} X_j\right)$$\n\n' + content[formula1_end:]

# 定位第二个公式的位置
formula2_start = content.find('若将生产系统类比为一个连续时间动态系统，其简化形式可写为：')
if formula2_start != -1:
    formula2_start += len('若将生产系统类比为一个连续时间动态系统，其简化形式可写为：')
    formula2_end = content.find('其中，状态变量', formula2_start)
    if formula2_end != -1:
        # 替换第二个公式
        content = content[:formula2_start] + '\n\n$$\dot{x}(t) = Ax(t) + Bu(t)$$\n\n' + content[formula2_end:]

# 保存修正后的内容
with open('e:\shendu\TSP_GA\jjx_fixed.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("文件已修正并保存为 jjx_fixed.md")