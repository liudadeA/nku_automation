import torch
from PFNet import PFNet

# Test PFNet with RGB-D input
dummy_input = torch.randn(1, 4, 416, 416)  # (batch, 4 channels, H, W)
print(f"Dummy input shape: {dummy_input.shape}")

# Load the model
model = PFNet(backbone_path='./backbone/pvt_v2_b2.pth')
model.eval()
print("Model loaded successfully!")

# Forward pass
with torch.no_grad():
    predict_4, predict_3, predict_2, predict_1, edge_output = model(dummy_input)

# Check output shapes
print(f"Predict 1 shape: {predict_1.shape}")
print(f"Predict 2 shape: {predict_2.shape}")
print(f"Predict 3 shape: {predict_3.shape}")
print(f"Predict 4 shape: {predict_4.shape}")
print(f"Edge output shape: {edge_output.shape}")

print("\nTest completed successfully!")
