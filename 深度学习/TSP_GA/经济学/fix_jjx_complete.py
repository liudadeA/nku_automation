# 读取文件内容
with open('e:\shendu\TSP_GA\jjx.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 处理第一个公式区域
formula1_start = content.find('在形式上，这一结构可以简化表示为：')
if formula1_start != -1:
    formula1_start += len('在形式上，这一结构可以简化表示为：')
    # 找到第一个"其中，"后的完整段落结束位置
    # 寻找包含"表示企业"的部分作为结束点
    formula1_end = content.find('表示企业', formula1_start)
    if formula1_end != -1:
        # 继续找到"表示企业"后的完整结构结束
        formula1_end_full = content.find('系统对这些节点的扰动敏感性将急剧上升。', formula1_end)
        if formula1_end_full != -1:
            formula1_end_full += len('系统对这些节点的扰动敏感性将急剧上升。')
            # 构建新的内容
            new_content_part1 = content[:formula1_start] + '\n\n$$Y_i = A_i \cdot f\left(\sum_j \omega_{ij} X_j\right)$$\n\n其中，$Y_i$ 表示企业 $i$ 的产出，$X_j$ 为来自上游企业 $j$ 的中间投入，$\omega_{ij}$ 则刻画了投入依赖强度。当 $\omega_{ij}$ 在少数 $j$ 上高度集中时，系统对这些节点的扰动敏感性将急剧上升。' + content[formula1_end_full:]
            content = new_content_part1

# 处理第二个公式区域
formula2_start = content.find('若将生产系统类比为一个连续时间动态系统，其简化形式可写为：')
if formula2_start != -1:
    formula2_start += len('若将生产系统类比为一个连续时间动态系统，其简化形式可写为：')
    # 找到第二个"其中，"后的完整段落结束位置
    formula2_end = content.find('系统等效阻尼下降', formula2_start)
    if formula2_end != -1:
        formula2_end_full = content.find('传递至输出端。', formula2_end)
        if formula2_end_full != -1:
            formula2_end_full += len('传递至输出端。')
            # 构建新的内容
            new_content_part2 = content[:formula2_start] + '\n\n$$\dot{x}(t) = Ax(t) + Bu(t)$$\n\n其中，状态变量 $x(t)$ 可理解为库存与在制品水平，控制输入 $u(t)$ 对应外部供应。当库存趋近于零时，系统等效阻尼下降，任何来自 $u(t)$ 的冲击都会被几乎无衰减地传递至输出端。' + content[formula2_end_full:]
            content = new_content_part2

# 保存修正后的内容
with open('e:\shendu\TSP_GA\jjx_fully_fixed.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("文件已完全修正并保存为 jjx_fully_fixed.md")