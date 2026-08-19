import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
import numpy as np
import os
import time

# 设置随机种子
torch.manual_seed(42)
np.random.seed(42)

# 创建保存结果的目录
if not os.path.exists('results_extra'):
    os.makedirs('results_extra')

# 设备配置
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# 数据加载和预处理
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])

# 加载MNIST数据集
train_dataset = torchvision.datasets.MNIST(root='./data', train=True, download=True, transform=transform)
test_dataset = torchvision.datasets.MNIST(root='./data', train=False, download=True, transform=transform)

# 为了更容易观察到过拟合，我们使用更少的训练数据
train_subset = torch.utils.data.Subset(train_dataset, range(3000))  # 只使用3000个样本
train_loader_small = torch.utils.data.DataLoader(train_subset, batch_size=128, shuffle=True)
train_loader_full = torch.utils.data.DataLoader(train_dataset, batch_size=128, shuffle=True)
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=128, shuffle=False)

print(f"完整训练集大小: {len(train_dataset)}")
print(f"小训练集大小: {len(train_subset)}")
print(f"测试集大小: {len(test_dataset)}")

class MLPWithRegularization(nn.Module):
    def __init__(self, layer_sizes, activation='relu', dropout_rate=0.0, use_batchnorm=False):
        super(MLPWithRegularization, self).__init__()
        layers = []
        
        for i in range(len(layer_sizes) - 1):
            layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))
            
            if i < len(layer_sizes) - 2:  # 不在输出层添加
                # Batch Normalization
                if use_batchnorm:
                    layers.append(nn.BatchNorm1d(layer_sizes[i+1]))
                
                # 激活函数
                if activation == 'relu':
                    layers.append(nn.ReLU())
                elif activation == 'sigmoid':
                    layers.append(nn.Sigmoid())
                elif activation == 'tanh':
                    layers.append(nn.Tanh())
                
                # Dropout
                if dropout_rate > 0:
                    layers.append(nn.Dropout(dropout_rate))
        
        self.network = nn.Sequential(*layers)
        
    def forward(self, x):
        x = x.view(x.size(0), -1)
        return self.network(x)

def count_parameters(model):
    return sum(p.numel() for p in model.parameters())

def train_and_evaluate(model, train_loader, test_loader, criterion, optimizer, num_epochs=10):
    train_losses, train_errors, test_errors = [], [], []
    
    for epoch in range(num_epochs):
        # 训练
        model.train()
        running_loss, correct_train, total_train = 0.0, 0, 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total_train += labels.size(0)
            correct_train += (predicted == labels).sum().item()
        
        # 测试
        model.eval()
        correct_test, total_test = 0, 0
        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs.data, 1)
                total_test += labels.size(0)
                correct_test += (predicted == labels).sum().item()
        
        train_loss = running_loss / len(train_loader)
        train_error = 1 - correct_train / total_train
        test_error = 1 - correct_test / total_test
        
        train_losses.append(train_loss)
        train_errors.append(train_error)
        test_errors.append(test_error)
        
        print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {train_loss:.4f}, Train Error: {train_error:.4f}, Test Error: {test_error:.4f}')
    
    return train_losses, train_errors, test_errors

def save_curves(train_losses, train_errors, test_errors, filename, title):
    plt.figure(figsize=(15, 4))
    
    plt.subplot(1, 3, 1)
    plt.plot(train_losses)
    plt.title(f'{title} - Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.grid(True)
    
    plt.subplot(1, 3, 2)
    plt.plot(train_errors, label='Train Error')
    plt.plot(test_errors, label='Test Error')
    plt.title(f'{title} - Error Rates')
    plt.xlabel('Epoch')
    plt.ylabel('Error Rate')
    plt.legend()
    plt.grid(True)
    
    plt.subplot(1, 3, 3)
    plt.semilogy(train_errors, label='Train Error')
    plt.semilogy(test_errors, label='Test Error')
    plt.title(f'{title} - Error Rates (Log Scale)')
    plt.xlabel('Epoch')
    plt.ylabel('Error Rate')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(f'results_extra/{filename}.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: results_extra/{filename}.png")

# 记录开始时间
start_time = time.time()

print("="*60)
print("附加题实验")
print("="*60)

# 要求1：模型复杂度与误差关系
print("\n" + "="*50)
print("要求1：模型复杂度与误差关系")
print("="*50)

complexity_architectures = {
    "Simple[64-32]": [784, 64, 32, 10],
    "Medium[256-128]": [784, 256, 128, 10],
    "Complex[512-256-128]": [784, 512, 256, 128, 10],
    "VeryComplex[1024-512-256-128]": [784, 1024, 512, 256, 128, 10]
}

complexity_results = []

for name, layers in complexity_architectures.items():
    print(f"\n训练 {name} 模型")
    model = MLPWithRegularization(layers, activation='relu').to(device)
    params = count_parameters(model)
    print(f"参数量: {params:,}")
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    train_losses, train_errors, test_errors = train_and_evaluate(
        model, train_loader_full, test_loader, criterion, optimizer, num_epochs=15
    )
    
    complexity_results.append({
        'name': name,
        'params': params,
        'train_errors': train_errors,
        'test_errors': test_errors,
        'final_train_error': train_errors[-1],
        'final_test_error': test_errors[-1],
        'overfitting_gap': test_errors[-1] - train_errors[-1]
    })
    
    save_curves(train_losses, train_errors, test_errors, f"complexity_{name}", f"Complexity: {name}")

# 分析模型复杂度与误差关系
print("\n模型复杂度与误差关系分析:")
print("-" * 80)
print(f"{'模型':<25} {'参数量':<15} {'训练误差':<12} {'测试误差':<12} {'过拟合差距':<12}")
print("-" * 80)
for result in complexity_results:
    print(f"{result['name']:<25} {result['params']:<15,} {result['final_train_error']:<12.4f} {result['final_test_error']:<12.4f} {result['overfitting_gap']:<12.4f}")

# 要求2：观察过拟合现象
print("\n" + "="*50)
print("要求2：观察过拟合现象")
print("="*50)

print("使用小训练集（3000样本）和复杂网络来制造过拟合...")

overfit_model = MLPWithRegularization([784, 1024, 512, 256, 128, 10], activation='relu').to(device)
print(f"过拟合模型参数量: {count_parameters(overfit_model):,}")

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(overfit_model.parameters(), lr=0.001)

train_losses, train_errors, test_errors = train_and_evaluate(
    overfit_model, train_loader_small, test_loader, criterion, optimizer, num_epochs=30
)

save_curves(train_losses, train_errors, test_errors, "overfitting", "Overfitting Example")

# 分析过拟合程度
final_overfitting_gap = test_errors[-1] - train_errors[-1]
print(f"\n过拟合分析:")
print(f"最终训练误差: {train_errors[-1]:.4f}")
print(f"最终测试误差: {test_errors[-1]:.4f}")
print(f"过拟合差距: {final_overfitting_gap:.4f}")

# 要求3：L2正则化
print("\n" + "="*50)
print("要求3：L2正则化")
print("="*50)

l2_values = [0, 0.001, 0.01, 0.1]
l2_results = []

for l2 in l2_values:
    print(f"\n训练 L2正则化 (λ={l2}) 模型")
    model = MLPWithRegularization([784, 1024, 512, 256, 128, 10], activation='relu').to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=l2)  # weight_decay就是L2正则化
    
    train_losses, train_errors, test_errors = train_and_evaluate(
        model, train_loader_small, test_loader, criterion, optimizer, num_epochs=20
    )
    
    l2_results.append({
        'l2': l2,
        'train_errors': train_errors,
        'test_errors': test_errors,
        'final_train_error': train_errors[-1],
        'final_test_error': test_errors[-1],
        'overfitting_gap': test_errors[-1] - train_errors[-1]
    })
    
    save_curves(train_losses, train_errors, test_errors, f"l2_{l2}", f"L2 Regularization (λ={l2})")

# 分析L2正则化效果
print("\nL2正则化效果分析:")
print("-" * 70)
print(f"{'L2值':<10} {'训练误差':<12} {'测试误差':<12} {'过拟合差距':<12} {'改善程度':<12}")
print("-" * 70)
baseline_gap = l2_results[0]['overfitting_gap']
for result in l2_results:
    improvement = baseline_gap - result['overfitting_gap']
    print(f"{result['l2']:<10} {result['final_train_error']:<12.4f} {result['final_test_error']:<12.4f} {result['overfitting_gap']:<12.4f} {improvement:<12.4f}")

# 要求4：Dropout
print("\n" + "="*50)
print("要求4：Dropout")
print("="*50)

dropout_rates = [0, 0.2, 0.5]
dropout_results = []

for dropout_rate in dropout_rates:
    print(f"\n训练 Dropout (rate={dropout_rate}) 模型")
    model = MLPWithRegularization(
        [784, 1024, 512, 256, 128, 10], 
        activation='relu', 
        dropout_rate=dropout_rate
    ).to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    train_losses, train_errors, test_errors = train_and_evaluate(
        model, train_loader_small, test_loader, criterion, optimizer, num_epochs=20
    )
    
    dropout_results.append({
        'dropout_rate': dropout_rate,
        'train_errors': train_errors,
        'test_errors': test_errors,
        'final_train_error': train_errors[-1],
        'final_test_error': test_errors[-1],
        'overfitting_gap': test_errors[-1] - train_errors[-1]
    })
    
    save_curves(train_losses, train_errors, test_errors, f"dropout_{dropout_rate}", f"Dropout (rate={dropout_rate})")

# 分析Dropout效果
print("\nDropout效果分析:")
print("-" * 75)
print(f"{'Dropout率':<12} {'训练误差':<12} {'测试误差':<12} {'过拟合差距':<12} {'改善程度':<12}")
print("-" * 75)
baseline_gap = dropout_results[0]['overfitting_gap']
for result in dropout_results:
    improvement = baseline_gap - result['overfitting_gap']
    print(f"{result['dropout_rate']:<12} {result['final_train_error']:<12.4f} {result['final_test_error']:<12.4f} {result['overfitting_gap']:<12.4f} {improvement:<12.4f}")

# 要求5：Batch Normalization
print("\n" + "="*50)
print("要求5：Batch Normalization")
print("="*50)

batchnorm_configs = [False, True]
batchnorm_results = []

for use_batchnorm in batchnorm_configs:
    config_name = "With BatchNorm" if use_batchnorm else "No BatchNorm"
    print(f"\n训练 {config_name} 模型")
    
    model = MLPWithRegularization(
        [784, 1024, 512, 256, 128, 10], 
        activation='relu',
        use_batchnorm=use_batchnorm
    ).to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    train_losses, train_errors, test_errors = train_and_evaluate(
        model, train_loader_small, test_loader, criterion, optimizer, num_epochs=20
    )
    
    batchnorm_results.append({
        'use_batchnorm': use_batchnorm,
        'train_errors': train_errors,
        'test_errors': test_errors,
        'final_train_error': train_errors[-1],
        'final_test_error': test_errors[-1],
        'overfitting_gap': test_errors[-1] - train_errors[-1]
    })
    
    save_curves(train_losses, train_errors, test_errors, f"batchnorm_{use_batchnorm}", f"BatchNorm: {config_name}")

# 分析BatchNorm效果
print("\nBatch Normalization效果分析:")
print("-" * 75)
print(f"{'配置':<15} {'训练误差':<12} {'测试误差':<12} {'过拟合差距':<12} {'改善程度':<12}")
print("-" * 75)
baseline_gap = batchnorm_results[0]['overfitting_gap']
for result in batchnorm_results:
    config_name = "With BatchNorm" if result['use_batchnorm'] else "No BatchNorm"
    improvement = baseline_gap - result['overfitting_gap']
    print(f"{config_name:<15} {result['final_train_error']:<12.4f} {result['final_test_error']:<12.4f} {result['overfitting_gap']:<12.4f} {improvement:<12.4f}")

# 综合对比所有正则化方法
print("\n" + "="*60)
print("正则化方法综合对比")
print("="*60)

print("所有正则化方法在减少过拟合方面的效果对比:")
print("-" * 90)
print(f"{'方法':<20} {'训练误差':<12} {'测试误差':<12} {'过拟合差距':<12} {'改善程度':<12} {'泛化能力':<12}")
print("-" * 90)

# 基准（无正则化）
baseline = l2_results[0]
print(f"{'无正则化':<20} {baseline['final_train_error']:<12.4f} {baseline['final_test_error']:<12.4f} {baseline['overfitting_gap']:<12.4f} {'0.0000':<12} {'差':<12}")

# 最佳L2
best_l2 = min(l2_results[1:], key=lambda x: x['overfitting_gap'])
print(f"{f'L2(λ={best_l2['l2']})':<20} {best_l2['final_train_error']:<12.4f} {best_l2['final_test_error']:<12.4f} {best_l2['overfitting_gap']:<12.4f} {baseline['overfitting_gap'] - best_l2['overfitting_gap']:<12.4f} {'好':<12}")

# 最佳Dropout
best_dropout = min(dropout_results[1:], key=lambda x: x['overfitting_gap'])
print(f"{f'Dropout({best_dropout['dropout_rate']})':<20} {best_dropout['final_train_error']:<12.4f} {best_dropout['final_test_error']:<12.4f} {best_dropout['overfitting_gap']:<12.4f} {baseline['overfitting_gap'] - best_dropout['overfitting_gap']:<12.4f} {'好':<12}")

# BatchNorm
batchnorm_result = batchnorm_results[1]  # 使用BatchNorm的结果
print(f"{'BatchNorm':<20} {batchnorm_result['final_train_error']:<12.4f} {batchnorm_result['final_test_error']:<12.4f} {batchnorm_result['overfitting_gap']:<12.4f} {baseline['overfitting_gap'] - batchnorm_result['overfitting_gap']:<12.4f} {'较好':<12}")

# 计算总运行时间
end_time = time.time()
total_time = end_time - start_time
print(f"\n所有附加题实验完成！总运行时间: {total_time:.2f} 秒")
print(f"所有图表已保存到 'results_extra' 目录")

# 实验总结
print("\n" + "="*60)
print("附加题实验总结")
print("="*60)
print("1. 模型复杂度与误差关系:")
print("   - 简单模型：训练误差和测试误差都较高，但差距小（欠拟合）")
print("   - 复杂模型：训练误差低，但测试误差高，差距大（过拟合）")
print("   - 适度复杂度：平衡训练和测试误差，泛化能力最佳")

print("\n2. 过拟合现象:")
print("   - 使用小数据集和复杂网络可以明显观察到过拟合")
print("   - 训练误差持续下降，但测试误差在某个点后开始上升")

print("\n3. 正则化效果:")
print("   - L2正则化：通过惩罚大权重减少过拟合")
print("   - Dropout：通过随机丢弃神经元防止过拟合")
print("   - BatchNorm：通过归一化激活值加速训练并提高泛化")

print("\n4. 最佳实践:")
print("   - 对于复杂模型，应该使用正则化技术")
print("   - 不同正则化方法可以组合使用")
print("   - 需要根据具体问题调整正则化强度")