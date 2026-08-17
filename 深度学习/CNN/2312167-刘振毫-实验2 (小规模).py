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

data_path = r"C:\Users\Administrator\Desktop\shendu\data\MNIST\raw"

# 加载数据集
train_dataset = datasets.FashionMNIST(root=data_path, train=True, download=True, transform=transform)
test_dataset = datasets.FashionMNIST(root=data_path, train=False, download=True, transform=transform)

batch_size = 128
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

# VGG网络
class  VGG(nn.Module):
    def __init__(self, num_classes=10):
        super( VGG, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), 
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, 3, padding=1), 
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(32, 64, 3, padding=1), 
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1), 
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(64 * 7 * 7, 256), 
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(256, 128), 
            nn.ReLU(inplace=True),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x

# NIN
class  NIN(nn.Module):
    def __init__(self, num_classes=10):
        super( NIN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 64, 5, padding=2), 
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 1), 
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 1), 
            nn.ReLU(inplace=True),
            nn.MaxPool2d(3, stride=2, padding=1),
            nn.Dropout(0.5),
            
            nn.Conv2d(64, 128, 5, padding=2), 
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 1), 
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 1), 
            nn.ReLU(inplace=True),
            nn.MaxPool2d(3, stride=2, padding=1),
            nn.Dropout(0.5),
            
            nn.Conv2d(128, 256, 3, padding=1), 
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 1), 
            nn.ReLU(inplace=True),
            nn.Conv2d(256, num_classes, 1),
            nn.AdaptiveAvgPool2d((1, 1))
        )
        
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return x

# Inception模块
class Inception(nn.Module):
    def __init__(self, in_channels, ch1x1, ch3x3):
        super(Inception, self).__init__()
        self.branch1 = nn.Sequential(
            nn.Conv2d(in_channels, ch1x1, kernel_size=1),
            nn.BatchNorm2d(ch1x1),
            nn.ReLU(inplace=True)
        )
        self.branch2 = nn.Sequential(
            nn.Conv2d(in_channels, ch3x3, kernel_size=3, padding=1),
            nn.BatchNorm2d(ch3x3),
            nn.ReLU(inplace=True)
        )
        
    def forward(self, x):
        branch1 = self.branch1(x)
        branch2 = self.branch2(x)
        outputs = [branch1, branch2]
        return torch.cat(outputs, 1)

# GoogleNet
class  GoogleNet(nn.Module):
    def __init__(self, num_classes=10):
        super( GoogleNet, self).__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True)
        )
        
        self.inception1 = Inception(32, 16, 32)
        self.inception2 = Inception(48, 32, 48)
        
        self.pool = nn.MaxPool2d(2, 2)
        
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(80 * 7 * 7, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )
        
    def forward(self, x):
        x = self.conv1(x)
        x = self.pool(x)
        
        x = self.inception1(x)
        x = self.pool(x)
        
        x = self.inception2(x)
        
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x

# 残差块
class BasicBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, stride, 1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, 1, 1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride),
                nn.BatchNorm2d(out_channels)
            )
            
    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out

# ResNet
class  ResNet(nn.Module):
    def __init__(self, num_classes=10):
        super( ResNet, self).__init__()
        self.in_channels = 32
        
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 32, 3, 1, 1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True)
        )
        
        self.layer1 = self._make_layer(32, 2, stride=1)
        self.layer2 = self._make_layer(64, 2, stride=2)
        
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(64, num_classes)
        
    def _make_layer(self, out_channels, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(BasicBlock(self.in_channels, out_channels, stride))
            self.in_channels = out_channels
        return nn.Sequential(*layers)
    
    def forward(self, x):
        x = self.conv1(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

# LeNet配置作为基准
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

# 训练和评估函数

def train_and_evaluate(model, train_loader, test_loader, epochs=5, model_name="Model"):
    """训练和评估模型"""
    print(f"\n开始训练: {model_name}")
    print("-" * 50)
    
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
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
        
        # 使用简单的循环替代tqdm
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

# 附加实验主函数

def main():
    epochs = 5
    results = {}
    
    # 保存结果路径
    save_dir = r"C:\Users\Administrator\Desktop\shendu\CNN"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 实验配置 - 深度网络实验
    print("=" * 60)
    print("深度网络附加实验")
    print("=" * 60)
    
    # 首先训练基准LeNet
    print("\n训练基准模型: Best LeNet (BatchNorm + ReLU)")
    benchmark_model = BestLeNet()
    benchmark_result = train_and_evaluate(benchmark_model, train_loader, test_loader, epochs, "Best LeNet")
    results["Best LeNet"] = benchmark_result
    
    # 深度网络实验
    deep_experiments = [
        {
            'name': '  VGG',
            'model':  VGG()
        },
        {
            'name': '  NIN',
            'model':  NIN()
        },
        {
            'name': '  GoogleNet',
            'model':  GoogleNet()
        },
        {
            'name': '  ResNet',
            'model':  ResNet()
        }
    ]
    
    # 运行深度网络实验
    for exp in deep_experiments:
        result = train_and_evaluate(exp['model'], train_loader, test_loader, epochs, exp['name'])
        results[exp['name']] = result
    
    # 绘制深度网络结果
    plot_comparison(results, "深度网络附加实验结果对比", 
                   os.path.join(save_dir, "深度网络附加实验结果.png"))
    
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
    result_file = os.path.join(save_dir, "附加实验结果汇总.txt")
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("Fashion-MNIST深度网络附加实验结果汇总\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("实验配置:\n")
        f.write("-" * 30 + "\n")
        f.write(f"Epochs: {epochs}\n")
        f.write(f"Batch Size: {batch_size}\n")
        f.write(f"Learning Rate: 0.001\n")
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
            elif name == "  VGG":
                model =  VGG()
            elif name == "  NIN":
                model =  NIN()
            elif name == "  GoogleNet":
                model =  GoogleNet()
            elif name == "  ResNet":
                model =  ResNet()
            
            total_params = sum(p.numel() for p in model.parameters())
            f.write(f"{name:20}: {total_params:,} 参数\n")
    
    print(f"\n附加实验已完成！")
    print(f"图表已保存到: {save_dir}")
    print(f"结果汇总已保存到: {result_file}")

if __name__ == "__main__":
    main()