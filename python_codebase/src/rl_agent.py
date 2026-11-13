"""
FX Signal Lab - Reinforcement Learning Agents (DQN and PPO/Actor-Critic)
Implements neural network-based trading agents with replay memory and policy gradients.
Designed with a clean, high-performance architecture compatible with pure NumPy/SciPy/PyTorch.
"""

import numpy as np
from collections import deque
import random
from typing import Tuple, List, Dict


class ReplayBuffer:
    """Experience replay memory buffer for off-policy Q-learning."""
    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.bool_)
        )

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    """
    Deep Q-Network Agent for FX Signal Decision Making.
    Learns Q(s, a) via Bellman optimality: Q(s, a) <- r + gamma * max_a' Q(s', a').
    """
    def __init__(
        self,
        state_dim: int,
        action_dim: int = 3,
        lr: float = 0.001,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        batch_size: int = 64
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        
        self.memory = ReplayBuffer(capacity=10000)
        
        # Two-layer MLP Q-network weights: input -> 64 -> 32 -> action_dim
        np.random.seed(42)
        self.W1 = np.random.randn(state_dim, 64) * np.sqrt(2.0 / state_dim)
        self.b1 = np.zeros(64)
        self.W2 = np.random.randn(64, 32) * np.sqrt(2.0 / 64)
        self.b2 = np.zeros(32)
        self.W3 = np.random.randn(32, action_dim) * np.sqrt(2.0 / 32)
        self.b3 = np.zeros(action_dim)
        
        # Target network weights
        self._sync_target()

    def _sync_target(self):
        self.target_W1 = self.W1.copy()
        self.target_b1 = self.b1.copy()
        self.target_W2 = self.W2.copy()
        self.target_b2 = self.b2.copy()
        self.target_W3 = self.W3.copy()
        self.target_b3 = self.b3.copy()

    def _forward(self, X: np.ndarray, target: bool = False) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        W1 = self.target_W1 if target else self.W1
        b1 = self.target_b1 if target else self.b1
        W2 = self.target_W2 if target else self.W2
        b2 = self.target_b2 if target else self.b2
        W3 = self.target_W3 if target else self.W3
        b3 = self.target_b3 if target else self.b3
        
        # Layer 1 + ReLU
        z1 = np.dot(X, W1) + b1
        a1 = np.maximum(0, z1)
        # Layer 2 + ReLU
        z2 = np.dot(a1, W2) + b2
        a2 = np.maximum(0, z2)
        # Output Q-values
        q = np.dot(a2, W3) + b3
        return q, a1, a2

    def select_action(self, state: np.ndarray, eval_mode: bool = False) -> int:
        if not eval_mode and np.random.rand() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        
        state_batch = np.expand_dims(state, axis=0)
        q_vals, _, _ = self._forward(state_batch)
        return int(np.argmax(q_vals[0]))

    def train_step(self) -> float:
        if len(self.memory) < self.batch_size:
            return 0.0
            
        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        
        # Predict Q(s)
        current_q, a1, a2 = self._forward(states)
        # Target Q(s')
        next_q, _, _ = self._forward(next_states, target=True)
        max_next_q = np.max(next_q, axis=1)
        
        # Bellman target
        targets = current_q.copy()
        for i in range(self.batch_size):
            target_val = rewards[i] if dones[i] else rewards[i] + self.gamma * max_next_q[i]
            targets[i, actions[i]] = target_val
            
        # Backpropagation gradients (MSE loss)
        dq = (current_q - targets) / self.batch_size
        loss = float(np.mean((current_q - targets)**2))
        
        # Gradients for layer 3
        dW3 = np.dot(a2.T, dq)
        db3 = np.sum(dq, axis=0)
        
        # Gradients for layer 2
        da2 = np.dot(dq, self.W3.T)
        dz2 = da2 * (a2 > 0)
        dW2 = np.dot(a1.T, dz2)
        db2 = np.sum(dz2, axis=0)
        
        # Gradients for layer 1
        da1 = np.dot(dz2, self.W2.T)
        dz1 = da1 * (a1 > 0)
        dW1 = np.dot(states.T, dz1)
        db1 = np.sum(dz1, axis=0)
        
        # Weight updates with gradient clipping
        clip = 5.0
        self.W3 -= self.lr * np.clip(dW3, -clip, clip)
        self.b3 -= self.lr * np.clip(db3, -clip, clip)
        self.W2 -= self.lr * np.clip(dW2, -clip, clip)
        self.b2 -= self.lr * np.clip(db2, -clip, clip)
        self.W1 -= self.lr * np.clip(dW1, -clip, clip)
        self.b1 -= self.lr * np.clip(db1, -clip, clip)
        
        # Decay exploration
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        return loss


class PPOAgent:
    """
    Actor-Critic / Proximal Policy Optimization trading policy.
    Uses Softmax policy head for actions and Value baseline head.
    """
    def __init__(self, state_dim: int, action_dim: int = 3, lr: float = 0.002, gamma: float = 0.99):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = lr
        self.gamma = gamma
        
        np.random.seed(101)
        # Shared representations
        self.W = np.random.randn(state_dim, 48) * np.sqrt(2.0 / state_dim)
        self.b = np.zeros(48)
        # Actor head (Logits -> Softmax probabilities)
        self.W_actor = np.random.randn(48, action_dim) * np.sqrt(2.0 / 48)
        self.b_actor = np.zeros(action_dim)
        # Critic head (State value)
        self.W_critic = np.random.randn(48, 1) * np.sqrt(2.0 / 48)
        self.b_critic = np.zeros(1)

    def get_action_and_value(self, state: np.ndarray) -> Tuple[int, float, np.ndarray]:
        h = np.maximum(0, np.dot(state, self.W) + self.b)
        logits = np.dot(h, self.W_actor) + self.b_actor
        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        
        # Critic value
        val = float(np.dot(h, self.W_critic) + self.b_critic)
        
        action = np.random.choice(self.action_dim, p=probs)
        return action, val, probs

    def evaluate_state(self, state: np.ndarray) -> int:
        """Deterministic policy action for evaluation."""
        h = np.maximum(0, np.dot(state, self.W) + self.b)
        logits = np.dot(h, self.W_actor) + self.b_actor
        return int(np.argmax(logits))
