import torch

# Path to the pretrained weights
weight_path = './backbone/pvt_v2_b2.pth'

# Load the weights
state_dict = torch.load(weight_path, weights_only=False)

# Print all keys in the state dict
print("Keys in the pretrained weights:")
for key in state_dict.keys():
    print(f"  {key}")

# If we find patch embedding keys, print their shapes
print("\nPatch embedding related keys and shapes:")
for key in state_dict.keys():
    if 'patch' in key.lower() or 'proj' in key.lower():
        print(f"  {key}: {state_dict[key].shape}")
