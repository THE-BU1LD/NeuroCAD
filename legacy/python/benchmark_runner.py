# benchmark_runner.py

import time
from geometry_metrics import triangle_count


def benchmark_pipeline(pipeline, input_data):
    start = time.time()
    mesh = pipeline.run(input_data)
    elapsed = time.time() - start

    return {
        "time_seconds": elapsed,
        "triangles": triangle_count(mesh),
    }
