# src/pipeline_manager.py
import time
import threading
import logging
from queue import Queue, Empty, Full

from kokoro import KPipeline
from .config import (
    DEFAULT_LANG_CODE,
    INITIAL_PIPELINE_POOL_SIZE,
    MIN_SPARE_PIPELINES,
    MAX_PIPELINE_POOL_SIZE,
    LOG_LEVEL
)

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

class TTSPipelineManager:
    def __init__(self, lang_code: str = DEFAULT_LANG_CODE):
        self.lang_code = lang_code
        self.pipeline_pool = Queue(maxsize=MAX_PIPELINE_POOL_SIZE)
        self.pool_lock = threading.Lock()
        self.current_pool_size = 0
        self.active_pipelines = 0 # Count of pipelines currently in use

        logger.info(f"Initializing TTSPipelineManager with lang_code='{lang_code}'")
        self._initialize_pool()

    def _create_pipeline(self) -> KPipeline | None:
        """Creates a new KPipeline instance."""
        try:
            logger.info(f"Creating new KPipeline instance for lang='{self.lang_code}'...")
            start_time = time.time()
            pipeline = KPipeline(lang_code=self.lang_code)
            creation_time = time.time() - start_time
            logger.info(f"Successfully created KPipeline instance in {creation_time:.2f}s.")
            return pipeline
        except Exception as e:
            logger.error(f"Failed to create KPipeline instance: {e}", exc_info=True)
            return None

    def _initialize_pool(self):
        """Initializes the pipeline pool with a starting number of pipelines."""
        with self.pool_lock:
            logger.info(f"Initializing pipeline pool with {INITIAL_PIPELINE_POOL_SIZE} instances.")
            for _ in range(INITIAL_PIPELINE_POOL_SIZE):
                if self.current_pool_size < MAX_PIPELINE_POOL_SIZE:
                    pipeline = self._create_pipeline()
                    if pipeline:
                        try:
                            self.pipeline_pool.put_nowait(pipeline)
                            self.current_pool_size += 1
                        except Full:
                            logger.warning("Pipeline pool is full during initialization. This shouldn't happen.")
                            break # Should not happen if MAX_PIPELINE_POOL_SIZE is respected
                    else:
                        logger.warning("Failed to create a pipeline during initial pool setup.")
                else:
                    logger.info("Reached MAX_PIPELINE_POOL_SIZE during initialization.")
                    break
            logger.info(f"Pipeline pool initialized. Current size: {self.current_pool_size}, Available: {self.pipeline_pool.qsize()}")

    def get_pipeline(self) -> KPipeline | None:
        """Gets an available pipeline from the pool. Scales up if necessary."""
        with self.pool_lock: # Lock to ensure consistent state for active_pipelines and scaling
            self.active_pipelines += 1
            logger.info(f"Attempting to get pipeline. Active pipelines: {self.active_pipelines}, Current pool size: {self.current_pool_size}, Available in queue: {self.pipeline_pool.qsize()}")

            # Check if scaling is needed
            # Scale if (total_pipelines - active_pipelines) < MIN_SPARE_PIPELINES
            # which means available_in_queue + (current_pool_size - active_pipelines - available_in_queue_approx) < MIN_SPARE_PIPELINES
            # A simpler check: if available pipelines in queue is less than min_spare_pipelines and we can still add more.
            # More robust: if (current_pool_size - active_pipelines) < MIN_SPARE_PIPELINES
            # This means the number of *potentially* free pipelines (not in queue yet but not active) + those in queue is low.
            
            # The condition from user: "When the usage reaches N-1 (total_pipelines - 1), you will create 1 more so that we have 2 additional pipelines."
            # This translates to: if active_pipelines == current_pool_size - 1, and current_pool_size < MAX_PIPELINE_POOL_SIZE, add one.
            # This ensures there's always at least one spare, and we aim for MIN_SPARE_PIPELINES.
            
            # Let's refine the scaling condition: if the number of *idle* pipelines (pool_size - active_pipelines) is less than MIN_SPARE_PIPELINES,
            # then we should consider scaling up.
            idle_pipelines = self.current_pool_size - self.active_pipelines
            if idle_pipelines < MIN_SPARE_PIPELINES and self.current_pool_size < MAX_PIPELINE_POOL_SIZE:
                logger.info(f"Scaling condition met: Idle pipelines ({idle_pipelines}) < MIN_SPARE_PIPELINES ({MIN_SPARE_PIPELINES}). Attempting to add a new pipeline.")
                if self._add_pipeline_to_pool():
                    logger.info("Successfully added a new pipeline during scaling.")
                else:
                    logger.warning("Failed to add a new pipeline during scaling.")
        try:
            # Try to get a pipeline without blocking indefinitely
            pipeline = self.pipeline_pool.get(timeout=10) # Wait up to 10s for a pipeline
            logger.info(f"Retrieved pipeline from pool. Available in queue: {self.pipeline_pool.qsize()}")
            return pipeline
        except Empty:
            logger.warning("Pipeline pool is empty and timeout reached. No pipeline available.")
            # If pool is empty, it means all current_pool_size pipelines are active.
            # We decrement active_pipelines here because we failed to get one.
            with self.pool_lock:
                self.active_pipelines -= 1
            return None

    def _add_pipeline_to_pool(self) -> bool:
        """Adds a single new pipeline to the pool if not exceeding max size. Called internally."""
        # This method assumes pool_lock is already held or not strictly needed if only current_pool_size is modified atomically.
        # However, for consistency with current_pool_size updates, it's better if called from a locked section.
        if self.current_pool_size < MAX_PIPELINE_POOL_SIZE:
            pipeline = self._create_pipeline()
            if pipeline:
                try:
                    self.pipeline_pool.put_nowait(pipeline) # Add to queue
                    self.current_pool_size += 1
                    logger.info(f"Added new pipeline. Pool size: {self.current_pool_size}, Available: {self.pipeline_pool.qsize()}")
                    return True
                except Full:
                    logger.error("Critical: Tried to add pipeline to an already full queue (max_size). This indicates a logic flaw or race condition.")
                    # If queue is full but current_pool_size < MAX_PIPELINE_POOL_SIZE, it's an issue.
                    # For now, we don't add it back, to avoid blocking. The pipeline instance might be lost.
                    return False # Should not happen if Queue(maxsize=MAX_PIPELINE_POOL_SIZE)
            else:
                logger.warning("Failed to create pipeline instance for scaling.")
                return False
        else:
            logger.info("Cannot add new pipeline; MAX_PIPELINE_POOL_SIZE reached.")
            return False

    def release_pipeline(self, pipeline: KPipeline):
        """Returns a pipeline to the pool."""
        if pipeline is None:
            logger.warning("Attempted to release a None pipeline.")
            # Decrement active_pipelines if it was incremented for a None pipeline that failed to be acquired.
            # This path should ideally not be hit if get_pipeline returns None and active_pipelines is decremented there.
            return

        try:
            self.pipeline_pool.put_nowait(pipeline)
            with self.pool_lock:
                self.active_pipelines -= 1
            logger.info(f"Pipeline released to pool. Active pipelines: {self.active_pipelines}, Available in queue: {self.pipeline_pool.qsize()}")
        except Full:
            # This case should ideally not happen if MAX_PIPELINE_POOL_SIZE is managed correctly
            # and pipelines are only added if current_pool_size < MAX_PIPELINE_POOL_SIZE.
            # If it does, it means we have more KPipeline objects than the queue can hold.
            # This could happen if MAX_PIPELINE_POOL_SIZE is small and many pipelines are created
            # then released rapidly before current_pool_size is updated, or a logic error.
            logger.error("CRITICAL: Attempted to release pipeline to a full pool! This may lead to pipeline loss.")
            # For now, we still decrement active_pipelines, assuming the pipeline is now 'lost' if not re-added.
            with self.pool_lock:
                self.active_pipelines -= 1
            # Consider what to do with the 'pipeline' object here. Destroy it? Log it?

    def get_status(self):
        """Returns the current status of the pipeline pool."""
        with self.pool_lock:
            return {
                "current_pool_size": self.current_pool_size,
                "active_pipelines": self.active_pipelines,
                "available_in_queue": self.pipeline_pool.qsize(),
                "max_pool_size": MAX_PIPELINE_POOL_SIZE,
                "min_spare_pipelines": MIN_SPARE_PIPELINES
            }

    def shutdown(self):
        """Cleans up resources, though KPipeline might not have explicit close()."""
        logger.info("Shutting down TTSPipelineManager. Clearing pipeline pool.")
        with self.pool_lock:
            while not self.pipeline_pool.empty():
                try:
                    pipeline = self.pipeline_pool.get_nowait()
                    # If KPipeline had a .close() or similar, call it here.
                    # For now, we just remove it from the queue.
                    del pipeline 
                except Empty:
                    break
            self.current_pool_size = 0
            self.active_pipelines = 0
        logger.info("Pipeline pool cleared.")

# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = TTSPipelineManager(lang_code='en')
    print("Initial status:", manager.get_status())

    pipelines_to_test = 5
    acquired_pipelines = []

    print(f"\nAttempting to acquire {pipelines_to_test} pipelines...")
    for i in range(pipelines_to_test):
        print(f"Acquiring pipeline {i+1}...")
        p = manager.get_pipeline()
        if p:
            print(f"Acquired pipeline {i+1}. Status: {manager.get_status()}")
            acquired_pipelines.append(p)
        else:
            print(f"Failed to acquire pipeline {i+1}. Status: {manager.get_status()}")
            break
        time.sleep(0.1) # Simulate some work / delay

    print(f"\nAcquired {len(acquired_pipelines)} pipelines.")
    print("Current status:", manager.get_status())

    print("\nReleasing pipelines...")
    for i, p in enumerate(acquired_pipelines):
        manager.release_pipeline(p)
        print(f"Released pipeline {i+1}. Status: {manager.get_status()}")
        time.sleep(0.1)

    print("\nFinal status after release:", manager.get_status())

    # Test scaling
    # Set INITIAL_PIPELINE_POOL_SIZE = 2, MIN_SPARE_PIPELINES = 2 for this test in config.py
    print("\n--- Testing Scaling Logic (adjust config for this test) ---")
    # Assuming INITIAL_PIPELINE_POOL_SIZE = 2, MIN_SPARE_PIPELINES = 2
    # MAX_PIPELINE_POOL_SIZE = 5
    # manager = TTSPipelineManager(lang_code='en') # Re-initialize with test config if needed
    # print("Initial status for scaling test:", manager.get_status())
    # p1 = manager.get_pipeline() # Active: 1, Pool: 2. Idle = 1. Should scale (1 < 2).
    # print("Status after 1st get:", manager.get_status()) # Expect Pool: 3
    # p2 = manager.get_pipeline() # Active: 2, Pool: 3. Idle = 1. Should scale (1 < 2).
    # print("Status after 2nd get:", manager.get_status()) # Expect Pool: 4
    # p3 = manager.get_pipeline() # Active: 3, Pool: 4. Idle = 1. Should scale (1 < 2).
    # print("Status after 3rd get:", manager.get_status()) # Expect Pool: 5 (max)
    # p4 = manager.get_pipeline() # Active: 4, Pool: 5. Idle = 1. No scale (max reached).
    # print("Status after 4th get:", manager.get_status()) # Expect Pool: 5
    # p5 = manager.get_pipeline() # Active: 5, Pool: 5. Idle = 0. No scale (max reached).
    # print("Status after 5th get:", manager.get_status()) # Expect Pool: 5

    # if p1: manager.release_pipeline(p1)
    # if p2: manager.release_pipeline(p2)
    # if p3: manager.release_pipeline(p3)
    # if p4: manager.release_pipeline(p4)
    # if p5: manager.release_pipeline(p5)
    # print("Status after releasing all for scaling test:", manager.get_status())

    manager.shutdown()
    print("Manager shut down.")

