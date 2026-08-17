import random
import time
import matplotlib.pyplot as plt
import math

# 城市数据
cities_data = [
    ("北京", 116.46, 39.92),
    ("天津", 117.2, 39.13),
    ("上海", 121.48, 31.22),
    ("重庆", 106.54, 29.59),
    ("拉萨", 91.11, 29.97),
    ("乌鲁木齐", 87.68, 43.77),
    ("银川", 106.27, 38.47),
    ("呼和浩特", 111.65, 40.82),
    ("南宁", 108.33, 22.84),
    ("哈尔滨", 126.63, 45.75),
    ("长春", 125.35, 43.88),
    ("沈阳", 123.38, 41.8),
    ("石家庄", 114.48, 38.03),
    ("太原", 112.53, 37.87),
    ("西宁", 101.74, 36.56),
    ("济南", 117, 36.65),
    ("郑州", 113.65, 34.76),
    ("南京", 118.78, 32.04),
    ("合肥", 117.27, 31.86),
    ("杭州", 120.19, 30.26),
    ("福州", 119.3, 26.08),
    ("南昌", 115.89, 28.68),
    ("长沙", 113, 28.21),
    ("武汉", 114.31, 30.52),
    ("广州", 113.23, 23.16),
    ("台北", 121.5, 25.05),
    ("海口", 110.35, 20.02),
    ("兰州", 103.73, 36.03),
    ("西安", 108.95, 34.27),
    ("成都", 104.06, 30.67),
    ("贵阳", 106.71, 26.57),
    ("昆明", 102.73, 25.04),
    ("香港", 114.1, 22.2),
    ("澳门", 113.33, 22.13)
]

# 获取前n个城市的数据
def get_cities(n):
    if n > len(cities_data):
        raise ValueError(f"城市数量不能超过{len(cities_data)}")
    return cities_data[:n]

# 计算两个城市之间的距离
def calculate_distance(city1, city2):
    lon1, lat1 = city1[1], city1[2]
    lon2, lat2 = city2[1], city2[2]
    
    # 欧式距离
    distance = math.sqrt((lon2 - lon1)**2 + (lat2 - lat1)**2)
    
    return distance

# 计算路径总长度
def calculate_path_length(path, cities):
    total_distance = 0
    n = len(path)
    for i in range(n):
        city1 = cities[path[i]]
        city2 = cities[path[(i+1) % n]]
        total_distance += calculate_distance(city1, city2)
    return total_distance

class AntColonyOptimization:
    def __init__(self, cities, n_ants=50, n_iterations=100, alpha=1.0, beta=2.0, rho=0.5, Q=100):
        self.cities = cities
        self.n = len(cities)
        self.n_ants = n_ants  # 蚂蚁数量
        self.n_iterations = n_iterations  # 迭代次数
        self.alpha = alpha  # 信息素重要程度
        self.beta = beta  # 启发式因子重要程度
        self.rho = rho  # 信息素挥发系数
        self.Q = Q  # 信息素总量
        self.pheromone = None  # 信息素矩阵
        self.visibility = None  # 启发式信息矩阵
        self.best_path = None
        self.best_distance = float('inf')
        self.iteration_best_distances = []
        
    # 初始化信息素和启发式信息矩阵
    def initialize_matrices(self):
        # 初始化信息素矩阵，所有元素初始化为1
        self.pheromone = [[1.0 for _ in range(self.n)] for _ in range(self.n)]
        
        # 初始化启发式信息矩阵，启发式信息为距离的倒数
        self.visibility = [[0.0 for _ in range(self.n)] for _ in range(self.n)]
        for i in range(self.n):
            for j in range(self.n):
                if i != j:
                    distance = calculate_distance(self.cities[i], self.cities[j])
                    self.visibility[i][j] = 1.0 / distance
    
    # 构建蚂蚁路径
    def construct_paths(self):
        paths = []
        distances = []
        
        for _ in range(self.n_ants):
            # 随机选择起始城市
            path = [random.randint(0, self.n - 1)]
            visited = set(path)
            
            # 构建路径
            while len(path) < self.n:
                current_city = path[-1]
                next_city = self.select_next_city(current_city, visited)
                path.append(next_city)
                visited.add(next_city)
            
            # 计算路径距离
            distance = calculate_path_length(path, self.cities)
            paths.append(path)
            distances.append(distance)
            
            # 更新最优解
            if distance < self.best_distance:
                self.best_distance = distance
                self.best_path = path.copy()
        
        return paths, distances
    
    # 选择下一个城市
    def select_next_city(self, current_city, visited):
        # 计算转移概率
        probabilities = []
        total = 0.0
        
        for city in range(self.n):
            if city not in visited:
                p = (self.pheromone[current_city][city] ** self.alpha) * (self.visibility[current_city][city] ** self.beta)
                probabilities.append((city, p))
                total += p
        
        # 轮盘赌选择
        r = random.random() * total
        cumulative = 0.0
        for city, p in probabilities:
            cumulative += p
            if cumulative >= r:
                return city
        
        # 如果出现意外情况，返回一个未访问的城市
        for city in range(self.n):
            if city not in visited:
                return city
    
    # 更新信息素
    def update_pheromones(self, paths, distances):
        # 信息素挥发
        for i in range(self.n):
            for j in range(self.n):
                self.pheromone[i][j] *= (1 - self.rho)
        
        # 信息素沉积
        for path, distance in zip(paths, distances):
            for i in range(self.n):
                city1 = path[i]
                city2 = path[(i + 1) % self.n]
                self.pheromone[city1][city2] += self.Q / distance
                self.pheromone[city2][city1] += self.Q / distance  # 双向更新
    
    # 运行蚁群算法
    def run(self):
        # 初始化矩阵
        self.initialize_matrices()
        
        for iteration in range(self.n_iterations):
            # 构建蚂蚁路径
            paths, distances = self.construct_paths()
            
            # 更新信息素
            self.update_pheromones(paths, distances)
            
            # 记录当前迭代的最优距离
            self.iteration_best_distances.append(self.best_distance)
            
            # 打印迭代信息
            if (iteration + 1) % 10 == 0:
                print(f"迭代 {iteration + 1}/{self.n_iterations}, 最优距离: {self.best_distance:.4f}")
        
        return self.best_path, self.best_distance, self.iteration_best_distances

# 绘制蚁群算法搜索过程中每代种群最优路径长度的变化
def plot_aco_progress(iteration_distances, params, filename="aco_progress.png"):
    # 设置支持中文的字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    plt.figure(figsize=(12, 8))
    
    # 绘制主趋势图
    plt.plot(range(len(iteration_distances)), iteration_distances, 'b-', linewidth=2, label='最优路径长度')
    
    # 标记关键迭代点
    key_iterations = [0, len(iteration_distances)//4, len(iteration_distances)//2, 3*len(iteration_distances)//4, len(iteration_distances)-1]
    for i in key_iterations:
        plt.plot(i, iteration_distances[i], 'ro', markersize=6)
        plt.text(i+1, iteration_distances[i]+0.5, f'{iteration_distances[i]:.2f}', fontsize=9)
    
    plt.xlabel("迭代次数", fontsize=12)
    plt.ylabel("最优路径长度", fontsize=12)
    plt.title(f"蚁群算法搜索过程 - 参数{params}", fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10)
    
    # 添加统计信息
    min_dist = min(iteration_distances)
    max_dist = max(iteration_distances)
    avg_dist = sum(iteration_distances)/len(iteration_distances)
    plt.figtext(0.15, 0.01, f'初始距离: {iteration_distances[0]:.4f}, 最小距离: {min_dist:.4f}, 最大距离: {max_dist:.4f}, 平均距离: {avg_dist:.4f}', 
                fontsize=10, ha='center')
    
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

# 绘制迭代过程中最优路径的变化趋势（多个关键迭代的路径对比）
def plot_iteration_paths(aco, key_iterations, cities, params, filename="iteration_paths.png"):
    # 设置支持中文的字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 重新运行算法，记录关键迭代的最优路径
    aco.initialize_matrices()
    iteration_paths = []
    iteration_distances = []
    
    for iteration in range(aco.n_iterations):
        paths, distances = aco.construct_paths()
        aco.update_pheromones(paths, distances)
        
        # 记录关键迭代的最优路径
        if iteration in key_iterations:
            iteration_paths.append(aco.best_path.copy())
            iteration_distances.append(aco.best_distance)
    
    # 创建子图展示不同迭代的路径
    n_iterations = len(key_iterations)
    fig, axes = plt.subplots(2, (n_iterations + 1) // 2, figsize=(15, 10))
    axes = axes.flatten()
    
    # 获取城市坐标
    lon = [city[1] for city in cities]
    lat = [city[2] for city in cities]
    names = [city[0] for city in cities]
    
    for i, (iteration, path, distance) in enumerate(zip(key_iterations, iteration_paths, iteration_distances)):
        ax = axes[i]
        
        # 绘制城市散点
        ax.scatter(lon, lat, c='red', marker='o', s=100)
        
        # 绘制最优路径
        for j in range(len(path)):
            city1_idx = path[j]
            city2_idx = path[(j+1) % len(path)]
            
            ax.plot(
                [lon[city1_idx], lon[city2_idx]],
                [lat[city1_idx], lat[city2_idx]],
                'b-', lw=1.5
            )
        
        # 添加城市名称标签（只显示部分重要城市）
        for j, name in enumerate(names):
            if j % 5 == 0:  # 每隔5个城市显示一个标签，避免过于拥挤
                ax.text(lon[j] + 0.1, lat[j] + 0.1, name, fontsize=8)
        
        ax.set_xlabel("经度")
        ax.set_ylabel("纬度")
        ax.set_title(f"迭代 {iteration+1} - 距离: {distance:.4f}")
        ax.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

# 绘制最优路径
def plot_best_path(best_path, cities, title, filename="best_path_aco.png"):
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    plt.figure(figsize=(12, 10))
    
    # 获取城市坐标
    lon = [city[1] for city in cities]
    lat = [city[2] for city in cities]
    names = [city[0] for city in cities]
    
    # 绘制城市散点
    plt.scatter(lon, lat, c='red', marker='o', s=100)
    
    # 绘制最优路径
    for i in range(len(best_path)):
        city1_idx = best_path[i]
        city2_idx = best_path[(i+1) % len(best_path)]
        
        plt.plot(
            [lon[city1_idx], lon[city2_idx]],
            [lat[city1_idx], lat[city2_idx]],
            'b-', lw=1.5
        )
    
    # 添加城市名称标签
    for i, name in enumerate(names):
        plt.text(lon[i] + 0.1, lat[i] + 0.1, name, fontsize=9)
    
    plt.xlabel("经度")
    plt.ylabel("纬度")
    plt.title(title)
    plt.grid(True)
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

# 主函数
def main():
    # 获取34个城市的数据
    cities_34 = get_cities(34)
    
    # 1. 蚁群算法求解34个城市的TSP问题
    print("1. 蚁群算法求解34个城市的TSP问题")
    print("参数：蚂蚁数量=50，迭代次数=100，alpha=1.0，beta=2.0，rho=0.5，Q=100")
    
    aco = AntColonyOptimization(cities_34, n_ants=50, n_iterations=100, alpha=1.0, beta=2.0, rho=0.5, Q=100)
    start_time = time.time()
    best_path, best_distance, iteration_best_distances = aco.run()
    end_time = time.time()
    
    print(f"最短路径：{[cities_34[i][0] for i in best_path]}")
    print(f"最短距离：{best_distance:.4f}")
    print(f"计算时间：{end_time - start_time:.4f}秒")
    
    # 2. 对比不同参数下的蚁群算法效果
    print("\n2. 不同参数下蚁群算法效果对比")
    
    # 记录所有测试中的最优解
    overall_best_path = best_path
    overall_best_distance = best_distance
    overall_best_distances = iteration_best_distances
    overall_best_params = {"蚂蚁数量": 50, "迭代次数": 100, "alpha": 1.0, "beta": 2.0, "rho": 0.5, "Q": 100}
    
    # 测试不同蚂蚁数量
    print("\n2.1 不同蚂蚁数量")
    print("固定参数：迭代次数=100，alpha=1.0，beta=2.0，rho=0.5，Q=100")
    ant_numbers = [30, 50, 70]
    
    for n_ants in ant_numbers:
        aco = AntColonyOptimization(cities_34, n_ants=n_ants, n_iterations=100, alpha=1.0, beta=2.0, rho=0.5, Q=100)
        path, distance, iter_distances = aco.run()
        print(f"蚂蚁数量：{n_ants}，最短距离：{distance:.4f}")
        
        # 更新全局最优解
        if distance < overall_best_distance:
            overall_best_distance = distance
            overall_best_path = path
            overall_best_distances = iter_distances
            overall_best_params = {"蚂蚁数量": n_ants, "迭代次数": 100, "alpha": 1.0, "beta": 2.0, "rho": 0.5, "Q": 100}
    
    # 测试不同信息素挥发系数
    print("\n2.2 不同信息素挥发系数")
    print("固定参数：蚂蚁数量=50，迭代次数=100，alpha=1.0，beta=2.0，Q=100")
    rhos = [0.3, 0.5, 0.7]
    
    for rho in rhos:
        aco = AntColonyOptimization(cities_34, n_ants=50, n_iterations=100, alpha=1.0, beta=2.0, rho=rho, Q=100)
        path, distance, iter_distances = aco.run()
        print(f"信息素挥发系数：{rho}，最短距离：{distance:.4f}")
        
        # 更新全局最优解
        if distance < overall_best_distance:
            overall_best_distance = distance
            overall_best_path = path
            overall_best_distances = iter_distances
            overall_best_params = {"蚂蚁数量": 50, "迭代次数": 100, "alpha": 1.0, "beta": 2.0, "rho": rho, "Q": 100}
    
    # 测试不同信息素因子alpha
    print("\n2.3 不同信息素因子alpha")
    print("固定参数：蚂蚁数量=50，迭代次数=100，beta=2.0，rho=0.5，Q=100")
    alphas = [0.5, 1.0, 1.5]
    
    for alpha in alphas:
        aco = AntColonyOptimization(cities_34, n_ants=50, n_iterations=100, alpha=alpha, beta=2.0, rho=0.5, Q=100)
        path, distance, iter_distances = aco.run()
        print(f"信息素因子alpha：{alpha}，最短距离：{distance:.4f}")
        
        # 更新全局最优解
        if distance < overall_best_distance:
            overall_best_distance = distance
            overall_best_path = path
            overall_best_distances = iter_distances
            overall_best_params = {"蚂蚁数量": 50, "迭代次数": 100, "alpha": alpha, "beta": 2.0, "rho": 0.5, "Q": 100}
    
    # 测试不同启发函数因子beta
    print("\n2.4 不同启发函数因子beta")
    print("固定参数：蚂蚁数量=50，迭代次数=100，alpha=1.0，rho=0.5，Q=100")
    betas = [1.0, 2.0, 3.0]
    
    for beta in betas:
        aco = AntColonyOptimization(cities_34, n_ants=50, n_iterations=100, alpha=1.0, beta=beta, rho=0.5, Q=100)
        path, distance, iter_distances = aco.run()
        print(f"启发函数因子beta：{beta}，最短距离：{distance:.4f}")
        
        # 更新全局最优解
        if distance < overall_best_distance:
            overall_best_distance = distance
            overall_best_path = path
            overall_best_distances = iter_distances
            overall_best_params = {"蚂蚁数量": 50, "迭代次数": 100, "alpha": 1.0, "beta": beta, "rho": 0.5, "Q": 100}
    
    # 输出全局最优解
    print("\n全局最优解：")
    print(f"参数：{overall_best_params}")
    print(f"最短距离：{overall_best_distance:.4f}")
    print(f"最短路径：{[cities_34[i][0] for i in overall_best_path]}")
    
    # 3. 可视化蚁群算法搜索过程
    print("\n3. 蚁群算法可视化")
    
    # 绘制每代种群最优路径长度的变化
    plot_aco_progress(overall_best_distances, overall_best_params, "aco_progress_best.png")
    
    # 绘制关键迭代的最优路径变化趋势
    key_iterations = [0, 20, 40, 60, 80, 99]  # 选择关键迭代点
    print(f"\n绘制关键迭代点{[i+1 for i in key_iterations]}的最优路径变化趋势...")
    
    # 转换中文参数名为英文参数名
    param_mapping = {
        '蚂蚁数量': 'n_ants',
        '迭代次数': 'n_iterations',
        'alpha': 'alpha',
        'beta': 'beta',
        'rho': 'rho',
        'Q': 'Q'
    }
    
    # 使用最优参数重新创建ACO实例
    english_params = {param_mapping[key]: value for key, value in overall_best_params.items()}
    best_aco = AntColonyOptimization(cities_34, **english_params)
    plot_iteration_paths(best_aco, key_iterations, cities_34, overall_best_params, "iteration_paths_best.png")
    
    # 绘制最优路径
    plot_best_path(overall_best_path, cities_34, f"蚁群算法最优路径{overall_best_distance:.4f}", "best_path_aco.png")
    
    print("\n可视化完成！生成的文件：")
    print("- aco_progress_best.png：展示搜索过程中种群最优路径长度的变化趋势")
    print("- iteration_paths_best.png：展示关键迭代点的最优路径变化")
    print("- best_path_aco.png：展示最终最优路径")

if __name__ == "__main__":
    main()