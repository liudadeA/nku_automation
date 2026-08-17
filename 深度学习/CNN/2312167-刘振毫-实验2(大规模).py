import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import matplotlib.pyplot as plt
import numpy as np
import time
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 设置随机种子
torch.manual_seed(42)
np.random.seed(42)

# 设备配置
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")

# 数据预处理
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

# 使用本地MNIST数据集路径
data_path = r"C:\Users\Administrator\Desktop\shendu\data\MNIST\raw"

# 加载数据集
train_dataset = datasets.FashionMNIST(root=data_path, train=True, download=True, transform=transform)
test_dataset = datasets.FashionMNIST(root=data_path, train=False, download=True, transform=transform)

batch_size = 128
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)


# 大规模VGG网络
class MediumVGG(nn.Module):
    def __init__(self, num_classes=10):
        super(MediumVGG, self).__init__()
        # 增加通道数和层数，但适应28x28输入
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(1, 64, 3, padding=1), 
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1), 
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Block 2
            nn.Conv2d(64, 128, 3, padding=1), 
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 3, padding=1), 
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Block 3
            nn.Conv2d(128, 256, 3, padding=1), 
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1), 
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256 * 7 * 7, 1024), 
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(1024, 512), 
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(512, num_classes)
        )
        
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x

# 大规模NIN
class MediumNIN(nn.Module):
    def __init__(self, num_classes=10):
        super(MediumNIN, self).__init__()
        # 增加通道数和网络深度，适应28x28输入
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(1, 96, 5, padding=2), 
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.Conv2d(96, 96, 1), 
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.Conv2d(96, 96, 1), 
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(3, stride=2, padding=1),
            nn.Dropout(0.5),
            
            # Block 2
            nn.Conv2d(96, 192, 5, padding=2), 
            nn.BatchNorm2d(192),
            nn.ReLU(inplace=True),
            nn.Conv2d(192, 192, 1), 
            nn.BatchNorm2d(192),
            nn.ReLU(inplace=True),
            nn.Conv2d(192, 192, 1), 
            nn.BatchNorm2d(192),
            nn.ReLU(inplace=True),
            nn.AvgPool2d(3, stride=2, padding=1),
            nn.Dropout(0.5),
            
            # Block 3
            nn.Conv2d(192, 192, 3, padding=1), 
            nn.BatchNorm2d(192),
            nn.ReLU(inplace=True),
            nn.Conv2d(192, 192, 1), 
            nn.BatchNorm2d(192),
            nn.ReLU(inplace=True),
            nn.Conv2d(192, num_classes, 1),
            nn.AdaptiveAvgPool2d((1, 1))
        )
        
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return x

# Inception模块 
class CorrectedInception(nn.Module):
    def __init__(self, in_channels, out1x1, red3x3, out3x3, red5x5, out5x5, pool_proj):
        super(CorrectedInception, self).__init__()
        
        # 1x1 branch
        self.branch1 = nn.Sequential(
            nn.Conv2d(in_channels, out1x1, kernel_size=1),
            nn.BatchNorm2d(out1x1),
            nn.ReLU(inplace=True)
        )
        
        # 3x3 branch
        self.branch2 = nn.Sequential(
            nn.Conv2d(in_channels, red3x3, kernel_size=1),
            nn.BatchNorm2d(red3x3),
            nn.ReLU(inplace=True),
            nn.Conv2d(red3x3, out3x3, kernel_size=3, padding=1),
            nn.BatchNorm2d(out3x3),
            nn.ReLU(inplace=True)
        )
        
        # 5x5 branch
        self.branch3 = nn.Sequential(
            nn.Conv2d(in_channels, red5x5, kernel_size=1),
            nn.BatchNorm2d(red5x5),
            nn.ReLU(inplace=True),
            nn.Conv2d(red5x5, out5x5, kernel_size=5, padding=2),
            nn.BatchNorm2d(out5x5),
            nn.ReLU(inplace=True)
        )
        
        # Pooling branch
        self.branch4 = nn.Sequential(
            nn.MaxPool2d(kernel_size=3, stride=1, padding=1),
            nn.Conv2d(in_channels, pool_proj, kernel_size=1),
            nn.BatchNorm2d(pool_proj),
            nn.ReLU(inplace=True)
        )
        
    def forward(self, x):
        branch1 = self.branch1(x)
        branch2 = self.branch2(x)
        branch3 = self.branch3(x)
        branch4 = self.branch4(x)
        
        outputs = [branch1, branch2, branch3, branch4]
        return torch.cat(outputs, 1)

# GoogleNet 
class CorrectedGoogleNet(nn.Module):
    def __init__(self, num_classes=10):
        super(CorrectedGoogleNet, self).__init__()
        
        # Initial convolution
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        )
        
        # Second convolution
        self.conv2 = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 192, kernel_size=3, padding=1),
            nn.BatchNorm2d(192),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        )
        
        # Inception modules
        self.inception3a = CorrectedInception(192, 64, 96, 128, 16, 32, 32)
        self.inception3b = CorrectedInception(256, 128, 128, 192, 32, 96, 64)
        
        # Max pooling
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        self.inception4a = CorrectedInception(480, 192, 96, 208, 16, 48, 64)
        
        # Global average pooling
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.dropout = nn.Dropout(0.4)
        
        # 计算最终的特征维度
        final_features = 192 + 208 + 48 + 64  # 所有分支的输出通道数之和
        self.fc = nn.Linear(final_features, num_classes)
        
    def forward(self, x):
        x = self.conv1(x)      # [batch, 64, 7, 7]
        x = self.conv2(x)      # [batch, 192, 4, 4]
        
        x = self.inception3a(x) # [batch, 256, 4, 4]
        x = self.inception3b(x) # [batch, 480, 4, 4]
        x = self.maxpool(x)     # [batch, 480, 2, 2]
        
        x = self.inception4a(x) # [batch, 512, 2, 2]
        
        x = self.avgpool(x)     # [batch, 512, 1, 1]
        x = x.view(x.size(0), -1)
        x = self.dropout(x)
        x = self.fc(x)
        return x

# 基础残差块
class BasicBlock(nn.Module):
    expansion = 1
    
    def __init__(self, in_channels, out_channels, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )
            
    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out

# 大规模ResNet 
class MediumResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super(MediumResNet, self).__init__()
        self.in_channels = 64
        
        #  初始卷积
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 64, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        # 残差层
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)
        
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)
        
    def _make_layer(self, block, out_channels, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_channels, out_channels, stride))
            self.in_channels = out_channels * block.expansion
        return nn.Sequential(*layers)
    
    def forward(self, x):
        x = self.conv1(x)      # [batch, 64, 28, 28]
        x = self.layer1(x)     # [batch, 64, 28, 28]
        x = self.layer2(x)     # [batch, 128, 14, 14]
        x = self.layer3(x)     # [batch, 256, 7, 7]
        x = self.layer4(x)     # [batch, 512, 4, 4]
        x = self.avgpool(x)    # [batch, 512, 1, 1]
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

def MediumResNet18():
    return MediumResNet(BasicBlock, [2, 2, 2, 2])

# 最佳LeNet配置作为基准
class BestLeNet(nn.Module):
    def __init__(self, num_classes=10):
        super(BestLeNet, self).__init__()
        self.conv1 = nn.Conv2d(1, 6, kernel_size=5, padding=2)
        self.bn1 = nn.BatchNorm2d(6)
        self.relu1 = nn.ReLU()
        self.avgpool1 = nn.AvgPool2d(kernel_size=2, stride=2)
        
        self.conv2 = nn.Conv2d(6, 16, kernel_size=5)
        self.bn2 = nn.BatchNorm2d(16)
        self.relu2 = nn.ReLU()
        self.avgpool2 = nn.AvgPool2d(kernel_size=2, stride=2)
        
        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.bn3 = nn.BatchNorm1d(120)
        self.relu3 = nn.ReLU()
        self.fc2 = nn.Linear(120, 84)
        self.bn4 = nn.BatchNorm1d(84)
        self.relu4 = nn.ReLU()
        self.fc3 = nn.Linear(84, num_classes)
        
    def forward(self, x):
        x = self.avgpool1(self.relu1(self.bn1(self.conv1(x))))
        x = self.avgpool2(self.relu2(self.bn2(self.conv2(x))))
        x = x.view(-1, 16 * 5 * 5)
        x = self.relu3(self.bn3(self.fc1(x)))
        x = self.relu4(self.bn4(self.fc2(x)))
        x = self.fc3(x)
        return x

# ==============================
# 训练和评估函数
# ==============================

def train_and_evaluate(model, train_loader, test_loader, epochs=10, model_name="Model"):
    """训练和评估模型"""
    print(f"\n开始训练: {model_name}")
    print("-" * 50)
    
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)
    
    train_losses = []
    train_errors = []
    test_errors = []
    training_time = 0
    
    for epoch in range(epochs):
        # 训练阶段
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0
        
        epoch_start = time.time()
        
        # 使用简单的循环
        batch_count = 0
        total_batches = len(train_loader)
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total_train += labels.size(0)
            correct_train += (predicted == labels).sum().item()
            
            batch_count += 1
            if batch_count % 20 == 0:  # 每20个batch打印一次进度
                print(f'{model_name} Epoch {epoch+1}/{epochs} - Batch {batch_count}/{total_batches}')
        
        scheduler.step()
        
        epoch_time = time.time() - epoch_start
        training_time += epoch_time
        
        train_loss = running_loss / len(train_loader)
        train_error = 100 * (1 - correct_train / total_train)
        
        # 测试阶段
        model.eval()
        correct_test = 0
        total_test = 0
        
        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs.data, 1)
                total_test += labels.size(0)
                correct_test += (predicted == labels).sum().item()
        
        test_error = 100 * (1 - correct_test / total_test)
        
        train_losses.append(train_loss)
        train_errors.append(train_error)
        test_errors.append(test_error)
        
        print(f'Epoch [{epoch+1}/{epochs}], Loss: {train_loss:.4f}, Train Error: {train_error:.2f}%, Test Error: {test_error:.2f}%, Time: {epoch_time:.2f}s')
    
    return {
        'train_loss': train_losses,
        'train_error': train_errors, 
        'test_error': test_errors,
        'training_time': training_time
    }

# 绘制结果曲线
def plot_comparison(results, title, save_path=None):
    """绘制比较曲线"""
    epochs = range(1, len(next(iter(results.values()))['train_loss']) + 1)
    
    fig = plt.figure(figsize=(15, 5))
    
    # 绘制损失函数
    plt.subplot(1, 3, 1)
    for name, data in results.items():
        plt.plot(epochs, data['train_loss'], label=name, linewidth=2)
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('训练损失')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 绘制训练误差
    plt.subplot(1, 3, 2)
    for name, data in results.items():
        plt.plot(epochs, data['train_error'], label=name, linewidth=2)
    plt.xlabel('Epoch')
    plt.ylabel('Train Error (%)')
    plt.title('训练误差')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 绘制测试误差
    plt.subplot(1, 3, 3)
    for name, data in results.items():
        plt.plot(epochs, data['test_error'], label=name, linewidth=2)
    plt.xlabel('Epoch')
    plt.ylabel('Test Error (%)')
    plt.title('测试误差')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()
    plt.close(fig)

#主函数

def main():
    epochs = 10  # 增加训练轮数以适应更大网络
    results = {}
    
    # 保存结果路径
    save_dir = r"C:\Users\Administrator\Desktop\shendu\CNN"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 实验配置 - 扩展规模深度网络实验
    print("=" * 60)
    print("扩展规模深度网络实验")
    print("=" * 60)
    
    # 首先训练基准LeNet
    print("\n训练基准模型: Best LeNet (BatchNorm + ReLU)")
    benchmark_model = BestLeNet()
    benchmark_result = train_and_evaluate(benchmark_model, train_loader, test_loader, epochs, "Best LeNet")
    results["Best LeNet"] = benchmark_result
    
    # 扩展规模深度网络实验
    deep_experiments = [
        {
            'name': 'Medium VGG',
            'model': MediumVGG()
        },
        {
            'name': 'Medium NIN',
            'model': MediumNIN()
        },
        {
            'name': 'Corrected GoogleNet',
            'model': CorrectedGoogleNet()
        },
        {
            'name': 'Medium ResNet18',
            'model': MediumResNet18()
        }
    ]
    
    # 运行扩展规模深度网络实验
    for exp in deep_experiments:
        try:
            result = train_and_evaluate(exp['model'], train_loader, test_loader, epochs, exp['name'])
            results[exp['name']] = result
        except Exception as e:
            print(f"训练 {exp['name']} 时出现错误: {e}")
            print("跳过该模型，继续下一个...")
    
    # 绘制扩展规模深度网络结果
    plot_comparison(results, "扩展规模深度网络实验结果对比", 
                   os.path.join(save_dir, "扩展规模深度网络实验结果.png"))
    
    # 打印最终测试误差比较
    print("\n" + "=" * 80)
    print("最终测试误差比较:")
    print("=" * 80)
    
    # 按测试误差排序
    sorted_results = sorted(results.items(), key=lambda x: x[1]['test_error'][-1])
    
    for name, data in sorted_results:
        final_test_error = data['test_error'][-1]
        training_time = data['training_time']
        print(f"{name:25}: {final_test_error:6.2f}% | 训练时间: {training_time:6.2f}s")
    
    # 计算相对改进
    print("\n" + "=" * 80)
    print("相对于基准的改进:")
    print("=" * 80)
    
    benchmark_error = results["Best LeNet"]['test_error'][-1]
    for name, data in sorted_results:
        if name != "Best LeNet":
            final_test_error = data['test_error'][-1]
            improvement = ((benchmark_error - final_test_error) / benchmark_error) * 100
            print(f"{name:25}: {improvement:6.2f}% 改进")
    
    # 保存实验结果到文件
    result_file = os.path.join(save_dir, "扩展规模实验结果汇总.txt")
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("Fashion-MNIST扩展规模深度网络实验结果汇总\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("实验配置:\n")
        f.write("-" * 30 + "\n")
        f.write(f"Epochs: {epochs}\n")
        f.write(f"Batch Size: {batch_size}\n")
        f.write(f"Learning Rate: 0.001 (with scheduler)\n")
        f.write(f"Optimizer: Adam\n\n")
        
        f.write("性能排名:\n")
        f.write("-" * 30 + "\n")
        for i, (name, data) in enumerate(sorted_results, 1):
            final_test_error = data['test_error'][-1]
            training_time = data['training_time']
            f.write(f"{i:2}. {name:20}: {final_test_error:.2f}% | 训练时间: {training_time:.2f}s\n")
        
        f.write("\n相对于基准的改进:\n")
        f.write("-" * 30 + "\n")
        for name, data in sorted_results:
            if name != "Best LeNet":
                final_test_error = data['test_error'][-1]
                improvement = ((benchmark_error - final_test_error) / benchmark_error) * 100
                f.write(f"{name:20}: {improvement:.2f}% 改进\n")
        
        f.write("\n网络参数统计:\n")
        f.write("-" * 30 + "\n")
        for name in results.keys():
            if name == "Best LeNet":
                model = BestLeNet()
            elif name == "Medium VGG":
                model = MediumVGG()
            elif name == "Medium NIN":
                model = MediumNIN()
            elif name == "Corrected GoogleNet":
                model = CorrectedGoogleNet()
            elif name == "Medium ResNet18":
                model = MediumResNet18()
            
            total_params = sum(p.numel() for p in model.parameters())
            f.write(f"{name:20}: {total_params:,} 参数\n")
        
        f.write("\n网络架构特点:\n")
        f.write("-" * 30 + "\n")
        f.write("Medium VGG: 3个卷积块，通道数64-128-256，适应28x28输入\n")
        f.write("Medium NIN: 3个MLP卷积块，使用全局平均池化\n")
        f.write("Corrected GoogleNet: 修正的Inception模块，适应小尺寸输入\n")
        f.write("Medium ResNet18: 使用BasicBlock，4个残差层\n")
    
    print(f"\n扩展规模实验已完成！")
    print(f"图表已保存到: {save_dir}")
    print(f"结果汇总已保存到: {result_file}")

if __name__ == "__main__":
    main()