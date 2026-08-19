import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import (StepLR, ExponentialLR, CosineAnnealingLR, LambdaLR)
import torchvision
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import os

# Set random seed for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# Check if GPU is available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Data preprocessing
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

# Load Fashion-MNIST dataset
train_dataset = torchvision.datasets.FashionMNIST(root='E:\shendu\MLP\data', train=True, 
                                                  download=True, transform=transform)
test_dataset = torchvision.datasets.FashionMNIST(root='E:\shendu\MLP\data', train=False, 
                                                 download=True, transform=transform)

# Define neural network model
class FashionMNISTModel(nn.Module):
    def __init__(self):
        super(FashionMNISTModel, self).__init__()
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(28*28, 512)
        self.relu1 = nn.ReLU()
        self.fc2 = nn.Linear(512, 256)
        self.relu2 = nn.ReLU()
        self.fc3 = nn.Linear(256, 128)
        self.relu3 = nn.ReLU()
        self.fc4 = nn.Linear(128, 10)
    
    def forward(self, x):
        x = self.flatten(x)
        x = self.relu1(self.fc1(x))
        x = self.relu2(self.fc2(x))
        x = self.relu3(self.fc3(x))
        x = self.fc4(x)
        return x

# Weight initialization function
def init_weights(m, init_type='gaussian'):
    if isinstance(m, nn.Linear):
        if init_type == 'gaussian':
            nn.init.normal_(m.weight, mean=0, std=0.01)
        elif init_type == 'xavier':
            nn.init.xavier_uniform_(m.weight)
        elif init_type == 'he':
            nn.init.kaiming_uniform_(m.weight, nonlinearity='relu')
        nn.init.zeros_(m.bias)

# Learning rate scheduler function
def get_lr_scheduler(optimizer, strategy='constant', epochs=10, warmup_epochs=0, 
                   base_lr=0.01, final_lr=0.0001):
    if strategy == 'constant':
        return LambdaLR(optimizer, lr_lambda=lambda epoch: 1.0)
    elif strategy == 'exponential':
        return ExponentialLR(optimizer, gamma=0.95)
    elif strategy == 'step':
        return StepLR(optimizer, step_size=3, gamma=0.1)
    elif strategy == 'polynomial':
        def lr_lambda(epoch):
            return (1 - epoch / epochs) ** 2
        return LambdaLR(optimizer, lr_lambda=lr_lambda)
    elif strategy == 'linear':
        def lr_lambda(epoch):
            return 1 - (epoch / epochs)
        return LambdaLR(optimizer, lr_lambda=lr_lambda)
    elif strategy == 'cosine':
        return CosineAnnealingLR(optimizer, T_max=epochs, eta_min=final_lr)
    elif strategy == 'warmup_cosine':
        def lr_lambda(epoch):
            if epoch < warmup_epochs:
                return epoch / warmup_epochs
            else:
                progress = (epoch - warmup_epochs) / (epochs - warmup_epochs)
                return 0.5 * (1 + np.cos(np.pi * progress)) * (1 - final_lr / base_lr) + final_lr / base_lr
        return LambdaLR(optimizer, lr_lambda=lr_lambda)
    else:
        raise ValueError(f"Unknown learning rate strategy: {strategy}")

# Training function
def train_model(model, train_loader, test_loader, optimizer, scheduler, criterion, epochs=10):
    train_losses = []
    train_accuracies = []
    test_accuracies = []
    
    model.to(device)
    
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        # Use tqdm to display training progress
        with tqdm(train_loader, unit='batch') as pbar:
            pbar.set_description(f"Epoch {epoch+1}/{epochs}")
            
            for images, labels in pbar:
                images, labels = images.to(device), labels.to(device)
                
                # Forward propagation
                outputs = model(images)
                loss = criterion(outputs, labels)
                
                # Backward propagation and optimization
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                # Calculate loss and accuracy
                running_loss += loss.item() * images.size(0)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()
                
                # Update progress bar
                pbar.set_postfix({'Loss': loss.item(), 'Accuracy': 100.*correct/total})
        
        # Calculate epoch loss and accuracy
        epoch_loss = running_loss / len(train_loader.dataset)
        epoch_acc = 100 * correct / total
        train_losses.append(epoch_loss)
        train_accuracies.append(epoch_acc)
        
        # Evaluate on test set
        test_acc = evaluate_model(model, test_loader)
        test_accuracies.append(test_acc)
        
        # Update learning rate
        scheduler.step()
        
        print(f"Epoch {epoch+1}/{epochs}: Loss: {epoch_loss:.4f}, Train Acc: {epoch_acc:.2f}%, Test Acc: {test_acc:.2f}%")
    
    return train_losses, train_accuracies, test_accuracies

# Evaluation function
def evaluate_model(model, test_loader):
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
    
    return 100 * correct / total

# Plotting function
def plot_results(results_dict, title, ylabel, save_path=None):
    plt.figure(figsize=(12, 6))
    
    for name, values in results_dict.items():
        plt.plot(values, label=name)
    
    plt.title(title)
    plt.xlabel('Epoch')
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    plt.show()

# Task 1: Train model using SGD with different parameters
def task1_sgd():
    print("\n=== Task 1: Train model using SGD ===")
    
    # 1.1 Different initialization methods
    print("\n1.1 Different initialization methods")
    init_methods = ['gaussian', 'xavier', 'he']
    init_results = {}
    
    for init_type in init_methods:
        print(f"\nUsing {init_type} initialization")
        model = FashionMNISTModel()
        model.apply(lambda m: init_weights(m, init_type))
        
        batch_size = 64
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.SGD(model.parameters(), lr=0.01)
        scheduler = get_lr_scheduler(optimizer, strategy='constant', epochs=10)
        
        train_losses, train_acc, test_acc = train_model(model, train_loader, test_loader, optimizer, scheduler, criterion, epochs=10)
        
        init_results[f'{init_type}_loss'] = train_losses
        init_results[f'{init_type}_train_acc'] = train_acc
        init_results[f'{init_type}_test_acc'] = test_acc
    
    # Plot initialization method comparison
    plot_results(
        {k: v for k, v in init_results.items() if 'loss' in k}, 
        'Loss Functions with Different Initializations', 'Loss', 'sgd_init_loss.png'
    )
    
    plot_results(
        {k: v for k, v in init_results.items() if 'train_acc' in k}, 
        'Training Accuracies with Different Initializations', 'Accuracy (%)', 'sgd_init_train_acc.png'
    )
    
    plot_results(
        {k: v for k, v in init_results.items() if 'test_acc' in k}, 
        'Test Accuracies with Different Initializations', 'Accuracy (%)', 'sgd_init_test_acc.png'
    )
    
    # 1.2 Different batch sizes
    print("\n1.2 Different batch sizes")
    batch_sizes = [1, 32, 64, 128, len(train_dataset)]  # s=1, s=total samples, and other sizes
    batch_results = {}
    
    for batch_size in batch_sizes:
        print(f"\nUsing batch size: {batch_size}")
        model = FashionMNISTModel()
        model.apply(lambda m: init_weights(m, 'he'))
        
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=64, shuffle=False)
        
        criterion = nn.CrossEntropyLoss()
        # Adjust learning rate based on batch size
        lr = 0.01 if batch_size <= 128 else 0.1  # Use larger learning rate for large batch sizes
        optimizer = optim.SGD(model.parameters(), lr=lr)
        scheduler = get_lr_scheduler(optimizer, strategy='constant', epochs=10)
        
        train_losses, train_acc, test_acc = train_model(model, train_loader, test_loader, optimizer, scheduler, criterion, epochs=10)
        
        batch_results[f'batch_{batch_size}_loss'] = train_losses
        batch_results[f'batch_{batch_size}_train_acc'] = train_acc
        batch_results[f'batch_{batch_size}_test_acc'] = test_acc
    
    # Plot batch size comparison
    plot_results(
        {k: v for k, v in batch_results.items() if 'loss' in k}, 
        'Loss Functions with Different Batch Sizes', 'Loss', 'sgd_batch_loss.png'
    )
    
    plot_results(
        {k: v for k, v in batch_results.items() if 'train_acc' in k}, 
        'Training Accuracies with Different Batch Sizes', 'Accuracy (%)', 'sgd_batch_train_acc.png'
    )
    
    plot_results(
        {k: v for k, v in batch_results.items() if 'test_acc' in k}, 
        'Test Accuracies with Different Batch Sizes', 'Accuracy (%)', 'sgd_batch_test_acc.png'
    )
    
    # 1.3 Different learning rate strategies
    print("\n1.3 Different learning rate strategies")
    lr_strategies = ['constant', 'exponential', 'step', 'polynomial', 'linear', 'cosine', 'warmup_cosine']
    lr_results = {}
    
    for strategy in lr_strategies:
        print(f"\nUsing learning rate strategy: {strategy}")
        model = FashionMNISTModel()
        model.apply(lambda m: init_weights(m, 'he'))
        
        batch_size = 64
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.SGD(model.parameters(), lr=0.01)
        scheduler = get_lr_scheduler(optimizer, strategy=strategy, epochs=10, warmup_epochs=2, base_lr=0.01, final_lr=0.0001)
        
        train_losses, train_acc, test_acc = train_model(model, train_loader, test_loader, optimizer, scheduler, criterion, epochs=10)
        
        lr_results[f'{strategy}_loss'] = train_losses
        lr_results[f'{strategy}_train_acc'] = train_acc
        lr_results[f'{strategy}_test_acc'] = test_acc
    
    # Plot learning rate strategy comparison
    plot_results(
        {k: v for k, v in lr_results.items() if 'loss' in k}, 
        'Loss Functions with Different LR Strategies', 'Loss', 'sgd_lr_loss.png'
    )
    
    plot_results(
        {k: v for k, v in lr_results.items() if 'train_acc' in k}, 
        'Training Accuracies with Different LR Strategies', 'Accuracy (%)', 'sgd_lr_train_acc.png'
    )
    
    plot_results(
        {k: v for k, v in lr_results.items() if 'test_acc' in k}, 
        'Test Accuracies with Different LR Strategies', 'Accuracy (%)', 'sgd_lr_test_acc.png'
    )

# Task 2: Train model using Adam
def task2_adam():
    print("\n=== Task 2: Train model using Adam ===")
    
    model = FashionMNISTModel()
    model.apply(lambda m: init_weights(m, 'he'))
    
    batch_size = 64
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = get_lr_scheduler(optimizer, strategy='warmup_cosine', epochs=10, warmup_epochs=2, base_lr=0.001, final_lr=0.00001)
    
    train_losses, train_acc, test_acc = train_model(model, train_loader, test_loader, optimizer, scheduler, criterion, epochs=10)
    
    # Plot Adam results
    adam_results = {
        'adam_loss': train_losses,
        'adam_train_acc': train_acc,
        'adam_test_acc': test_acc
    }
    
    plot_results({'adam_loss': train_losses}, 'Adam Loss Function', 'Loss', 'adam_loss.png')
    plot_results({'adam_train_acc': train_acc}, 'Adam Training Accuracy', 'Accuracy (%)', 'adam_train_acc.png')
    plot_results({'adam_test_acc': test_acc}, 'Adam Test Accuracy', 'Accuracy (%)', 'adam_test_acc.png')

# Task 3: Train model using SGD + momentum
def task3_sgd_momentum():
    print("\n=== Task 3: Train model using SGD + momentum ===")
    
    # 3.1 He initialization + warmup + cosine decay
    print("\n3.1 He initialization + warmup + cosine decay")
    model = FashionMNISTModel()
    model.apply(lambda m: init_weights(m, 'he'))
    
    batch_size = 64
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
    scheduler = get_lr_scheduler(optimizer, strategy='warmup_cosine', epochs=10, warmup_epochs=2, base_lr=0.01, final_lr=0.0001)
    
    train_losses, train_acc, test_acc = train_model(model, train_loader, test_loader, optimizer, scheduler, criterion, epochs=10)
    
    # 3.2 Different weight decay rates
    print("\n3.2 Different weight decay rates")
    weight_decays = [0, 0.0001, 0.001, 0.01]
    wd_results = {}
    
    for wd in weight_decays:
        print(f"\nUsing weight decay rate: {wd}")
        model = FashionMNISTModel()
        model.apply(lambda m: init_weights(m, 'he'))
        
        optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9, weight_decay=wd)
        scheduler = get_lr_scheduler(optimizer, strategy='warmup_cosine', epochs=10, warmup_epochs=2, base_lr=0.01, final_lr=0.0001)
        
        losses, train_acc_wd, test_acc_wd = train_model(model, train_loader, test_loader, optimizer, scheduler, criterion, epochs=10)
        
        wd_results[f'wd_{wd}_loss'] = losses
        wd_results[f'wd_{wd}_train_acc'] = train_acc_wd
        wd_results[f'wd_{wd}_test_acc'] = test_acc_wd
    
    # Plot weight decay comparison
    plot_results(
        {k: v for k, v in wd_results.items() if 'loss' in k}, 
        'Loss Functions with Different Weight Decays', 'Loss', 'sgd_momentum_wd_loss.png'
    )
    
    plot_results(
        {k: v for k, v in wd_results.items() if 'test_acc' in k}, 
        'Test Accuracies with Different Weight Decays', 'Accuracy (%)', 'sgd_momentum_wd_test_acc.png'
    )
    
    # 3.3 Nesterov acceleration
    print("\n3.3 Nesterov acceleration")
    model = FashionMNISTModel()
    model.apply(lambda m: init_weights(m, 'he'))
    
    optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9, weight_decay=0.0001, nesterov=True)
    scheduler = get_lr_scheduler(optimizer, strategy='warmup_cosine', epochs=10, warmup_epochs=2, base_lr=0.01, final_lr=0.0001)
    
    train_losses_nesterov, train_acc_nesterov, test_acc_nesterov = train_model(model, train_loader, test_loader, optimizer, scheduler, criterion, epochs=10)
    
    # Compare momentum and Nesterov
    momentum_results = {
        'momentum_loss': wd_results['wd_0.0001_loss'],
        'nesterov_loss': train_losses_nesterov
    }
    
    plot_results(momentum_results, 'Momentum vs Nesterov Loss Functions', 'Loss', 'sgd_momentum_vs_nesterov_loss.png')

# Task 4: Train model using AdamW
def task4_adamw():
    print("\n=== Task 4: Train model using AdamW ===")
    
    # Compare weight decay in Adam and AdamW
    optimizers = ['Adam', 'AdamW']
    adam_w_results = {}
    
    for opt_name in optimizers:
        print(f"\nUsing {opt_name}")
        model = FashionMNISTModel()
        model.apply(lambda m: init_weights(m, 'he'))
        
        batch_size = 64
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
        
        criterion = nn.CrossEntropyLoss()
        
        if opt_name == 'Adam':
            optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=0.01)
        else:
            optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        
        scheduler = get_lr_scheduler(optimizer, strategy='warmup_cosine', epochs=10, warmup_epochs=2, base_lr=0.001, final_lr=0.00001)
        
        train_losses, train_acc, test_acc = train_model(model, train_loader, test_loader, optimizer, scheduler, criterion, epochs=10)
        
        adam_w_results[f'{opt_name}_loss'] = train_losses
        adam_w_results[f'{opt_name}_train_acc'] = train_acc
        adam_w_results[f'{opt_name}_test_acc'] = test_acc
    
    # Plot Adam vs AdamW comparison
    plot_results(
        {k: v for k, v in adam_w_results.items() if 'loss' in k}, 
        'Adam vs AdamW Loss Functions', 'Loss', 'adam_vs_adamw_loss.png'
    )
    
    plot_results(
        {k: v for k, v in adam_w_results.items() if 'test_acc' in k}, 
        'Adam vs AdamW Test Accuracies', 'Accuracy (%)', 'adam_vs_adamw_test_acc.png'
    )

if __name__ == '__main__':
    # Create output directory
    if not os.path.exists('results'):
        os.makedirs('results')
    
    # Run all tasks
    task1_sgd()
    #task2_adam()
    #task3_sgd_momentum()
    #task4_adamw()
    
    print("\nAll tasks completed!")
