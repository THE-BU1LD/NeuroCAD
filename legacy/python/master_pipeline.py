# master_pipeline_v2.py

import time
from typing import Any, List

from logging_config import get_logger
from pipeline_stage import PipelineStage
from config import config

logger = get_logger("MasterPipeline")


class MasterPipeline:
    def __init__(self, stages: List[PipelineStage]):
        self.stages = stages

    def run(self, input_data: Any) -> Any:
        data = input_data

        for stage in self.stages:
            start = time.time()

            data = stage.run(data)

            if config.pipeline.log_timings:
                elapsed = time.time() - start
                logger.info(f"{stage.__class__.__name__} completed in {elapsed:.4f}s")

        return data
