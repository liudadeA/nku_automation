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
if not os.path.exists('results'):
    os.makedirs('results')

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

train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=128, shuffle=True)
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=128, shuffle=False)

print(f"训练集大小: {len(train_dataset)}")
print(f"测试集大小: {len(test_dataset)}")

class MLP(nn.Module):
    def __init__(self, layer_sizes, activation='relu'):
        super(MLP, self).__init__()
        layers = []
        for i in range(len(layer_sizes) - 1):
            layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))
            if i < len(layer_sizes) - 2:
                if activation == 'relu':
                    layers.append(nn.ReLU())
                elif activation == 'sigmoid':
                    layers.append(nn.Sigmoid())
                elif activation == 'tanh':
                    layers.append(nn.Tanh())
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
    plt.savefig(f'results/{filename}.png', dpi=150, bbox_inches='tight')
    plt.close()  # 关闭图表，释放内存
    print(f"图表已保存: results/{filename}.png")

# 记录开始时间
start_time = time.time()

# 要求1：基础模型训练
print("="*50)
print("要求1：基础模型训练")
print("="*50)

base_model = MLP([784, 256, 128, 10], activation='relu').to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(base_model.parameters(), lr=0.001)

print(f"基础模型参数量: {count_parameters(base_model):,}")

train_losses, train_errors, test_errors = train_and_evaluate(
    base_model, train_loader, test_loader, criterion, optimizer, num_epochs=10
)

save_curves(train_losses, train_errors, test_errors, "base_model", "Base Model")

# 要求2：参数量计算
print("\n" + "="*50)
print("要求2：参数量计算")
print("="*50)
print(f"基础模型总参数量: {count_parameters(base_model):,}")

# 要求3：不同网络结构比较
print("\n" + "="*50)
print("要求3：不同网络结构比较")
print("="*50)

architectures = {
    "Small[64-32]": [784, 64, 32, 10],
    "Base[256-128]": [784, 256, 128, 10],
    "Large[512-256]": [784, 512, 256, 10],
    "Deeper[256-128-64]": [784, 256, 128, 64, 10]
}

architecture_results = []

for name, layers in architectures.items():
    print(f"\n训练 {name} 模型")
    model = MLP(layers, activation='relu').to(device)
    params = count_parameters(model)
    print(f"参数量: {params:,}")
    
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    train_losses, train_errors, test_errors = train_and_evaluate(
        model, train_loader, test_loader, criterion, optimizer, num_epochs=8
    )
    
    architecture_results.append({
        'name': name,
        'params': params,
        'train_errors': train_errors,
        'test_errors': test_errors,
        'final_test_error': test_errors[-1]
    })
    
    save_curves(train_losses, train_errors, test_errors, f"architecture_{name}", f"Architecture: {name}")

# 参数量与性能关系分析
print("\n参数量对性能的影响分析:")
for result in architecture_results:
    print(f"{result['name']}: {result['params']:,} 参数, 最终测试误差: {result['final_test_error']:.4f}")

# 要求4：不同激活函数比较
print("\n" + "="*50)
print("要求4：不同激活函数比较")
print("="*50)

activations = ['relu', 'sigmoid', 'tanh']

for activation in activations:
    print(f"\n训练使用 {activation} 激活函数的模型")
    model = MLP([784, 256, 128, 10], activation=activation).to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    train_losses, train_errors, test_errors = train_and_evaluate(
        model, train_loader, test_loader, criterion, optimizer, num_epochs=8
    )
    
    save_curves(train_losses, train_errors, test_errors, f"activation_{activation}", f"Activation: {activation}")

# 要求5：不同损失函数比较
print("\n" + "="*50)
print("要求5：不同损失函数比较")
print("="*50)

loss_functions = {
    'CrossEntropy': nn.CrossEntropyLoss(),
    'MSE': nn.MSELoss(),
}

for loss_name, loss_func in loss_functions.items():
    print(f"\n训练使用 {loss_name} 损失函数的模型")
    model = MLP([784, 256, 128, 10], activation='relu').to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # 对于MSE损失，需要特殊处理
    if loss_name == 'MSE':
        def mse_criterion(outputs, labels):
            targets = torch.nn.functional.one_hot(labels, num_classes=10).float()
            return loss_func(outputs, targets)
        current_criterion = mse_criterion
    else:
        current_criterion = loss_func
    
    train_losses, train_errors, test_errors = train_and_evaluate(
        model, train_loader, test_loader, current_criterion, optimizer, num_epochs=8
    )
    
    save_curves(train_losses, train_errors, test_errors, f"loss_{loss_name}", f"Loss: {loss_name}")

# 计算总运行时间
end_time = time.time()
total_time = end_time - start_time
print(f"\n所有实验完成！总运行时间: {total_time:.2f} 秒")
print(f"所有图表已保存到 'results' 目录")