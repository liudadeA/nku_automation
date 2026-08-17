import numpy as np
import matplotlib.pyplot as plt

# XOR 数据集
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
y = np.array([[0], [1], [1], [0]])

# 神经网络参数
input_size = 2
hidden_size = 5
output_size = 1

# 更好的参数初始化
np.random.seed(42)
W = np.random.randn(hidden_size, input_size) * np.sqrt(2.0 / input_size)  # He初始化
b = np.zeros((hidden_size, 1))
w = np.random.randn(output_size, hidden_size) * np.sqrt(2.0 / hidden_size)
b_out = np.zeros((output_size, 1))

# 超参数
learning_rate = 0.1
epochs = 10000

# 存储损失
losses = []

# 训练网络
for epoch in range(epochs):
    total_loss = 0
    
    # 随机梯度下降：逐个样本训练
    for i in range(len(X)):
        # 前向传播
        x_i = X[i].reshape(-1, 1)
        y_true = y[i]
        
        # 隐藏层
        z = np.dot(W, x_i) + b
        h = np.maximum(0, z)  # ReLU激活函数
        
        # 输出层
        y_pred = np.dot(w, h) + b_out
        
        # 计算损失
        loss = np.square(y_pred - y_true)
        total_loss += loss[0, 0]
        
        # 反向传播
        # 输出层梯度
        d_loss = 2 * (y_pred - y_true)
        
        # 输出层权重梯度
        dw = np.dot(d_loss, h.T)
        db_out = d_loss
        
        # 隐藏层梯度
        dh = np.dot(w.T, d_loss)
        # ReLU梯度
        dz = dh.copy()
        dz[z <= 0] = 0
        
        dW = np.dot(dz, x_i.T)
        db = dz
        
        # 更新参数
        w -= learning_rate * dw
        b_out -= learning_rate * db_out
        W -= learning_rate * dW
        b -= learning_rate * db
    
    # 记录平均损失
    avg_loss = total_loss / len(X)
    losses.append(avg_loss)
    
    if epoch % 1000 == 0:
        print(f"Epoch {epoch}, Loss: {avg_loss:.6f}")

# 测试网络
print("\n测试结果:")
for i in range(len(X)):
    x_i = X[i].reshape(-1, 1)
    z = np.dot(W, x_i) + b
    h = np.maximum(0, z)
    y_pred = np.dot(w, h) + b_out
    print(f"输入: {X[i]}, 预测: {y_pred[0,0]:.4f}, 真实: {y[i,0]}")

# 绘制损失曲线
plt.figure(figsize=(10, 6))
plt.plot(losses)
plt.title('Training Loss')
plt.xlabel('Epoch')
plt.ylabel('MSE Loss')
plt.yscale('log')
plt.grid(True)
plt.show()