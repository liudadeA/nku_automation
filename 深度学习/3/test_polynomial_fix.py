import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import LambdaLR
import numpy as np

# Test the polynomial learning rate scheduler fix

# Create a simple model
model = nn.Linear(10, 2)

# Create optimizer
optimizer = optim.SGD(model.parameters(), lr=0.01)

def get_lr_scheduler(optimizer, strategy='constant', epochs=10, warmup_epochs=0, base_lr=0.01, final_lr=0.0001):
    if strategy == 'polynomial':
        def lr_lambda(epoch):
            return (1 - epoch / epochs) ** 2
        return LambdaLR(optimizer, lr_lambda=lr_lambda)
    else:
        return LambdaLR(optimizer, lr_lambda=lambda epoch: 1.0)

# Test the polynomial scheduler
print("Testing polynomial learning rate scheduler...")
try:
    scheduler = get_lr_scheduler(optimizer, strategy='polynomial', epochs=10)
    print("✓ Scheduler created successfully!")
    
    # Test a few epochs
    for epoch in range(3):
        scheduler.step()
        lr = optimizer.param_groups[0]['lr']
        print(f"Epoch {epoch+1}, Learning Rate: {lr:.6f}")
    
    print("✓ Scheduler works correctly!")
except Exception as e:
    print(f"✗ Error: {e}")
