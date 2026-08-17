#######################################################################
# Copyright (C)                                                       #
# 2016 - 2018 Shangtong Zhang(zhangshangtong.cpp@gmail.com)           #
# 2016 Jan Hakenberg(jan.hakenberg@gmail.com)                         #
# 2016 Tian Jun(tianjun.cpp@gmail.com)                                #
# 2016 Kenta Shimada(hyperkentakun@gmail.com)                         #
# Permission given to modify the code as long as you keep this        #
# declaration at the top                                              #
#######################################################################

import numpy as np
import pickle
import matplotlib.pyplot as plt
from collections import defaultdict
BOARD_ROWS = 4
BOARD_COLS = 4
BOARD_SIZE = BOARD_ROWS * BOARD_COLS
class State:
    def __init__(self):
        # the board is represented by an n * n array,
        # 1 represents a chessman of the player who moves first,
        # -1 represents a chessman of another player
        # 0 represents an empty position
        self.data = np.zeros((BOARD_ROWS, BOARD_COLS))
        self.winner = None
        self.hash_val = None
        self.end = None
    # compute the hash value for one state, it's unique
    def hash(self):
        if self.hash_val is None:
            self.hash_val = 0
            for i in np.nditer(self.data):
                self.hash_val = self.hash_val * 3 + i + 1
        return self.hash_val
    # check whether a player has won the game, or it's a tie
    def is_end(self):
        if self.end is not None:
            return self.end
        
        # Check rows for four in a row
        for i in range(BOARD_ROWS):
            for j in range(BOARD_COLS - 3):
                total = sum(self.data[i, j:j+4])
                if total == 4:
                    self.winner = 1
                    self.end = True
                    return self.end
                if total == -4:
                    self.winner = -1
                    self.end = True
                    return self.end
        
        # Check columns for four in a row
        for i in range(BOARD_ROWS - 3):
            for j in range(BOARD_COLS):
                total = sum(self.data[i:i+4, j])
                if total == 4:
                    self.winner = 1
                    self.end = True
                    return self.end
                if total == -4:
                    self.winner = -1
                    self.end = True
                    return self.end
        
        # Check diagonals (top-left to bottom-right)
        for i in range(BOARD_ROWS - 3):
            for j in range(BOARD_COLS - 3):
                total = sum([self.data[i+k, j+k] for k in range(4)])
                if total == 4:
                    self.winner = 1
                    self.end = True
                    return self.end
                if total == -4:
                    self.winner = -1
                    self.end = True
                    return self.end
        
        # Check diagonals (bottom-left to top-right)
        for i in range(3, BOARD_ROWS):
            for j in range(BOARD_COLS - 3):
                total = sum([self.data[i-k, j+k] for k in range(4)])
                if total == 4:
                    self.winner = 1
                    self.end = True
                    return self.end
                if total == -4:
                    self.winner = -1
                    self.end = True
                    return self.end

        # whether it's a tie
        sum_values = np.sum(np.abs(self.data))
        if sum_values == BOARD_SIZE:
            self.winner = 0
            self.end = True
            return self.end

        # game is still going on
        self.end = False
        return self.end
    # @symbol: 1 or -1
    # put chessman symbol in position (i, j)
    def next_state(self, i, j, symbol):
        new_state = State()
        new_state.data = np.copy(self.data)
        new_state.data[i, j] = symbol
        return new_state
    # print the board
    def print_state(self):
        for i in range(BOARD_ROWS):
            print('-------------')
            out = '| '
            for j in range(BOARD_COLS):
                if self.data[i, j] == 1:
                    token = '*'
                elif self.data[i, j] == -1:
                    token = 'x'
                else:
                    token = '0'
                out += token + ' | '
            print(out)
        print('-------------')
# 移除预计算所有状态的部分，改为在需要时动态处理
class Judger:
    # @player1: the player who will move first, its chessman will be 1
    # @player2: another player with a chessman -1
    def __init__(self, player1, player2):
        self.p1 = player1
        self.p2 = player2
        self.current_player = None
        self.p1_symbol = 1
        self.p2_symbol = -1
        self.p1.set_symbol(self.p1_symbol)
        self.p2.set_symbol(self.p2_symbol)
        self.current_state = State()

    def reset(self):
        self.p1.reset()
        self.p2.reset()

    def alternate(self):
        while True:
            yield self.p1
            yield self.p2

    # @print_state: if True, print each board during the game
    def play(self, print_state=False):
        alternator = self.alternate()
        self.reset()
        current_state = State()
        self.p1.set_state(current_state)
        self.p2.set_state(current_state)
        if print_state:
            current_state.print_state()
        while True:
            player = next(alternator)
            i, j, symbol = player.act()
            current_state = current_state.next_state(i, j, symbol)
            is_end = current_state.is_end()
            self.p1.set_state(current_state)
            self.p2.set_state(current_state)
            if print_state:
                current_state.print_state()
            if is_end:
                return current_state.winner
# AI player
class Player:
    # @step_size: the step size to update estimations
    # @epsilon: the probability to explore
    def __init__(self, step_size=0.1, epsilon=0.1):
        self.estimations = dict()
        self.step_size = step_size
        self.epsilon = epsilon
        self.states = []
        self.greedy = []
        self.symbol = 0

    def reset(self):
        self.states = []
        self.greedy = []

    def set_state(self, state):
        self.states.append(state)
        self.greedy.append(True)

    def set_symbol(self, symbol):
        self.symbol = symbol
        # 初始化估计值字典，在需要时动态添加状态
        pass
    # update value estimation
    def backup(self):
        states = [state.hash() for state in self.states]

        for i in reversed(range(len(states) - 1)):
            state = states[i]
            next_state = states[i + 1]
            # 确保状态在estimations字典中
            if state not in self.estimations:
                self.estimations[state] = 0.5
            if next_state not in self.estimations:
                self.estimations[next_state] = 0.5
            td_error = self.greedy[i] * (
                self.estimations[next_state] - self.estimations[state]
            )
            self.estimations[state] += self.step_size * td_error
    # choose an action based on the state
    def act(self):
        state = self.states[-1]
        next_states = []
        next_positions = []
        for i in range(BOARD_ROWS):
            for j in range(BOARD_COLS):
                if state.data[i, j] == 0:
                    next_positions.append([i, j])
                    next_state = state.next_state(i, j, self.symbol)
                    next_hash = next_state.hash()
                    # 如果状态不在estimations字典中，添加它
                    if next_hash not in self.estimations:
                        is_end = next_state.is_end()
                        if is_end:
                            if next_state.winner == self.symbol:
                                self.estimations[next_hash] = 1.0
                            elif next_state.winner == 0:
                                self.estimations[next_hash] = 0.5
                            else:
                                self.estimations[next_hash] = 0
                        else:
                            self.estimations[next_hash] = 0.5
                    next_states.append(next_hash)
        if np.random.rand() < self.epsilon:
            action = next_positions[np.random.randint(len(next_positions))]
            action.append(self.symbol)
            self.greedy[-1] = False
            return action
        values = []
        for hash_val, pos in zip(next_states, next_positions):
            values.append((self.estimations[hash_val], pos))
        # to select one of the actions of equal value at random due to Python's sort is stable
        np.random.shuffle(values)
        values.sort(key=lambda x: x[0], reverse=True)
        action = values[0][1]
        action.append(self.symbol)
        return action

    def save_policy(self):
        with open('policy_%s.bin' % ('first' if self.symbol == 1 else 'second'), 'wb') as f:
            pickle.dump(self.estimations, f)

    def load_policy(self):
        with open('policy_%s.bin' % ('first' if self.symbol == 1 else 'second'), 'rb') as f:
            self.estimations = pickle.load(f)
# human interface
# input a number to put a chessman
# | q | w | e | r |
# | a | s | d | f |
# | z | x | c | v |
# | b | n | m | , |
class HumanPlayer:
    def __init__(self, **kwargs):
        self.symbol = None
        self.keys = ['q', 'w', 'e', 'r', 'a', 's', 'd', 'f', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',']
        self.state = None

    def reset(self):
        pass

    def set_state(self, state):
        self.state = state

    def set_symbol(self, symbol):
        self.symbol = symbol

    def act(self):
        self.state.print_state()
        key = input("Input your position:")
        data = self.keys.index(key)
        i = data // BOARD_COLS
        j = data % BOARD_COLS
        return i, j, self.symbol
def train(epochs, print_every_n=500, model_name="model"):
    player1 = Player(epsilon=0.01)
    player2 = Player(epsilon=0.01)
    judger = Judger(player1, player2)
    player1_win = 0.0
    player2_win = 0.0
    tie_count = 0.0
    
    # 记录训练曲线数据
    training_history = {
        'epochs': [],
        'player1_winrate': [],
        'player2_winrate': [],
        'tie_rate': [],
        'player1_estimations_size': [],
        'player2_estimations_size': []
    }
    
    print(f"\n开始训练模型 {model_name}...")
    print(f"训练轮数: {epochs}")
    print("=" * 60)
    
    for i in range(1, epochs + 1):
        winner = judger.play(print_state=False)
        if winner == 1:
            player1_win += 1
        elif winner == -1:
            player2_win += 1
        else:
            tie_count += 1
            
        if i % print_every_n == 0:
            p1_rate = player1_win / i
            p2_rate = player2_win / i
            tie_rate = tie_count / i
            print(f'Epoch {i:6d} | Player1: {p1_rate:6.2%} | Player2: {p2_rate:6.2%} | Tie: {tie_rate:6.2%} | '
                  f'P1 States: {len(player1.estimations):5d} | P2 States: {len(player2.estimations):5d}')
            
            # 记录训练数据
            training_history['epochs'].append(i)
            training_history['player1_winrate'].append(p1_rate)
            training_history['player2_winrate'].append(p2_rate)
            training_history['tie_rate'].append(tie_rate)
            training_history['player1_estimations_size'].append(len(player1.estimations))
            training_history['player2_estimations_size'].append(len(player2.estimations))
        
        player1.backup()
        player2.backup()
        judger.reset()
    
    # 保存策略到不同的文件
    with open(f'policy_first_{model_name}.bin', 'wb') as f:
        pickle.dump(player1.estimations, f)
    with open(f'policy_second_{model_name}.bin', 'wb') as f:
        pickle.dump(player2.estimations, f)
    
    # 保存训练历史
    with open(f'training_history_{model_name}.bin', 'wb') as f:
        pickle.dump(training_history, f)
    
    print(f"\n{model_name} 训练完成!")
    print(f"Player1 estimations size: {len(player1.estimations)}")
    print(f"Player2 estimations size: {len(player2.estimations)}")
    print(f"最终胜率 - Player1: {player1_win/epochs:.2%}, Player2: {player2_win/epochs:.2%}, Tie: {tie_count/epochs:.2%}")
    print("=" * 60)
    
    return training_history
def compete(turns, model_name="model"):
    player1 = Player(epsilon=0.0)
    player2 = Player(epsilon=0)
    judger = Judger(player1, player2)
    # 加载指定模型的策略
    with open(f'policy_first_{model_name}.bin', 'rb') as f:
        player1.estimations = pickle.load(f)
    with open(f'policy_second_{model_name}.bin', 'rb') as f:
        player2.estimations = pickle.load(f)
    player1_win = 0.0
    player2_win = 0.0
    tie_count = 0.0
    for _ in range(turns):
        winner = judger.play()
        if winner == 1:
            player1_win += 1
        elif winner == -1:
            player2_win += 1
        else:
            tie_count += 1
        judger.reset()
    print(f'{model_name} - {turns} turns, player 1 win {player1_win / turns:.02f}, player 2 win {player2_win / turns:.02f}, tie {tie_count / turns:.02f}')
    return {
        'player1_winrate': player1_win / turns,
        'player2_winrate': player2_win / turns,
        'tie_rate': tie_count / turns
    }


def plot_training_curve(history_10k, history_100k):
    plt.figure(figsize=(15, 10))
    
    # 1. 胜率曲线
    plt.subplot(2, 2, 1)
    plt.plot(history_10k['epochs'], history_10k['player1_winrate'], 'b-', label='10k - Player1', linewidth=2)
    plt.plot(history_10k['epochs'], history_10k['player2_winrate'], 'b--', label='10k - Player2', linewidth=2)
    plt.plot(history_10k['epochs'], history_10k['tie_rate'], 'b:', label='10k - Tie', linewidth=2)
    plt.plot(history_100k['epochs'], history_100k['player1_winrate'], 'r-', label='100k - Player1', linewidth=2)
    plt.plot(history_100k['epochs'], history_100k['player2_winrate'], 'r--', label='100k - Player2', linewidth=2)
    plt.plot(history_100k['epochs'], history_100k['tie_rate'], 'r:', label='100k - Tie', linewidth=2)
    plt.xlabel('Training Epochs')
    plt.ylabel('Win Rate')
    plt.title('Win Rate Comparison')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 2. 状态数量增长
    plt.subplot(2, 2, 2)
    plt.plot(history_10k['epochs'], history_10k['player1_estimations_size'], 'b-', label='10k - Player1 States', linewidth=2)
    plt.plot(history_10k['epochs'], history_10k['player2_estimations_size'], 'b--', label='10k - Player2 States', linewidth=2)
    plt.plot(history_100k['epochs'], history_100k['player1_estimations_size'], 'r-', label='100k - Player1 States', linewidth=2)
    plt.plot(history_100k['epochs'], history_100k['player2_estimations_size'], 'r--', label='100k - Player2 States', linewidth=2)
    plt.xlabel('Training Epochs')
    plt.ylabel('Number of States')
    plt.title('State Space Coverage')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 3. Player1胜率对比
    plt.subplot(2, 2, 3)
    plt.plot(history_10k['epochs'], history_10k['player1_winrate'], 'b-', label='10k Model', linewidth=2, marker='o', markersize=4)
    plt.plot(history_100k['epochs'], history_100k['player1_winrate'], 'r-', label='100k Model', linewidth=2, marker='s', markersize=4)
    plt.xlabel('Training Epochs')
    plt.ylabel('Player1 Win Rate')
    plt.title('Player1 (First Player) Performance Comparison')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 4. 最终性能对比
    plt.subplot(2, 2, 4)
    models = ['10k Model', '100k Model']
    final_p1_10k = history_10k['player1_winrate'][-1]
    final_p2_10k = history_10k['player2_winrate'][-1]
    final_tie_10k = history_10k['tie_rate'][-1]
    final_p1_100k = history_100k['player1_winrate'][-1]
    final_p2_100k = history_100k['player2_winrate'][-1]
    final_tie_100k = history_100k['tie_rate'][-1]
    
    x = np.arange(len(models))
    width = 0.25
    
    plt.bar(x - width, [final_p1_10k, final_p1_100k], width, label='Player1', color='blue', alpha=0.7)
    plt.bar(x, [final_p2_10k, final_p2_100k], width, label='Player2', color='red', alpha=0.7)
    plt.bar(x + width, [final_tie_10k, final_tie_100k], width, label='Tie', color='green', alpha=0.7)
    
    plt.xlabel('Model')
    plt.ylabel('Final Win Rate')
    plt.title('Final Performance Comparison')
    plt.xticks(x, models)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('training_comparison.png', dpi=300, bbox_inches='tight')
    print("\n训练曲线图已保存为: training_comparison.png")
    plt.show()

def model_vs_model_competition(turns=1000):
    """让10k模型与100k模型进行比赛"""
    print(f"\n开始10k模型与100k模型的比赛，共{turns}轮...")
    
    # 10k模型作为先手，100k模型作为后手
    player1_10k = Player(epsilon=0.0)
    player2_100k = Player(epsilon=0.0)
    judger1 = Judger(player1_10k, player2_100k)
    
    # 加载策略
    with open('policy_first_10k.bin', 'rb') as f:
        player1_10k.estimations = pickle.load(f)
    with open('policy_second_100k.bin', 'rb') as f:
        player2_100k.estimations = pickle.load(f)
    
    # 100k模型作为先手，10k模型作为后手
    player1_100k = Player(epsilon=0.0)
    player2_10k = Player(epsilon=0.0)
    judger2 = Judger(player1_100k, player2_10k)
    
    # 加载策略
    with open('policy_first_100k.bin', 'rb') as f:
        player1_100k.estimations = pickle.load(f)
    with open('policy_second_10k.bin', 'rb') as f:
        player2_10k.estimations = pickle.load(f)
    
    # 记录比赛结果
    results = {
        '10k_first': {'wins': 0, 'losses': 0, 'ties': 0},
        '100k_first': {'wins': 0, 'losses': 0, 'ties': 0}
    }
    
    # 记录每轮比赛结果，用于绘制曲线
    competition_history = {
        'rounds': [],
        '10k_first_winrate': [],
        '100k_first_winrate': []
    }
    
    for i in range(1, turns + 1):
        # 10k先手 vs 100k后手
        winner1 = judger1.play(print_state=False)
        if winner1 == 1:  # 10k赢
            results['10k_first']['wins'] += 1
        elif winner1 == -1:  # 100k赢
            results['10k_first']['losses'] += 1
        else:  # 平局
            results['10k_first']['ties'] += 1
        judger1.reset()
        
        # 100k先手 vs 10k后手
        winner2 = judger2.play(print_state=False)
        if winner2 == 1:  # 100k赢
            results['100k_first']['wins'] += 1
        elif winner2 == -1:  # 10k赢
            results['100k_first']['losses'] += 1
        else:  # 平局
            results['100k_first']['ties'] += 1
        judger2.reset()
        
        # 每100轮记录一次数据
        if i % 100 == 0:
            competition_history['rounds'].append(i)
            competition_history['10k_first_winrate'].append(results['10k_first']['wins'] / i)
            competition_history['100k_first_winrate'].append(results['100k_first']['wins'] / i)
            
            print(f'Round {i:4d} | 10k先手: {results["10k_first"]["wins"]/i:.2%} | 100k先手: {results["100k_first"]["wins"]/i:.2%}')
    
    # 计算最终统计
    total_games = turns * 2
    total_10k_wins = results['10k_first']['wins'] + results['100k_first']['losses']
    total_100k_wins = results['10k_first']['losses'] + results['100k_first']['wins']
    total_ties = results['10k_first']['ties'] + results['100k_first']['ties']
    
    print("\n" + "=" * 70)
    print("10k模型 vs 100k模型 比赛结果")
    print("=" * 70)
    print(f"总比赛轮数: {total_games}")
    print(f"10k模型获胜: {total_10k_wins} ({total_10k_wins/total_games:.2%})")
    print(f"100k模型获胜: {total_100k_wins} ({total_100k_wins/total_games:.2%})")
    print(f"平局: {total_ties} ({total_ties/total_games:.2%})")
    
    print("\n详细结果:")
    print(f"10k先手 vs 100k后手: 10k赢 {results['10k_first']['wins']}, 100k赢 {results['10k_first']['losses']}, 平局 {results['10k_first']['ties']}")
    print(f"100k先手 vs 10k后手: 100k赢 {results['100k_first']['wins']}, 10k赢 {results['100k_first']['losses']}, 平局 {results['100k_first']['ties']}")
    
    # Plot competition curve
    plt.figure(figsize=(12, 6))
    plt.plot(competition_history['rounds'], competition_history['10k_first_winrate'], 'b-', label='10k Model (First)', linewidth=2, marker='o')
    plt.plot(competition_history['rounds'], competition_history['100k_first_winrate'], 'r-', label='100k Model (First)', linewidth=2, marker='s')
    plt.xlabel('Competition Rounds')
    plt.ylabel('Win Rate')
    plt.title('10k Model vs 100k Model Competition Curve')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('model_competition.png', dpi=300, bbox_inches='tight')
    print("\nCompetition curve saved as: model_competition.png")
    plt.show()
    
    return results, competition_history

def print_comparison_summary(results_10k, results_100k):
    print("\n" + "=" * 70)
    print("模型性能对比总结")
    print("=" * 70)
    
    print(f"\n{'指标':<20} {'10k模型':<15} {'100k模型':<15} {'差异':<15}")
    print("-" * 70)
    
    metrics = [
        ('Player1胜率', results_10k['player1_winrate'], results_100k['player1_winrate']),
        ('Player2胜率', results_10k['player2_winrate'], results_100k['player2_winrate']),
        ('平局率', results_10k['tie_rate'], results_100k['tie_rate'])
    ]
    
    for name, val_10k, val_100k in metrics:
        diff = val_100k - val_10k
        diff_str = f"{diff:+.2%}"
        print(f"{name:<20} {val_10k:>14.2%} {val_100k:>14.2%} {diff_str:>14}")
    
    print("\n分析结论:")
    if results_100k['player1_winrate'] > results_10k['player1_winrate']:
        print("✓ 100k模型的Player1胜率更高，训练效果更好")
    elif results_100k['player1_winrate'] < results_10k['player1_winrate']:
        print("✗ 100k模型的Player1胜率更低，可能需要更多训练")
    else:
        print("= 两个模型的Player1胜率相当")
    
    if results_100k['player2_winrate'] > results_10k['player2_winrate']:
        print("✓ 100k模型的Player2胜率更高，后手策略更强")
    elif results_100k['player2_winrate'] < results_10k['player2_winrate']:
        print("✗ 100k模型的Player2胜率更低")
    else:
        print("= 两个模型的Player2胜率相当")
    
    if results_100k['tie_rate'] > results_10k['tie_rate']:
        print("✓ 100k模型的平局率更高，策略更稳定")
    elif results_100k['tie_rate'] < results_10k['tie_rate']:
        print("✗ 100k模型的平局率更低")
    else:
        print("= 两个模型的平局率相当")
    
    print("=" * 70)

# The game is a zero sum game. If both players are playing with an optimal strategy, every game will end in a tie.
# So we test whether the AI can guarantee at least a tie if it goes second.
def play(model_name="model"):
    while True:
        player1 = HumanPlayer()
        player2 = Player(epsilon=0)
        judger = Judger(player1, player2)
        # 加载指定模型的策略
        with open(f'policy_second_{model_name}.bin', 'rb') as f:
            player2.estimations = pickle.load(f)
        winner = judger.play()
        if winner == player2.symbol:
            print("You lose!")
        elif winner == player1.symbol:
            print("You win!")
        else:
            print("It is a tie!")


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("4x4井字棋强化学习训练 - 模型对比实验")
    print("=" * 70)
    
    # 训练10k模型
    print("\n" + "=" * 70)
    print("第一阶段：训练10k模型（10,000轮）")
    print("=" * 70)
    history_10k = train(int(1e4), model_name="10k")
    results_10k = compete(int(1e2), model_name="10k")
    
    # 训练100k模型
    print("\n" + "=" * 70)
    print("第二阶段：训练100k模型（100,000轮）")
    print("=" * 70)
    history_100k = train(int(1e5), model_name="100k")
    results_100k = compete(int(1e2), model_name="100k")
    
    # 性能对比和可视化
    print("\n" + "=" * 70)
    print("第三阶段：模型性能对比分析")
    print("=" * 70)
    print_comparison_summary(results_10k, results_100k)
    plot_training_curve(history_10k, history_100k)
    
    # 模型比赛
    print("\n" + "=" * 70)
    print("第四阶段：10k模型 vs 100k模型 比赛")
    print("=" * 70)
    model_vs_model_competition(turns=1000)
    
    # 人机对战
    # print("\n" + "=" * 70)
    # print("第五阶段：人机对战测试")
    # print("=" * 70)
    # print("使用10k模型进行人机对战:")
    # play(model_name="10k")
