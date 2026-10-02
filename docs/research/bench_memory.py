"""模拟 32 智能体沙盒在内存中能占多少"""
import os, sys, tracemalloc
sys.path.insert(0, '/home/ubuntu/atria')

# 模拟一个智能体的状态（memory stream 风格，最占内存的部件）
class Agent:
    def __init__(self, i):
        self.id = i
        self.name = f"居民_{i}"
        self.personality = "外向、好奇心强、喜欢囤积、讨厌噪音" * 3
        # Smallville 风格记忆流：每步存观察+反思，跑48步
        self.memory = []
        for step in range(72):
            self.memory.append({
                "type": "event",
                "step": step,
                "desc": f"在广场遇到了居民_{(i+7)%32}，聊起了天气和物价，对方提到下周集市可能有新货到。" * 4,
                "loc": (i*13 % 100, i*29 % 100),
                "recency": 72 - step,
                "importance": (step * 37) % 10,
            })
        # 长期反思
        self.reflections = [f"我发现居民_{(i+3)%32}不值得信任，因为他三次答应的事都没做到。" * 6] * 20

agents = [Agent(i) for i in range(32)]
tracemalloc.start()
snap = tracemalloc.take_traceback if False else None
current, peak = tracemalloc.get_traced_memory()
print(f"32 智能体 x 72 步记忆 = {current/1024/1024:.1f} MB (peak {peak/1024/1024:.1f} MB)")
print(f"服务器可用约 2713 MB → {'✓ 够' if current < 2000 else '✗ 超限'}")

# 512K 上下文测试数据准备：25 agent x 24 步的记忆 dump
import json
dump = json.dumps([a.__dict__ for a in agents[:25]], ensure_ascii=False, default=str)
print(f"25 智能体全量记忆 JSON = {len(dump)/1024:.0f} KB → 512K ctx {'✓' if len(dump) < 400000 else '✗'}")
