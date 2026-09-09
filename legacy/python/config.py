# config.py

from dataclasses import dataclass


@dataclass
class GeometryConfig:
    tolerance: float = 1e-6
    default_resolution: int = 64
    max_triangles: int = 1_000_000


@dataclass
class NLPConfig:
    dimension_unit: str = "mm"
    allow_ambiguity: bool = False
    max_tokens: int = 2048


@dataclass
class NeuralConfig:
    latent_dim: int = 128
    sdf_resolution: int = 128
    enable_gpu: bool = True


@dataclass
class OptimizationConfig:
    enable_geometry_optimization: bool = True
    enable_topology_optimization: bool = False
    simplify_mesh: bool = True


@dataclass
class PipelineConfig:
    debug: bool = True
    deterministic_mode: bool = True
    log_timings: bool = True


class Config:
    geometry = GeometryConfig()
    nlp = NLPConfig()
    neural = NeuralConfig()
    optimization = OptimizationConfig()
    pipeline = PipelineConfig()


config = Config()
