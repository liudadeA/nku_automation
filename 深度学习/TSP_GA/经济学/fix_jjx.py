# 读取文件内容
with open(r'e:\shendu\TSP_GA\jjx.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 修正第一个公式（使用更精确的匹配）
content = content[:13] + '在形式上，这一结构可以简化表示为：\n\n$$Y_i = A_i \cdot f\left(\sum_j \omega_{ij} X_j\right)$$\n\n' + content[90:]

# 修正第二个公式（使用更精确的匹配）
content = content[:94] + '二、零库存逻辑与动态系统"欠阻尼"问题\n\n在分析丰田汽车等企业所面临的生产中断时，零库存（Just-in-Time）机制是一个无法回避的关键因素。该模式的核心目标在于压缩库存成本，使生产系统运行在接近理论最优效率的区间。然而，这一设计也意味着系统中用于吸收外部扰动的缓冲变量被大幅削弱。\n\n若将生产系统类比为一个连续时间动态系统，其简化形式可写为：\n\n$$\dot{x}(t) = Ax(t) + Bu(t)$$\n\n其中，' + content[137:]

# 保存修正后的内容
with open(r'e:\shendu\TSP_GA\jjx_corrected.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("文件已修正并保存为 jjx_corrected.md")