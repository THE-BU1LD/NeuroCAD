import torch
from torch import nn
import math


# ============================================================
# Positional Encoding (vectorized + faster)
# ============================================================

class PositionalEncoding(nn.Module):
    def __init__(self, num_freqs=6):
        super().__init__()
        self.num_freqs = num_freqs
        self.freq_bands = 2.0 ** torch.arange(num_freqs)

    def forward(self, x):
        # x: (..., 3)
        freqs = self.freq_bands.to(x.device)

        x_expanded = (x[..., None, :] * freqs[:, None])  # (..., F, 3)

        sin = torch.sin(x_expanded)
        cos = torch.cos(x_expanded)

        enc = torch.cat([sin, cos], dim=-2)  # (..., 2F, 3)
        enc = enc.reshape(*x.shape[:-1], -1)

        return torch.cat([x, enc], dim=-1)


# ============================================================
# Neural SDF Network
# ============================================================

class NeuralSDF(nn.Module):
    """
    Improved Neural SDF with:
    - Vectorized positional encoding
    - Stable geometric initialization
    - Proper skip handling
    """

    def __init__(
        self,
        hidden=256,
        layers=8,
        skip_layer=4,
        num_freqs=6,
        geometric_init=True,
    ):
        super().__init__()

        self.pe = PositionalEncoding(num_freqs)
        pe_dim = 3 * (1 + 2 * num_freqs)

        self.skip_layer = skip_layer

        self.layers = nn.ModuleList()

        in_dim = pe_dim

        for i in range(layers):

            if i == skip_layer:
                in_dim += pe_dim

            linear = nn.Linear(in_dim, hidden)

            if geometric_init:
                nn.init.normal_(linear.weight, 0.0, math.sqrt(2) / math.sqrt(hidden))
                nn.init.constant_(linear.bias, 0.0)

            self.layers.append(linear)
            in_dim = hidden

        self.activation = nn.SiLU()

        self.final = nn.Linear(hidden, 1)

        if geometric_init:
            nn.init.normal_(
                self.final.weight,
                mean=math.sqrt(math.pi) / math.sqrt(hidden),
                std=1e-5,
            )
            nn.init.constant_(self.final.bias, -0.5)

    def forward(self, p):
        p_enc = self.pe(p)
        x = p_enc

        for i, layer in enumerate(self.layers):
            if i == self.skip_layer:
                x = torch.cat([x, p_enc], dim=-1)

            x = self.activation(layer(x))

        return self.final(x).squeeze(-1)

    # --------------------------------------------------------
    # Gradient (normals)
    # --------------------------------------------------------

    def gradient(self, p):
        p = p.clone().detach().requires_grad_(True)

        sdf = self.forward(p)

        grads = torch.autograd.grad(
            outputs=sdf,
            inputs=p,
            grad_outputs=torch.ones_like(sdf),
            create_graph=True,
            retain_graph=True,
        )[0]

        return grads

    # --------------------------------------------------------
    # Eikonal loss (stabilized)
    # --------------------------------------------------------

    def eikonal_loss(self, p):
        grads = self.gradient(p)
        return ((grads.norm(dim=-1) - 1.0) ** 2).mean()

    # --------------------------------------------------------
    # Surface loss (NEW – important)
    # --------------------------------------------------------

    def surface_loss(self, p, target_sdf):
        pred = self.forward(p)
        return (pred - target_sdf).abs().mean()

    # --------------------------------------------------------
    # Narrow-band clamp
    # --------------------------------------------------------

    def forward_clamped(self, p, clamp=0.1):
        return torch.clamp(self.forward(p), -clamp, clamp)


# ============================================================
# Neural Shape Library
# ============================================================

class NeuralShapeLibrary:

    @staticmethod
    def gyroid(p, scale=6.0):
        x, y, z = p[..., 0], p[..., 1], p[..., 2]
        return (
            torch.sin(scale * x) * torch.cos(scale * y)
            + torch.sin(scale * y) * torch.cos(scale * z)
            + torch.sin(scale * z) * torch.cos(scale * x)
        )

    @staticmethod
    def superquadric(p, e1=0.3, e2=0.3):
        x = torch.abs(p[..., 0])
        y = torch.abs(p[..., 1])
        z = torch.abs(p[..., 2])

        return (
            (x ** (2 / e2) + y ** (2 / e2)) ** (e2 / e1)
            + z ** (2 / e1)
            - 1.0
        )

    @staticmethod
    def fractal_noise(p, octaves=4):
        val = 0.0
        amp = 1.0
        freq = 1.0

        for _ in range(octaves):
            val += amp * (
                torch.sin(freq * p[..., 0])
                * torch.sin(freq * p[..., 1])
                * torch.sin(freq * p[..., 2])
            )
            amp *= 0.5
            freq *= 2.0

        return val

    @staticmethod
    def blend(sdf_a, sdf_b, k=0.2):
        # numerically stable soft-min
        m = torch.minimum(sdf_a, sdf_b)
        return m - torch.log(
            torch.exp(-k * (sdf_a - m)) + torch.exp(-k * (sdf_b - m))
        ) / k


# ============================================================
# Hybrid Neural + Primitive Wrapper (FIXED)
# ============================================================

class HybridSDF(nn.Module):
    """
    Combines analytic SDF with neural refinement.
    """

    def __init__(self, primitive_sdf, neural_sdf, weight=0.5):
        super().__init__()
        self.primitive = primitive_sdf
        self.neural = neural_sdf
        self.weight = weight

    def forward(self, p):
        base = self.primitive(p)

        # prevent neural from destroying global shape
        detail = torch.tanh(self.neural(p))

        return base + self.weight * detail