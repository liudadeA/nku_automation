# 测试修复后的代码是否解决了卡死问题
import numpy as np
import torch
import os
import sys

# 将当前目录添加到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入必要的函数
from txt import compare_all_variants

# 定义一个简单的测试函数
def simple_func(x, num_obj=2):
    """简单的多目标测试函数"""
    if hasattr(x, 'shape') and len(x.shape) > 1:
        # 批量处理
        f1 = torch.sum(x ** 2, dim=1)
        f2 = torch.sum((x - 2) ** 2, dim=1)
        return torch.stack([f1, f2], dim=1)
    else:
        # 单个样本
        f1 = torch.sum(x ** 2)
        f2 = torch.sum((x - 2) ** 2)
        return torch.tensor([f1, f2])

if __name__ == "__main__":
    print("开始测试修复后的代码...")
    
    # 运行一个简单的测试
    results, stats = compare_all_variants(
        func=simple_func,
        func_name="test_simple",
        dim=2,
        max_iter=10,
        runs=2,  # 仅运行2轮
        pop_size=10,
        is_multi_obj=True,
        num_obj=2
    )
    
    print("\n测试完成！")
    print(f"结果类型: {type(results)}")
    print(f"统计信息: {stats}")
    
    # 检查是否生成了结果文件
    result_files = [f for f in os.listdir('.') if f.startswith('test_simple')]
    print(f"\n生成的文件: {result_files}")
    
    print("\n测试成功！修复后的代码没有卡死。")