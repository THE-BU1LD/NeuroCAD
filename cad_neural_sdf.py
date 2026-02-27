import torch
from torch import nn
import math


# ============================================================
# Positional Encoding
# ============================================================

class PositionalEncoding(nn.Module):
    def __init__(self, num_freqs=6):
        super().__init__()
        self.num_freqs = num_freqs

    def forward(self, x):
        enc = [x]
        for i in range(self.num_freqs):
            freq = 2.0 ** i
            enc.append(torch.sin(freq * x))
            enc.append(torch.cos(freq * x))
        return torch.cat(enc, dim=-1)


# ============================================================
# Neural SDF Network
# ============================================================

class NeuralSDF(nn.Module):
    """
    High-quality neural implicit SDF with:
    - Positional encoding
    - Skip connections
    - Geometric initialization
    - Gradient computation
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

        net = []
        in_dim = pe_dim

        for i in range(layers):
            if i == skip_layer:
                in_dim += pe_dim

            linear = nn.Linear(in_dim, hidden)

            if geometric_init:
                nn.init.normal_(linear.weight, mean=0.0, std=math.sqrt(2) / math.sqrt(hidden))
                nn.init.constant_(linear.bias, 0.0)

            net.append(linear)
            net.append(nn.SiLU())
            in_dim = hidden

        final = nn.Linear(hidden, 1)

        if geometric_init:
            nn.init.normal_(final.weight, mean=math.sqrt(math.pi) / math.sqrt(hidden), std=1e-5)
            nn.init.constant_(final.bias, -0.5)

        net.append(final)

        self.net = nn.ModuleList(net)

    def forward(self, p):
        p_enc = self.pe(p)
        x = p_enc

        layer_idx = 0
        for module in self.net:
            if isinstance(module, nn.Linear):
                if layer_idx == self.skip_layer:
                    x = torch.cat([x, p_enc], dim=-1)
                x = module(x)
                layer_idx += 1
            else:
                x = module(x)

        return x.squeeze(-1)

    # --------------------------------------------------------
    # Gradient (for normals)
    # --------------------------------------------------------

    def gradient(self, p):
        p.requires_grad_(True)
        sdf = self.forward(p)
        grads = torch.autograd.grad(
            outputs=sdf,
            inputs=p,
            grad_outputs=torch.ones_like(sdf),
            create_graph=True,
            retain_graph=True,
            only_inputs=True,
        )[0]
        return grads

    # --------------------------------------------------------
    # Eikonal loss
    # --------------------------------------------------------

    def eikonal_loss(self, p):
        grads = self.gradient(p)
        return ((grads.norm(dim=-1) - 1.0) ** 2).mean()

    # --------------------------------------------------------
    # Inference clamp (narrow-band stability)
    # --------------------------------------------------------

    def forward_clamped(self, p, clamp=0.1):
        sdf = self.forward(p)
        return torch.clamp(sdf, -clamp, clamp)


# ============================================================
# Neural Shape Library (High Quality Fields)
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
        return (x ** (2 / e2) + y ** (2 / e2)) ** (e2 / e1) + z ** (2 / e1) - 1.0

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
        return -torch.log(
            torch.exp(-k * sdf_a) + torch.exp(-k * sdf_b)
        ) / k


# ============================================================
# Hybrid Neural + Primitive Wrapper
# ============================================================

class HybridSDF(nn.Module):
    """
    Combines primitive SDF with neural refinement.
    """

    def __init__(self, primitive_sdf, neural_sdf, weight=0.5):
        super().__init__()
        self.primitive = primitive_sdf
        self.neural = neural_sdf
        self.weight = weight

    def forward(self, p):
        base = self.primitive(p)
        detail = self.neural(p)
        return base + self.weight * detail
