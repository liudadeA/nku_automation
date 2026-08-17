import itertools
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

def exhaustive_search(cities):
    n = len(cities)

    # 生成所有可能的路径排列
    cities_indices = list(range(n))
    shortest_path = None
    shortest_distance = float('inf')
    
    # 固定第一个城市，生成其余城市的所有排列
    for perm in itertools.permutations(cities_indices[1:]):
        path = [cities_indices[0]] + list(perm)
        distance = calculate_path_length(path, cities)
        
        if distance < shortest_distance:
            shortest_distance = distance
            shortest_path = path
    
    return shortest_path, shortest_distance

class GeneticAlgorithm:
    def __init__(self, cities, population_size=100, crossover_rate=0.8, mutation_rate=0.05, max_generations=1000):
        self.cities = cities
        self.n = len(cities)
        self.population_size = population_size
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.max_generations = max_generations
        self.population = []
        self.fitness = []
        self.best_path = None
        self.best_distance = float('inf')
        self.generation_best_distances = []
    
    # 初始化种群
    def initialize_population(self):
        self.population = []
        for _ in range(self.population_size):
            # 生成随机路径
            path = list(range(self.n))
            random.shuffle(path)
            self.population.append(path)
    
    # 计算适应度
    def calculate_fitness(self):
        self.fitness = []
        for path in self.population:
            distance = calculate_path_length(path, self.cities)
            # 使用距离的倒数作为适应度，确保距离越短适应度越高
            fitness_value = 1 / distance
            self.fitness.append(fitness_value)
    
    # 轮盘赌选择
    def selection(self):
        total_fitness = sum(self.fitness)
        selection_probs = [f / total_fitness for f in self.fitness]
        
        selected = []
        for _ in range(self.population_size):
            # 轮盘赌选择
            r = random.random()
            cumulative_prob = 0
            for i, prob in enumerate(selection_probs):
                cumulative_prob += prob
                if r <= cumulative_prob:
                    selected.append(self.population[i])
                    break
        
        self.population = selected
    
    # 交叉
    def crossover(self):
        new_population = []
        
        for i in range(0, self.population_size, 2):
            parent1 = self.population[i]
            parent2 = self.population[i+1] if i+1 < self.population_size else self.population[0]
            
            if random.random() < self.crossover_rate:
                # 选择交叉点
                point1 = random.randint(0, self.n - 1)
                point2 = random.randint(0, self.n - 1)
                start, end = min(point1, point2), max(point1, point2)
                
                # 创建子代
                child1 = [-1] * self.n
                child2 = [-1] * self.n
                
                # 复制交叉区域
                child1[start:end+1] = parent1[start:end+1]
                child2[start:end+1] = parent2[start:end+1]
                
                # 填充剩余部分
                self._fill_child(child1, parent2, start, end)
                self._fill_child(child2, parent1, start, end)
                
                new_population.extend([child1, child2])
            else:
                new_population.extend([parent1, parent2])
        
        # 确保种群大小不变
        self.population = new_population[:self.population_size]
    
    # 辅助函数：填充交叉后剩余的基因
    def _fill_child(self, child, parent, start, end):
        n = self.n
        current_pos = (end + 1) % n
        parent_pos = (end + 1) % n
        
        while -1 in child:
            if parent[parent_pos] not in child:
                child[current_pos] = parent[parent_pos]
                current_pos = (current_pos + 1) % n
            parent_pos = (parent_pos + 1) % n
    
    # 变异操作
    def mutation(self):
        for i in range(self.population_size):
            if random.random() < self.mutation_rate:
                # 选择两个不同的位置进行交换
                pos1 = random.randint(0, self.n - 1)
                pos2 = random.randint(0, self.n - 1)
                while pos1 == pos2:
                    pos2 = random.randint(0, self.n - 1)
                
                # 交换位置
                self.population[i][pos1], self.population[i][pos2] = self.population[i][pos2], self.population[i][pos1]
    
    # 更新最优解
    def update_best_solution(self):
        for i in range(self.population_size):
            path = self.population[i]
            distance = calculate_path_length(path, self.cities)
            
            if distance < self.best_distance:
                self.best_distance = distance
                self.best_path = path.copy()
    
    # 运行遗传算法
    def run(self):
        # 初始化种群
        self.initialize_population()
        
        for generation in range(self.max_generations):
            # 计算适应度
            self.calculate_fitness()
            
            # 更新最优解
            self.update_best_solution()
            
            # 记录当前代的最优距离
            current_best = min([calculate_path_length(path, self.cities) for path in self.population])
            self.generation_best_distances.append(current_best)
            
            # 保留精英个体
            elite_size = 2
            elites = elitism(self.population, self.fitness, elite_size)
            
            # 选择
            self.selection()
            
            # 交叉
            self.crossover()
            
            # 变异
            self.mutation()
            
            # 将精英个体放回种群
            for i in range(elite_size):
                if i < len(self.population):
                    self.population[i] = elites[i].copy()
        
        self.calculate_fitness()
        self.update_best_solution()
        
        return self.best_path, self.best_distance, self.generation_best_distances

# 精英保留策略：保留当前种群中最优的个体
def elitism(population, fitness, elite_size=2):
    # 适应度排序
    sorted_population = sorted(zip(population, fitness), key=lambda x: x[1], reverse=True)
    # 精英个体
    elites = [individual for individual, _ in sorted_population[:elite_size]]
    return elites

# 绘制遗传算法搜索过程中每代种群最优路径长度的变化
def plot_ga_progress(generation_distances, title="遗传算法搜索过程"):
    # 设置支持中文的字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(generation_distances)), generation_distances)
    plt.xlabel("迭代次数")
    plt.ylabel("最优路径长度")
    plt.title(title)
    plt.grid(True)
    plt.savefig("ga_progress_euclidean.png", dpi=300, bbox_inches='tight')
    plt.close()

# 绘制最优路径
def plot_best_path(best_path, cities, title="最优路径"):

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
    plt.savefig("best_path_euclidean.png", dpi=300, bbox_inches='tight')
    plt.close()

# 主函数
def main():   
    # 1. 穷举法求解10个城市的TSP问题
    print("\n1. 穷举法求解10个城市的TSP问题")
    
    cities_10 = get_cities(10)

    start_time = time.time()
    best_path, best_distance = exhaustive_search(cities_10)
    end_time = time.time()
        
    print(f"最短路径：{[cities_10[i][0] for i in best_path]}")
    print(f"最短距离：{best_distance:.4f}")
    print(f"计算时间：{end_time - start_time:.4f}秒")
    
    # 2. 遗传算法求解34个城市的TSP问题
    
    cities_34 = get_cities(34)
    
    # 遗传算法
    print("\n2.1 遗传算法")
    print("参数：种群大小=100，交叉率=0.8，变异率=0.05，最大迭代=1000")
    
    ga = GeneticAlgorithm(cities_34, population_size=100, crossover_rate=0.8, mutation_rate=0.05, max_generations=1000)
    start_time = time.time()
    best_path, best_distance, generation_distances = ga.run()
    end_time = time.time()
    
    print(f"最短路径：{[cities_34[i][0] for i in best_path]}")
    print(f"最短距离：{best_distance:.4f}")
    print(f"计算时间：{end_time - start_time:.4f}秒")
    
    # 3. 对比不同参数下的遗传算法效果
    print("\n3. 不同参数下遗传算法效果对比")
    
    # 记录所有测试中的最优解
    overall_best_path = best_path
    overall_best_distance = best_distance
    overall_best_generation_distances = generation_distances
    overall_best_params = {"种群规模": 100, "交叉率": 0.8, "变异率": 0.05}
    
    # 测试不同种群规模
    print("\n3.1 不同种群规模")
    print("固定参数：交叉率=0.8，变异率=0.05，最大迭代=1000")
    population_sizes = [50, 100, 200]
    
    for size in population_sizes:
        ga = GeneticAlgorithm(cities_34, population_size=size, crossover_rate=0.8, mutation_rate=0.05, max_generations=1000)
        path, distance, gen_distances = ga.run()
        print(f"种群规模：{size}，最短距离：{distance:.4f}")
        
        # 更新全局最优解
        if distance < overall_best_distance:
            overall_best_distance = distance
            overall_best_path = path
            overall_best_generation_distances = gen_distances
            overall_best_params = {"种群规模": size, "交叉率": 0.8, "变异率": 0.05}
    
    # 测试不同交叉率
    print("\n3.2 不同交叉率")
    print("固定参数：种群规模=100，变异率=0.05，最大迭代=1000")
    crossover_rates = [0.6, 0.8, 0.9]
    
    for rate in crossover_rates:
        ga = GeneticAlgorithm(cities_34, population_size=100, crossover_rate=rate, mutation_rate=0.05, max_generations=1000)
        path, distance, gen_distances = ga.run()
        print(f"交叉率：{rate}，最短距离：{distance:.4f}")
        
        # 更新全局最优解
        if distance < overall_best_distance:
            overall_best_distance = distance
            overall_best_path = path
            overall_best_generation_distances = gen_distances
            overall_best_params = {"种群规模": 100, "交叉率": rate, "变异率": 0.05}
    
    # 测试不同变异率
    print("\n3.3 不同变异率")
    print("固定参数：种群规模=100，交叉率=0.8，最大迭代=1000")
    mutation_rates = [0.03, 0.05, 0.08]
    
    for rate in mutation_rates:
        ga = GeneticAlgorithm(cities_34, population_size=100, crossover_rate=0.8, mutation_rate=rate, max_generations=1000)
        path, distance, gen_distances = ga.run()
        print(f"变异率：{rate}，最短距离：{distance:.4f}")
        
        # 更新全局最优解
        if distance < overall_best_distance:
            overall_best_distance = distance
            overall_best_path = path
            overall_best_generation_distances = gen_distances
            overall_best_params = {"种群规模": 100, "交叉率": 0.8, "变异率": rate}
    
    # 输出全局最优解
    print("\n全局最优解：")
    print(f"参数：{overall_best_params}")
    print(f"最短距离：{overall_best_distance:.4f}")
    print(f"最短路径：{[cities_34[i][0] for i in overall_best_path]}")
    
    # 4. 可视化遗传算法搜索过程
    print("\n4. 遗传算法可视化")
    
    # 绘制每代种群最优路径长度的变化
    plot_ga_progress(overall_best_generation_distances, f"最优参数{overall_best_params}")
    
    # 绘制最优路径
    plot_best_path(overall_best_path, cities_34, f"最优路径{overall_best_distance:.4f}")

if __name__ == "__main__":
    main()
