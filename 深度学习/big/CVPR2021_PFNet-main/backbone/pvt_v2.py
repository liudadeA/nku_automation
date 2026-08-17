"""
 @Time    : 2021/7/6 09:53
 @Author  : Haiyang Mei
 @E-mail  : mhy666@mail.dlut.edu.cn

 @Project : CVPR2021_PFNet
 @File    : pvt_v2.py
 @Function: PVTv2 Model File

"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from functools import partial

class Mlp(nn.Module):
    def __init__(self, in_features, hidden_features=None, out_features=None, act_layer=nn.GELU, drop=0.):
        super().__init__()
        out_features = out_features or in_features
        hidden_features = hidden_features or in_features
        self.fc1 = nn.Linear(in_features, hidden_features)
        self.dwconv = nn.Conv2d(hidden_features, hidden_features, 3, padding=1, groups=hidden_features)
        self.act = act_layer()
        self.fc2 = nn.Linear(hidden_features, out_features)
        self.drop = nn.Dropout(drop)
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.trunc_normal_(m.weight, std=.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode='fan_out')
            if m.bias is not None:
                nn.init.zeros_(m.bias)

    def forward(self, x):
        B, C, H, W = x.shape
        x = x.flatten(2).transpose(1, 2)  # (B, H*W, C)
        x = self.fc1(x)
        x = x.transpose(1, 2).reshape(B, -1, H, W)  # (B, C, H, W)
        x = self.dwconv(x)
        x = x.flatten(2).transpose(1, 2)  # (B, H*W, C)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = x.transpose(1, 2).reshape(B, -1, H, W)  # (B, C, H, W)
        x = self.drop(x)
        return x

class Attention(nn.Module):
    def __init__(self, dim, num_heads=8, qkv_bias=False, qk_scale=None, attn_drop=0., proj_drop=0., sr_ratio=1):
        super().__init__()
        assert dim % num_heads == 0, f"dim {dim} should be divided by num_heads {num_heads}."
        self.dim = dim
        self.num_heads = num_heads
        head_dim = dim // num_heads
        self.scale = qk_scale or head_dim ** -0.5

        self.q = nn.Linear(dim, dim, bias=qkv_bias)
        self.kv = nn.Linear(dim, dim * 2, bias=qkv_bias)
        self.attn_drop = nn.Dropout(attn_drop)
        self.proj = nn.Linear(dim, dim)
        self.proj_drop = nn.Dropout(proj_drop)

        self.sr_ratio = sr_ratio
        if sr_ratio > 1:
            self.sr = nn.Conv2d(dim, dim, kernel_size=sr_ratio, stride=sr_ratio)
            self.norm = nn.LayerNorm(dim)

        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.trunc_normal_(m.weight, std=.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode='fan_out')
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.LayerNorm):
            nn.init.zeros_(m.bias)
            nn.init.ones_(m.weight)

    def forward(self, x):
        B, C, H, W = x.shape
        x = x.flatten(2).transpose(1, 2)  # (B, H*W, C)
        
        q = self.q(x).reshape(B, -1, self.num_heads, C // self.num_heads).permute(0, 2, 1, 3)

        if self.sr_ratio > 1:
            x_ = x.permute(0, 2, 1).reshape(B, C, H, W)
            x_ = self.sr(x_).reshape(B, C, -1).permute(0, 2, 1)
            x_ = self.norm(x_)
            kv = self.kv(x_).reshape(B, -1, 2, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
        else:
            kv = self.kv(x).reshape(B, -1, 2, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
        k, v = kv[0], kv[1]

        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)

        x = (attn @ v).transpose(1, 2).reshape(B, -1, C)
        x = self.proj(x)
        x = self.proj_drop(x)
        x = x.transpose(1, 2).reshape(B, C, H, W)
        return x

class Block(nn.Module):
    def __init__(self, dim, num_heads, mlp_ratio=4., qkv_bias=False, qk_scale=None, drop=0., attn_drop=0.,
                 drop_path=0., act_layer=nn.GELU, norm_layer=nn.BatchNorm2d, sr_ratio=1):
        super().__init__()
        self.norm1 = norm_layer(dim)
        self.attn = Attention(
            dim, num_heads=num_heads, qkv_bias=qkv_bias, qk_scale=qk_scale, attn_drop=attn_drop, proj_drop=drop, sr_ratio=sr_ratio)
        self.drop_path = nn.Identity()
        self.norm2 = norm_layer(dim)
        mlp_hidden_dim = int(dim * mlp_ratio)
        self.mlp = Mlp(in_features=dim, hidden_features=mlp_hidden_dim, act_layer=act_layer, drop=drop)
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.BatchNorm2d):
            nn.init.zeros_(m.bias)
            nn.init.ones_(m.weight)

    def forward(self, x):
        x = x + self.drop_path(self.attn(self.norm1(x)))
        x = x + self.drop_path(self.mlp(self.norm2(x)))
        return x

class PatchEmbed(nn.Module):
    def __init__(self, img_size=224, patch_size=4, in_chans=3, embed_dim=64, norm_layer=None):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.grid_size = (img_size // patch_size, img_size // patch_size)
        self.num_patches = self.grid_size[0] * self.grid_size[1]

        # Use the same kernel size as in the pretrained weights (7x7 for patch_embed1, 3x3 for others)
        if embed_dim == 64:  # patch_embed1
            self.proj = nn.Conv2d(in_chans, embed_dim, kernel_size=7, stride=4, padding=2)
        else:
            self.proj = nn.Conv2d(in_chans, embed_dim, kernel_size=3, stride=2, padding=1)
        self.norm = norm_layer(embed_dim) if norm_layer else nn.Identity()
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode='fan_out')
            if m.bias is not None:
                nn.init.zeros_(m.bias)

    def forward(self, x):
        B, C, H, W = x.shape
        x = self.proj(x)
        x = self.norm(x)
        return x

class PyramidVisionTransformerV2(nn.Module):
    def __init__(self, img_size=224, patch_size=4, in_chans=4, num_classes=1000, embed_dims=[64, 128, 320, 512],
                 num_heads=[1, 2, 5, 8], mlp_ratios=[8, 8, 4, 4], qkv_bias=True, qk_scale=None,
                 drop_rate=0., attn_drop_rate=0., drop_path_rate=0., norm_layer=nn.BatchNorm2d,
                 depths=[3, 4, 6, 3], sr_ratios=[8, 4, 2, 1]):
        super().__init__()
        self.num_classes = num_classes
        self.depths = depths

        dpr = [x.item() for x in torch.linspace(0, drop_path_rate, sum(depths))]
        cur = 0

        self.patch_embed1 = PatchEmbed(
            img_size=img_size, patch_size=patch_size, in_chans=in_chans, embed_dim=embed_dims[0],
            norm_layer=norm_layer)
        self.block1 = nn.ModuleList([Block(
            dim=embed_dims[0], num_heads=num_heads[0], mlp_ratio=mlp_ratios[0], qkv_bias=qkv_bias,
            qk_scale=qk_scale, drop=drop_rate, attn_drop=attn_drop_rate, drop_path=dpr[cur + i],
            norm_layer=norm_layer, sr_ratio=sr_ratios[0])
            for i in range(depths[0])])
        self.norm1 = norm_layer(embed_dims[0])

        cur += depths[0]
        self.patch_embed2 = PatchEmbed(
            img_size=img_size // 4, patch_size=2, in_chans=embed_dims[0], embed_dim=embed_dims[1],
            norm_layer=norm_layer)
        self.block2 = nn.ModuleList([Block(
            dim=embed_dims[1], num_heads=num_heads[1], mlp_ratio=mlp_ratios[1], qkv_bias=qkv_bias,
            qk_scale=qk_scale, drop=drop_rate, attn_drop=attn_drop_rate, drop_path=dpr[cur + i],
            norm_layer=norm_layer, sr_ratio=sr_ratios[1])
            for i in range(depths[1])])
        self.norm2 = norm_layer(embed_dims[1])

        cur += depths[1]
        self.patch_embed3 = PatchEmbed(
            img_size=img_size // 8, patch_size=2, in_chans=embed_dims[1], embed_dim=embed_dims[2],
            norm_layer=norm_layer)
        self.block3 = nn.ModuleList([Block(
            dim=embed_dims[2], num_heads=num_heads[2], mlp_ratio=mlp_ratios[2], qkv_bias=qkv_bias,
            qk_scale=qk_scale, drop=drop_rate, attn_drop=attn_drop_rate, drop_path=dpr[cur + i],
            norm_layer=norm_layer, sr_ratio=sr_ratios[2])
            for i in range(depths[2])])
        self.norm3 = norm_layer(embed_dims[2])

        cur += depths[2]
        self.patch_embed4 = PatchEmbed(
            img_size=img_size // 16, patch_size=2, in_chans=embed_dims[2], embed_dim=embed_dims[3],
            norm_layer=norm_layer)
        self.block4 = nn.ModuleList([Block(
            dim=embed_dims[3], num_heads=num_heads[3], mlp_ratio=mlp_ratios[3], qkv_bias=qkv_bias,
            qk_scale=qk_scale, drop=drop_rate, attn_drop=attn_drop_rate, drop_path=dpr[cur + i],
            norm_layer=norm_layer, sr_ratio=sr_ratios[3])
            for i in range(depths[3])])
        self.norm4 = norm_layer(embed_dims[3])

        self.head = nn.Linear(embed_dims[3], num_classes) if num_classes > 0 else nn.Identity()
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.trunc_normal_(m.weight, std=.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)

    def forward_features(self, x):
        B = x.shape[0]

        x = self.patch_embed1(x)
        for blk in self.block1:
            x = blk(x)
        x = self.norm1(x)
        layer1 = x

        x = self.patch_embed2(x)
        for blk in self.block2:
            x = blk(x)
        x = self.norm2(x)
        layer2 = x

        x = self.patch_embed3(x)
        for blk in self.block3:
            x = blk(x)
        x = self.norm3(x)
        layer3 = x

        x = self.patch_embed4(x)
        for blk in self.block4:
            x = blk(x)
        x = self.norm4(x)
        layer4 = x

        return layer1, layer2, layer3, layer4

    def forward(self, x):
        layer1, layer2, layer3, layer4 = self.forward_features(x)
        return layer1, layer2, layer3, layer4

def pvt_v2_b2(backbone_path=None, pretrained=True, **kwargs):
    # For RGB-D input, we need 4 channels
    if 'in_chans' not in kwargs:
        kwargs['in_chans'] = 4
    
    model = PyramidVisionTransformerV2(
        patch_size=4, embed_dims=[64, 128, 320, 512], num_heads=[1, 2, 5, 8],
        mlp_ratios=[8, 8, 4, 4], qkv_bias=True, depths=[3, 4, 6, 3], sr_ratios=[8, 4, 2, 1],
        norm_layer=nn.BatchNorm2d, **kwargs)
    
    if pretrained and backbone_path is not None:
        print(f"Loading weights from {backbone_path}...")
        state_dict = torch.load(backbone_path, weights_only=False)
        
        # Debug: Check if the key exists
        if 'patch_embed1.proj.weight' in state_dict:
            print(f"Key 'patch_embed1.proj.weight' found, shape: {state_dict['patch_embed1.proj.weight'].shape}")
        else:
            print("Key 'patch_embed1.proj.weight' NOT found!")
            # Print first 10 keys for debugging
            print("First 10 keys in state_dict:")
            for i, key in enumerate(list(state_dict.keys())[:10]):
                print(f"  {i}: {key}")
        
        # Handle channel mismatch for patch_embed1.proj.weight
        if kwargs['in_chans'] == 4:
            print(f"Input channels set to 4, need to adjust weights")
            if 'patch_embed1.proj.weight' in state_dict and state_dict['patch_embed1.proj.weight'].shape[1] == 3:
                print("Handling channel mismatch: converting 3-channel pretrained weights to 4-channel...")
                # Average the RGB channels for the depth channel
                depth_channel = state_dict['patch_embed1.proj.weight'].mean(dim=1, keepdim=True)
                # Concatenate the depth channel to get 4 channels
                state_dict['patch_embed1.proj.weight'] = torch.cat([state_dict['patch_embed1.proj.weight'], depth_channel], dim=1)
                print(f"New shape of 'patch_embed1.proj.weight': {state_dict['patch_embed1.proj.weight'].shape}")
        
        # Load the adjusted state dict
        model.load_state_dict(state_dict, strict=False)
        print(f"From {backbone_path} Load PVTv2-b2 Weights Succeed!")
    
    return model

if __name__ == '__main__':
    model = pvt_v2_b2()
    x = torch.randn(1, 3, 224, 224)
    layer1, layer2, layer3, layer4 = model(x)
    print(layer1.shape, layer2.shape, layer3.shape, layer4.shape)
