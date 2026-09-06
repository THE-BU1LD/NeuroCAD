# design_ir.py

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class Constraint:
    type: str
    parameters: Dict[str, Any]


@dataclass
class Feature:
    name: str
    parameters: Dict[str, Any]
    constraints: List[Constraint] = field(default_factory=list)


@dataclass
class DesignIR:
    features: List[Feature] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_feature(self, feature: Feature):
        self.features.append(feature)

    def summary(self) -> Dict[str, Any]:
        return {
            "feature_count": len(self.features),
            "metadata": self.metadata,
        }
