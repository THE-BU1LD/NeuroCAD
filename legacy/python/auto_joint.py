# auto_joint.py
from connector import Joint
import math


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def auto_generate_joints(parts, threshold=1.5):
    joints = []

    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            p1, p2 = parts[i], parts[j]
            d = distance(p1.centroid, p2.centroid)

            if d < threshold:
                jt = "revolute" if p1.mass < p2.mass else "fixed"
                joints.append(
                    Joint(
                        type_=jt,
                        part_a=p1,
                        part_b=p2,
                        position=tuple((a + b) / 2 for a, b in zip(p1.centroid, p2.centroid)),
                        axis=(0, 0, 1),
                        stiffness=1.0,
                        damping=0.1,
                        max_load=200 + 10 * (p1.mass + p2.mass),
                    )
                )
    return joints
