# src/tts_service.py
import logging
import time
import numpy as np

from .pipeline_manager import TTSPipelineManager
from .config import DEFAULT_VOICE, LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

SAMPLE_RATE = 24000  # Assuming kokoro outputs at 24kHz as per user example

class TTSService:
    def __init__(self, pipeline_manager: TTSPipelineManager):
        self.pipeline_manager = pipeline_manager
        if not pipeline_manager:
            logger.error("TTSPipelineManager instance is required.")
            raise ValueError("TTSPipelineManager instance cannot be None.")

    def synthesize_speech(self, text: str, voice: str = DEFAULT_VOICE) -> tuple[np.ndarray | None, int | None]:
        """
        Synthesizes speech from text using a managed KPipeline.

        Args:
            text (str): The text to synthesize.
            voice (str): The voice to use for synthesis. Defaults to DEFAULT_VOICE.

        Returns:
            tuple[np.ndarray | None, int | None]: A tuple containing the audio data as a NumPy array
                                                  and the sample rate. Returns (None, None) on failure.
        """
        if not text:
            logger.warning("Synthesize speech called with empty text.")
            return None, None

        pipeline = None
        try:
            logger.info(f"Requesting pipeline for voice: '{voice}'")
            pipeline = self.pipeline_manager.get_pipeline()

            if not pipeline:
                logger.error("Failed to acquire a TTS pipeline from the manager.")
                return None, None

            logger.info(f"Pipeline acquired. Synthesizing text: '{text[:50]}...' using voice '{voice}'")
            synthesis_start_time = time.time()

            # The KPipeline call returns a generator
            generator = pipeline(text, voice=voice)

            audio_chunks = []
            first_chunk_time = None
            
            for i, (gs, ps, audio_segment) in enumerate(generator):
                if i == 0:
                    first_chunk_time = time.time() - synthesis_start_time
                    logger.info(f"Time to first audio chunk: {first_chunk_time:.3f}s")
                logger.debug(f"Received audio chunk {i}, gs: {gs}, ps: {ps}, segment length: {len(audio_segment)}")
                audio_chunks.append(audio_segment)
            
            if not audio_chunks:
                logger.warning("TTS synthesis resulted in no audio chunks.")
                return None, None

            # Concatenate all audio chunks
            full_audio = np.concatenate(audio_chunks)
            total_synthesis_time = time.time() - synthesis_start_time
            logger.info(f"Speech synthesized successfully. Total audio duration: {len(full_audio)/SAMPLE_RATE:.2f}s. Total synthesis time: {total_synthesis_time:.3f}s")
            
            return full_audio, SAMPLE_RATE

        except Exception as e:
            logger.error(f"Error during speech synthesis: {e}", exc_info=True)
            return None, None
        finally:
            if pipeline:
                self.pipeline_manager.release_pipeline(pipeline)
                logger.info("Pipeline released back to the manager.")

# Example Usage (for testing purposes - requires a running manager setup)
if __name__ == "__main__":
    from .config import DEFAULT_LANG_CODE
    # This is a simplified setup for testing. 
    # In a real app, manager would be initialized once.
    print("Setting up a dummy TTSPipelineManager for testing TTSService...")
    # Ensure KPipeline and its dependencies (like espeak-ng) are available
    try:
        manager = TTSPipelineManager(lang_code=DEFAULT_LANG_CODE)
        service = TTSService(pipeline_manager=manager)

        test_text = "नमस्ते दुनिया, यह एक परीक्षण है।"
        print(f"\nTesting synthesis with text: '{test_text}'")
        
        audio_data, sample_rate = service.synthesize_speech(test_text)

        if audio_data is not None and sample_rate is not None:
            print(f"Synthesis successful. Sample rate: {sample_rate}, Audio data shape: {audio_data.shape}, dtype: {audio_data.dtype}")
            # Optionally, save to a file to verify
            # import soundfile as sf
            # sf.write("test_output.wav", audio_data, sample_rate)
            # print("Saved test output to test_output.wav")
        else:
            print("Synthesis failed.")
        
        manager.shutdown()
        print("Dummy manager shut down.")

    except ImportError as ie:
        print(f"Import error, ensure kokoro and its dependencies are installed: {ie}")
    except Exception as ex:
        print(f"An error occurred during TTSService test: {ex}")
