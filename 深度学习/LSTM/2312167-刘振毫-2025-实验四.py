import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import urllib.request
import re
import os
import sys
import signal

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    class SimpleProgressBar:
        def __init__(self, total, desc="Progress"):
            self.total = total
            self.desc = desc
            self.n = 0
            self.bar_length = 30
        
        def update(self, n=1):
            self.n += n
            percent = self.n / self.total
            filled = int(self.bar_length * self.n // self.total)
            bar = "█" * filled + "░" * (self.bar_length - filled)
            print(f"\r{self.desc}: |{bar}| {self.n}/{self.total} ({percent:.1%})", end="", flush=True)
            if self.n >= self.total:
                print()
        
        def set_postfix(self, **kwargs):
            items = " ".join([f"{k}={v}" for k, v in kwargs.items()])
            print(f" {items}", end="", flush=True)
        
        def close(self):
            if self.n < self.total:
                self.update(self.total - self.n)
    
    def tqdm(*args, **kwargs):
        return SimpleProgressBar(*args, **kwargs)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
CHECKPOINT_PATH = "lstm_checkpoint.pth"

print(f"{'='*60}")
print(f"LSTM Sentence Generation - The Time Machine Dataset")
print(f"{'='*60}")
print(f"Using device: {device}")

if torch.cuda.is_available():
    print(f"✓ GPU: {torch.cuda.get_device_name(0)}")
    print(f"✓ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    torch.cuda.empty_cache()
else:
    print("⚠ WARNING: CUDA not available, using CPU")

class Vocabulary:
    def __init__(self):
        self.char_to_idx = {}
        self.idx_to_char = {}
        self.vocab_size = 0
        
    def build_vocab(self, text):
        chars = sorted(set(text))
        self.char_to_idx = {char: idx for idx, char in enumerate(chars)}
        self.idx_to_char = {idx: char for idx, char in enumerate(chars)}
        self.vocab_size = len(chars)
        print(f"✓ Vocabulary size: {self.vocab_size}")
        
    def encode(self, char):
        return self.char_to_idx[char]
    
    def decode(self, idx):
        return self.idx_to_char[idx]

class TextDataset:
    def __init__(self, text, seq_length, vocab):
        self.text = text
        self.seq_length = seq_length
        self.vocab = vocab
        
    def __len__(self):
        return len(self.text) - self.seq_length
    
    def __getitem__(self, idx):
        input_seq = self.text[idx:idx + self.seq_length]
        target_seq = self.text[idx + 1:idx + self.seq_length + 1]
        
        input_idx = [self.vocab.encode(char) for char in input_seq]
        target_idx = [self.vocab.encode(char) for char in target_seq]
        
        return torch.tensor(input_idx, dtype=torch.long), torch.tensor(target_idx, dtype=torch.long)

class LSTMModel(nn.Module):
    def __init__(self, vocab_size, embed_size, hidden_size, num_layers, dropout=0.3):
        super(LSTMModel, self).__init__()
        self.embed_size = embed_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.embedding = nn.Embedding(vocab_size, embed_size)
        self.lstm = nn.LSTM(embed_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout if num_layers > 1 else 0,
                           bidirectional=False)
        self.fc = nn.Linear(hidden_size, vocab_size)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x, hidden=None):
        if hidden is None:
            hidden = self.init_hidden(x.size(0))
        
        embedded = self.dropout(self.embedding(x))
        output, hidden = self.lstm(embedded, hidden)
        output = self.fc(output)
        return output, hidden
    
    def init_hidden(self, batch_size):
        h0 = torch.zeros(self.num_layers, batch_size, self.hidden_size).to(device)
        c0 = torch.zeros(self.num_layers, batch_size, self.hidden_size).to(device)
        return (h0, c0)

class TrainingInterrupt(Exception):
    pass

def signal_handler(signum, frame):
    raise TrainingInterrupt("训练被用户中断")

def download_and_preprocess_data():
    urls = [
        "http://d2l-data.s3-accelerate.amazonaws.com/timemachine.txt",
        "https://www.gutenberg.org/cache/epub/35/pg35.txt"
    ]
    
    text = None
    for i, url in enumerate(urls):
        try:
            filename = "dataset.txt"
            if not os.path.exists(filename):
                print(f"📥 Downloading dataset from {url}...")
                urllib.request.urlretrieve(url, filename)
            
            with open(filename, "r", encoding="utf-8") as f:
                text = f.read()
            print(f"✓ Dataset loaded successfully")
            break
        except Exception as e:
            if i == len(urls) - 1:
                raise e
            continue
    
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    print(f"✓ Dataset size: {len(text):,} characters")
    
    return text

def train_model(model, dataset, epochs, batch_size, lr, device):
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    # Mixed precision training
    scaler = torch.amp.GradScaler('cuda', enabled=True)
    
    dataloader = torch.utils.data.DataLoader(
        dataset, batch_size=batch_size, shuffle=True, drop_last=True,
        num_workers=4, pin_memory=True, persistent_workers=True
    )
    
    start_epoch = 0
    best_loss = float('inf')
    
    if os.path.exists(CHECKPOINT_PATH):
        print(f"\n📂 发现检查点文件，正在加载...")
        checkpoint = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        scaler.load_state_dict(checkpoint['scaler_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        best_loss = checkpoint['loss']
        print(f"✓ 已从第 {checkpoint['epoch']} 个epoch恢复训练")
        print(f"✓ 上次训练损失: {best_loss:.4f}")
        print(f"✓ 将从第 {start_epoch} 个epoch继续训练")
    
    model.train()
    
    print(f"\n🚀 Starting training...")
    print(f"   Total epochs: {epochs}")
    print(f"   Start epoch: {start_epoch}")
    print(f"   Batch size: {batch_size}")
    print(f"   Learning rate: {lr}")
    print(f"   Data batches: {len(dataloader)}")
    
    original_signal_handler = signal.signal(signal.SIGINT, signal_handler)
    
    try:
        progress_bar = tqdm(range(start_epoch, epochs), desc="Training", unit="epoch")
        
        for epoch in progress_bar:
            epoch_loss = 0
            batch_progress = tqdm(dataloader, desc=f"  Epoch {epoch+1}/{epochs}", unit="batch", leave=False)
            
            for batch_idx, (inputs, targets) in enumerate(batch_progress):
                inputs, targets = inputs.to(device, non_blocking=True), targets.to(device, non_blocking=True)
                
                optimizer.zero_grad(set_to_none=True)
                
                # Mixed precision training
                with torch.amp.autocast('cuda', enabled=True):
                    outputs, hidden = model(inputs)
                    loss = criterion(outputs.view(-1, outputs.size(-1)), targets.view(-1))
                
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
                
                epoch_loss += loss.item()
                batch_progress.set_postfix(loss=f"{loss.item():.4f}")
            
            scheduler.step()
            avg_loss = epoch_loss / len(dataloader)
            
            if avg_loss < best_loss:
                best_loss = avg_loss
            
            progress_bar.set_postfix(loss=f"{avg_loss:.4f}", best=f"{best_loss:.4f}", lr=f"{scheduler.get_last_lr()[0]:.6f}")
            
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'scaler_state_dict': scaler.state_dict(),
                'loss': avg_loss,
                'best_loss': best_loss,
                'config': {
                    'embed_size': model.embed_size,
                    'hidden_size': model.hidden_size,
                    'num_layers': model.num_layers,
                    'vocab_size': None
                }
            }
            torch.save(checkpoint, CHECKPOINT_PATH)
            
    except TrainingInterrupt:
        print(f"\n\n⚠ 检测到用户中断，正在保存检查点...")
        checkpoint = {
            'epoch': epoch if 'epoch' in dir() else start_epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'scaler_state_dict': scaler.state_dict(),
            'loss': epoch_loss / len(dataloader) if 'epoch_loss' in dir() else best_loss,
            'best_loss': best_loss,
            'config': {
                'embed_size': model.embed_size,
                'hidden_size': model.hidden_size,
                'num_layers': model.num_layers,
                'vocab_size': None
            }
        }
        torch.save(checkpoint, CHECKPOINT_PATH)
        print(f"✓ 检查点已保存到: {CHECKPOINT_PATH}")
        print(f"✓ 下次运行将从 epoch {checkpoint['epoch'] + 1} 继续训练")
        signal.signal(signal.SIGINT, original_signal_handler)
        return best_loss
    
    signal.signal(signal.SIGINT, original_signal_handler)
    
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)
        print(f"\n✓ 训练完成，检查点文件已清理")
    
    return best_loss

def generate_text(model, vocab, prompt, max_length=300, temperature=0.7, beam_width=3):
    import math
    model.eval()
    device = next(model.parameters()).device
    with torch.no_grad():
        chars = list(prompt)
        input_seq = torch.tensor([[vocab.encode(c) for c in chars]], dtype=torch.long).to(device)
        
        # Process the prompt
        hidden = model.init_hidden(1)
        output, hidden = model(input_seq, hidden)
        
        # Initialize beam search
        beams = [(prompt, hidden, 0.0)]
        
        for _ in range(max_length):
            new_beams = []
            
            for beam in beams:
                current_text, current_hidden, current_score = beam
                
                # Get last character
                last_char = current_text[-1]
                char_idx = torch.tensor([[vocab.encode(last_char)]], dtype=torch.long).to(device)
                
                output, new_hidden = model(char_idx, current_hidden)
                probs = torch.softmax(output[:, -1] / temperature, dim=-1)
                
                # Get top k candidates
                top_probs, top_indices = torch.topk(probs, beam_width)
                
                for i in range(beam_width):
                    prob = top_probs[0][i].item()
                    idx = top_indices[0][i].item()
                    next_char = vocab.decode(idx)
                    
                    new_text = current_text + next_char
                    new_score = current_score + math.log(prob)
                    new_beams.append((new_text, new_hidden, new_score))
            
            # Keep top k beams
            new_beams.sort(key=lambda x: x[2], reverse=True)
            beams = new_beams[:beam_width]
        
        # Return the best beam
        best_beam = max(beams, key=lambda x: x[2])
        return best_beam[0]

def main():
    text = download_and_preprocess_data()
    
    vocab = Vocabulary()
    vocab.build_vocab(text)
    
    seq_length = 256
    dataset = TextDataset(text, seq_length, vocab)
    
    embed_size = 256
    hidden_size = 1024
    num_layers = 3
    batch_size = 256
    epochs = 100
    learning_rate = 0.0003
    
    model = LSTMModel(vocab.vocab_size, embed_size, hidden_size, num_layers)
    
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n📊 Model Configuration:")
    print(f"   Embedding size: {embed_size}")
    print(f"   Hidden size: {hidden_size}")
    print(f"   LSTM layers: {num_layers}")
    print(f"   Trainable parameters: {total_params:,}")
    
    if torch.cuda.is_available():
        model = model.to(device)
    
    print(f"\n🎯 Training LSTM model...")
    avg_loss = train_model(model, dataset, epochs, batch_size, learning_rate, device)
    print(f"\n✓ Training completed! Final loss: {avg_loss:.4f}")
    
    test_prompts = [
        "time traveller",
        "traveller",
        "the time traveller says that",
        "when the time traveller returns to the garden",
        "the time traveller begins learning the language",
        "the time traveller determines that",
        "the time traveller knows he will have to stop",
        "when he wakes up",
        "the time traveller finds himself",
        "the time traveller tells the narrator to wait for him"
    ]
    
    print(f"\n{'='*60}")
    print(f"🔮 Generated Text Results")
    print(f"{'='*60}")
    
    model.eval()
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n📝 Test {i}/{len(test_prompts)}: \"{prompt}\"")
        print(f"{'-'*55}")
        
        generated = generate_text(model, vocab, prompt, max_length=300, temperature=0.7, beam_width=3)
        
        print(f"{generated}\n")

if __name__ == "__main__":
    main()
