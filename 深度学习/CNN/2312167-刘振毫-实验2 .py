import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import matplotlib.pyplot as plt
import numpy as np
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

# 定义LeNet模型类
class BaseLeNet(nn.Module):
    def __init__(self, activation='sigmoid', use_batchnorm=False, pool_type='avg', kernel_size=5, channels1=6, channels2=16):
        super(BaseLeNet, self).__init__()
        
        # 激活函数选择
        if activation == 'relu':
            activation_layer = nn.ReLU
        else:
            activation_layer = nn.Sigmoid
            
        # 池化层选择
        if pool_type == 'max':
            pool_layer = nn.MaxPool2d
        else:
            pool_layer = nn.AvgPool2d
        
        # 第一个卷积块
        self.conv1 = nn.Conv2d(1, channels1, kernel_size=kernel_size, padding=kernel_size//2)
        if use_batchnorm:
            self.bn1 = nn.BatchNorm2d(channels1)
        self.act1 = activation_layer()
        self.pool1 = pool_layer(kernel_size=2, stride=2)
        
        # 第二个卷积块
        self.conv2 = nn.Conv2d(channels1, channels2, kernel_size=kernel_size)
        if use_batchnorm:
            self.bn2 = nn.BatchNorm2d(channels2)
        self.act2 = activation_layer()
        self.pool2 = pool_layer(kernel_size=2, stride=2)
        
        # 计算全连接层输入尺寸
        if kernel_size == 3:
            fc_input_size = channels2 * 6 * 6
        elif kernel_size == 5:
            fc_input_size = channels2 * 5 * 5
        elif kernel_size == 7:
            fc_input_size = channels2 * 4 * 4
        else:
            fc_input_size = channels2 * 5 * 5
        
        # 全连接层
        self.fc1 = nn.Linear(fc_input_size, 120)
        if use_batchnorm:
            self.bn3 = nn.BatchNorm1d(120)
        self.act3 = activation_layer()
        
        self.fc2 = nn.Linear(120, 84)
        if use_batchnorm:
            self.bn4 = nn.BatchNorm1d(84)
        self.act4 = activation_layer()
        
        self.fc3 = nn.Linear(84, 10)
        
        # 保存配置
        self.use_batchnorm = use_batchnorm
        self.fc_input_size = fc_input_size
        
    def forward(self, x):
        # 第一个卷积块
        x = self.conv1(x)
        if self.use_batchnorm:
            x = self.bn1(x)
        x = self.act1(x)
        x = self.pool1(x)
        
        # 第二个卷积块
        x = self.conv2(x)
        if self.use_batchnorm:
            x = self.bn2(x)
        x = self.act2(x)
        x = self.pool2(x)
        
        # 全连接层
        x = x.view(-1, self.fc_input_size)
        x = self.fc1(x)
        if self.use_batchnorm:
            x = self.bn3(x)
        x = self.act3(x)
        
        x = self.fc2(x)
        if self.use_batchnorm:
            x = self.bn4(x)
        x = self.act4(x)
        
        x = self.fc3(x)
        return x

# 训练和评估函数
def train_and_evaluate(model_config, train_loader, test_loader, epochs=5):
    """训练和评估模型"""
    model_name = model_config['name']
    model = model_config['model']
    
    print(f"\n开始训练: {model_name}")
    print("-" * 50)
    
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    train_losses = []
    train_errors = []
    test_errors = []
    
    for epoch in range(epochs):
        # 训练阶段
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0
        
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
        
        print(f'Epoch [{epoch+1}/{epochs}], Loss: {train_loss:.4f}, Train Error: {train_error:.2f}%, Test Error: {test_error:.2f}%')
    
    return {
        'train_loss': train_losses,
        'train_error': train_errors, 
        'test_error': test_errors
    }

# 绘制结果曲线
def plot_comparison(results, title, save_path=None):
    """绘制比较曲线"""
    epochs = range(1, len(next(iter(results.values()))['train_loss']) + 1)
    
    plt.figure(figsize=(15, 5))
    
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

# 主实验函数
def main():
    epochs = 5
    results = {}
    
    # 实验配置
    experiments = [
        # 实验1: 原始LeNet (Sigmoid)
        {
            'name': '原始LeNet (Sigmoid)',
            'model': BaseLeNet(activation='sigmoid', use_batchnorm=False, pool_type='avg', kernel_size=5, channels1=6, channels2=16)
        },
        # 实验2: ReLU激活函数
        {
            'name': 'LeNet with ReLU',
            'model': BaseLeNet(activation='relu', use_batchnorm=False, pool_type='avg', kernel_size=5, channels1=6, channels2=16)
        },
        # 实验3: BatchNorm + ReLU
        {
            'name': 'BatchNorm + ReLU',
            'model': BaseLeNet(activation='relu', use_batchnorm=True, pool_type='avg', kernel_size=5, channels1=6, channels2=16)
        },
        # 实验4: 不同卷积核大小
        {
            'name': '卷积核 3x3',
            'model': BaseLeNet(activation='relu', use_batchnorm=False, pool_type='avg', kernel_size=3, channels1=6, channels2=16)
        },
        {
            'name': '卷积核 7x7', 
            'model': BaseLeNet(activation='relu', use_batchnorm=False, pool_type='avg', kernel_size=7, channels1=6, channels2=16)
        },
        # 实验5: 不同输出通道数
        {
            'name': '通道 12-32',
            'model': BaseLeNet(activation='relu', use_batchnorm=False, pool_type='avg', kernel_size=5, channels1=12, channels2=32)
        },
        # 实验6: Max Pooling
        {
            'name': 'Max Pooling',
            'model': BaseLeNet(activation='relu', use_batchnorm=False, pool_type='max', kernel_size=5, channels1=6, channels2=16)
        }
    ]
    
    # 运行所有实验
    for exp in experiments:
        result = train_and_evaluate(exp, train_loader, test_loader, epochs)
        results[exp['name']] = result
    
    # 保存结果路径
    save_dir = r"C:\Users\Administrator\Desktop\shendu\CNN"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 绘制所有结果
    plot_comparison(results, "Fashion-MNIST实验结果对比", 
                   os.path.join(save_dir, "Fashion_MNIST_实验结果.png"))
    
    # 分组绘制结果以便更好比较
    # 1. 激活函数比较
    activation_results = {k: v for k, v in results.items() if k in ['原始LeNet (Sigmoid)', 'LeNet with ReLU', 'BatchNorm + ReLU']}
    if activation_results:
        plot_comparison(activation_results, "激活函数比较", 
                       os.path.join(save_dir, "激活函数比较.png"))
    
    # 2. 卷积核大小比较  
    kernel_results = {k: v for k, v in results.items() if '卷积核' in k}
    if kernel_results:
        kernel_results['卷积核 5x5'] = results['LeNet with ReLU']  # 添加基准
        plot_comparison(kernel_results, "卷积核大小比较",
                       os.path.join(save_dir, "卷积核大小比较.png"))
    
    # 3. 通道数比较
    channel_results = {
        '通道 6-16': results['LeNet with ReLU'],
        '通道 12-32': results['通道 12-32']
    }
    plot_comparison(channel_results, "通道数量比较",
                   os.path.join(save_dir, "通道数量比较.png"))
    
    # 4. 池化方法比较
    pool_results = {
        'Avg Pooling': results['LeNet with ReLU'],
        'Max Pooling': results['Max Pooling']
    }
    plot_comparison(pool_results, "池化方法比较",
                   os.path.join(save_dir, "池化方法比较.png"))
    
    # 打印最终测试误差比较
    print("\n" + "=" * 60)
    print("最终测试误差比较:")
    print("=" * 60)
    for name, data in results.items():
        final_test_error = data['test_error'][-1]
        print(f"{name:20}: {final_test_error:.2f}%")
    
    # 保存实验结果到文件
    result_file = os.path.join(save_dir, "实验结果汇总.txt")
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("Fashion-MNIST卷积网络实验结果汇总\n")
        f.write("=" * 50 + "\n")
        for name, data in results.items():
            final_test_error = data['test_error'][-1]
            f.write(f"{name:20}: {final_test_error:.2f}%\n")
    
    print(f"\n实验结果已保存到: {save_dir}")

if __name__ == "__main__":
    main()