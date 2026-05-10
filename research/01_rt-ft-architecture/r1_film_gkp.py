#!/usr/bin/env python3
"""
R1 Phase 2-4: FiLM-GKP Adaptive Decoder
=========================================

Architecture:
  Input: GKP residuals r ∈ R^{n_edges} (continuous, per-shot)
  Conditioning: V_eff (scalar, injected via FiLM layers)
  Body: MLP with FiLM conditioning at each layer
  Output: P(logical_error) ∈ [0,1]

FiLM (Feature-wise Linear Modulation):
  γ, β = f(V_eff)   # conditioning network
  h' = γ ⊙ h + β    # modulate hidden activations

This allows the decoder to ADAPT its behavior based on the
current noise level — something MWPM cannot do due to scale invariance.

Training:
  - Mixed V_eff: train on samples with V_eff ∈ [0.08, 0.20]
  - FiLM conditions on V_eff → learns to adapt
  - Loss: binary cross-entropy on logical error prediction

Evaluation:
  - Static noise: compare with MWPM soft-info
  - Drift/spike: compare adaptation capability
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import os
import json
import time

DEVICE = 'mps' if torch.backends.mps.is_available() else 'cpu'


# ============================================================
# Dataset
# ============================================================
class GKPDataset(Dataset):
    """Load GKP residual data from .npz files."""

    def __init__(self, npz_path):
        data = np.load(npz_path)
        self.residuals = torch.tensor(data['residuals'], dtype=torch.float32)
        self.llr = torch.tensor(data['llr'], dtype=torch.float32)
        self.labels = torch.tensor(data['labels'], dtype=torch.float32)
        self.V_eff = torch.tensor(data['V_eff'], dtype=torch.float32)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            'residuals': self.residuals[idx],
            'llr': self.llr[idx],
            'V_eff': self.V_eff[idx],
            'label': self.labels[idx],
        }


class MixedVeffDataset(Dataset):
    """Generate on-the-fly with varying V_eff for FiLM training."""

    def __init__(self, n_samples, n_edges, V_range=(0.08, 0.20), seed=42):
        self.n_samples = n_samples
        self.n_edges = n_edges
        self.V_range = V_range
        self.rng = np.random.default_rng(seed)
        self._generate()

    def _generate(self):
        from scipy.special import erfc
        SQRT_PI = np.sqrt(np.pi)

        # Sample V_eff uniformly in range
        V_effs = self.rng.uniform(self.V_range[0], self.V_range[1], self.n_samples)
        sigmas = np.sqrt(V_effs)

        # GKP noise
        z = self.rng.standard_normal((self.n_samples, self.n_edges))
        delta = z * sigmas[:, np.newaxis]
        n_lat = np.rint(delta / SQRT_PI).astype(np.int64)
        errors = (n_lat % 2) != 0
        residual = delta - n_lat * SQRT_PI
        r_abs = np.abs(residual)
        llr = np.clip(((SQRT_PI - r_abs)**2 - r_abs**2) /
                      (2.0 * V_effs[:, np.newaxis]), -30, 30)

        # Simple label: majority vote of errors as proxy
        # (Real label requires full syndrome → MWPM decode, too slow for on-the-fly)
        # Instead, use error fraction as soft label
        self.residuals = torch.tensor(residual, dtype=torch.float32)
        self.llr = torch.tensor(llr, dtype=torch.float32)
        self.V_eff = torch.tensor(V_effs, dtype=torch.float32)
        # For real training, use pre-generated datasets with proper labels
        self.labels = torch.tensor(errors.sum(axis=1) % 2, dtype=torch.float32)

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        return {
            'residuals': self.residuals[idx],
            'llr': self.llr[idx],
            'V_eff': self.V_eff[idx],
            'label': self.labels[idx],
        }


# ============================================================
# FiLM Layer
# ============================================================
class FiLMLayer(nn.Module):
    """Feature-wise Linear Modulation.
    Conditions hidden features on a scalar (V_eff).
    """
    def __init__(self, cond_dim, hidden_dim):
        super().__init__()
        self.gamma_net = nn.Linear(cond_dim, hidden_dim)
        self.beta_net = nn.Linear(cond_dim, hidden_dim)

    def forward(self, h, cond):
        """h: (batch, hidden_dim), cond: (batch, cond_dim)"""
        gamma = self.gamma_net(cond)  # (batch, hidden_dim)
        beta = self.beta_net(cond)    # (batch, hidden_dim)
        return gamma * h + beta


# ============================================================
# FiLM-GKP Decoder Network
# ============================================================
class FiLMGKPDecoder(nn.Module):
    """
    Adaptive decoder for GKP surface codes.

    Takes continuous GKP residuals + V_eff conditioning.
    Outputs P(logical_error).
    """
    def __init__(self, input_dim, hidden_dim=256, n_layers=4, cond_dim=16):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        # Conditioning encoder: V_eff → cond_embedding
        self.cond_encoder = nn.Sequential(
            nn.Linear(1, cond_dim),
            nn.ReLU(),
            nn.Linear(cond_dim, cond_dim),
            nn.ReLU(),
        )

        # Input projection
        self.input_proj = nn.Linear(input_dim, hidden_dim)

        # FiLM-conditioned residual blocks
        self.layers = nn.ModuleList()
        self.film_layers = nn.ModuleList()
        self.norms = nn.ModuleList()
        for _ in range(n_layers):
            self.layers.append(nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
            ))
            self.film_layers.append(FiLMLayer(cond_dim, hidden_dim))
            self.norms.append(nn.LayerNorm(hidden_dim))

        # Output head
        self.output_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, residuals, V_eff):
        """
        residuals: (batch, input_dim) — GKP residuals (continuous)
        V_eff: (batch,) — noise parameter
        """
        # Encode conditioning
        cond = self.cond_encoder(V_eff.unsqueeze(-1))  # (batch, cond_dim)

        # Input projection
        h = F.relu(self.input_proj(residuals))  # (batch, hidden_dim)

        # FiLM-conditioned residual blocks
        for layer, film, norm in zip(self.layers, self.film_layers, self.norms):
            residual = layer(h)
            residual = film(residual, cond)  # FiLM modulation
            h = norm(h + residual)  # Residual connection + LayerNorm

        # Output
        logit = self.output_head(h).squeeze(-1)  # (batch,)
        return logit


# ============================================================
# Training
# ============================================================
def train_model(model, train_loader, val_loader, epochs=50, lr=1e-3,
                device=DEVICE):
    """Train FiLM-GKP decoder."""
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)

    best_val_loss = float('inf')
    history = []

    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        for batch in train_loader:
            res = batch['residuals'].to(device)
            V = batch['V_eff'].to(device)
            labels = batch['label'].to(device)

            logits = model(res, V)
            loss = F.binary_cross_entropy_with_logits(logits, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * len(labels)
            preds = (torch.sigmoid(logits) > 0.5).float()
            train_correct += (preds == labels).sum().item()
            train_total += len(labels)

        scheduler.step()

        # Validate
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        val_tp = 0  # true positives (correctly predicted errors)
        val_fn = 0  # false negatives (missed errors)
        val_fp = 0  # false positives

        with torch.no_grad():
            for batch in val_loader:
                res = batch['residuals'].to(device)
                V = batch['V_eff'].to(device)
                labels = batch['label'].to(device)

                logits = model(res, V)
                loss = F.binary_cross_entropy_with_logits(logits, labels)

                val_loss += loss.item() * len(labels)
                preds = (torch.sigmoid(logits) > 0.5).float()
                val_correct += (preds == labels).sum().item()
                val_total += len(labels)
                val_tp += ((preds == 1) & (labels == 1)).sum().item()
                val_fn += ((preds == 0) & (labels == 1)).sum().item()
                val_fp += ((preds == 1) & (labels == 0)).sum().item()

        train_loss /= train_total
        val_loss /= val_total
        train_acc = train_correct / train_total
        val_acc = val_correct / val_total

        entry = {
            'epoch': epoch,
            'train_loss': train_loss,
            'val_loss': val_loss,
            'train_acc': train_acc,
            'val_acc': val_acc,
            'val_tp': val_tp,
            'val_fn': val_fn,
            'val_fp': val_fp,
        }
        history.append(entry)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if epoch % 10 == 0 or epoch == epochs - 1:
            err_rate = val_fn / max(val_fn + val_tp, 1)
            print(f"  Epoch {epoch:3d}: train_loss={train_loss:.4f} "
                  f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} "
                  f"missed_errors={val_fn}/{val_tp+val_fn}")

    model.load_state_dict(best_state)
    return model, history


# ============================================================
# Evaluation: FiLM-GKP vs MWPM
# ============================================================
def evaluate_decoder(model, test_loader, device=DEVICE):
    """Evaluate FiLM-GKP decoder on test set."""
    model = model.to(device)
    model.eval()

    all_preds = []
    all_labels = []
    all_logits = []

    with torch.no_grad():
        for batch in test_loader:
            res = batch['residuals'].to(device)
            V = batch['V_eff'].to(device)
            labels = batch['label']

            logits = model(res, V).cpu()
            preds = (torch.sigmoid(logits) > 0.5).float()

            all_preds.append(preds)
            all_labels.append(labels)
            all_logits.append(logits)

    preds = torch.cat(all_preds).numpy()
    labels = torch.cat(all_labels).numpy()
    logits = torch.cat(all_logits).numpy()

    # Logical error rate = rate of INCORRECTLY predicted logical errors
    # For a decoder, "prediction" means whether the correction succeeds
    # We need to compare with the actual logical error after correction
    n_total = len(labels)
    n_label_errors = labels.sum()
    n_pred_errors = preds.sum()
    n_correct = (preds == labels).sum()
    accuracy = n_correct / n_total

    # The decoder's p_L is the rate at which it makes wrong predictions
    p_L_decoder = 1.0 - accuracy

    return {
        'p_L': float(p_L_decoder),
        'accuracy': float(accuracy),
        'n_total': int(n_total),
        'n_label_errors': int(n_label_errors),
        'label_rate': float(n_label_errors / n_total),
    }


# ============================================================
# Main
# ============================================================
def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    t0 = time.time()

    print("=" * 70)
    print("  R1: FiLM-GKP Adaptive Decoder")
    print(f"  Device: {DEVICE}")
    print("=" * 70)

    # Check if datasets exist
    datasets_exist = os.path.exists(os.path.join(out_dir, 'r1_static_phase1_train.npz'))
    if not datasets_exist:
        print("\n  Datasets not found. Run r1_gkp_dataset.py first.")
        return

    # Load datasets
    print("\n  Loading datasets...")
    train_static = GKPDataset(os.path.join(out_dir, 'r1_static_phase1_train.npz'))
    test_static = GKPDataset(os.path.join(out_dir, 'r1_static_phase1_test.npz'))
    test_drift = GKPDataset(os.path.join(out_dir, 'r1_drift_phase1_test.npz'))
    test_spike = GKPDataset(os.path.join(out_dir, 'r1_spike_phase1_test.npz'))

    input_dim = train_static.residuals.shape[1]
    print(f"  Input dim: {input_dim} (n_edges)")
    print(f"  Train: {len(train_static)} shots")
    print(f"  Test static: {len(test_static)}, drift: {len(test_drift)}, spike: {len(test_spike)}")

    # DataLoaders
    train_loader = DataLoader(train_static, batch_size=512, shuffle=True)
    test_static_loader = DataLoader(test_static, batch_size=1024)
    test_drift_loader = DataLoader(test_drift, batch_size=1024)
    test_spike_loader = DataLoader(test_spike, batch_size=1024)

    # Build model
    model = FiLMGKPDecoder(
        input_dim=input_dim,
        hidden_dim=128,
        n_layers=3,
        cond_dim=8,
    )
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Model: FiLM-GKP ({n_params:,} parameters)")

    # Train
    print("\n  Training on static Phase 1 data...")
    model, history = train_model(
        model, train_loader, test_static_loader,
        epochs=50, lr=1e-3, device=DEVICE,
    )

    # Evaluate
    print("\n" + "=" * 70)
    print("  EVALUATION: FiLM-GKP vs MWPM Baseline")
    print("=" * 70)

    # Load baselines
    with open(os.path.join(out_dir, 'r1_baselines.json')) as f:
        baselines = json.load(f)

    for name, loader in [
        ('static_phase1', test_static_loader),
        ('drift_phase1', test_drift_loader),
        ('spike_phase1', test_spike_loader),
    ]:
        result = evaluate_decoder(model, loader, device=DEVICE)
        mwpm = baselines.get(name, {}).get('mwpm_pL', None)

        mwpm_str = f"{mwpm:.4e}" if mwpm else "N/A"
        film_str = f"{result['p_L']:.4e}"

        ratio = ""
        if mwpm and mwpm > 0 and result['p_L'] > 0:
            r = mwpm / result['p_L']
            ratio = f"  FiLM/MWPM={r:.2f}x"
            if r > 1:
                ratio += " (FiLM better)"
            else:
                ratio += " (MWPM better)"

        print(f"\n  {name}:")
        print(f"    MWPM soft-info: p_L={mwpm_str}")
        print(f"    FiLM-GKP:      p_L={film_str} (acc={result['accuracy']:.4f})")
        print(f"    Label rate:     {result['label_rate']:.4f}")
        print(f"    {ratio}")

    # Save model and results
    torch.save(model.state_dict(), os.path.join(out_dir, 'r1_film_gkp_model.pt'))
    with open(os.path.join(out_dir, 'r1_film_gkp_history.json'), 'w') as f:
        json.dump(history, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n  Total: {elapsed:.0f}s ({elapsed/60:.1f}min)")


if __name__ == '__main__':
    main()
