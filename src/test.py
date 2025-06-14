import asyncio
import time
import aiohttp
import json
import tempfile
import os
import soundfile as sf
import numpy as np

try:
    from playsound import playsound
except ImportError:
    playsound = None
    print("Warning: 'playsound' library not found. Audio playback will be skipped. Install it with 'pip install playsound'")

# Your deployed service URL
url = "https://kokoro-tts-136433412517.us-central1.run.app/synthesize"

# Request headers
headers = {
    "accept": "application/json",
    "Content-Type": "application/json"
}

# List of 10 different Hindi texts
# List of 30 different Hindi texts
hindi_texts = [
    "नमस्ते दुनिया",
    "आपका दिन कैसा चल रहा है?",
    "मुझे यह सुनकर खुशी हुई",
    "क्या आप मेरी मदद कर सकते हैं?",
    "भारत एक खूबसूरत देश है",
    "मैं हिंदी सीख रहा हूँ",
    "आज मौसम बहुत अच्छा है",
    "कृपया धीरे बोलिए",
    "यह कितने का है?",
    "धन्यवाद, फिर मिलेंगे",
    "यह रास्ता कहाँ जाता है?",
    "मुझे भूख लगी है।",
    "क्या आप शाकाहारी हैं?",
    "यह बहुत स्वादिष्ट है।",
    "शुभ प्रभात!",
    "शुभ रात्रि!",
    "आपका स्वागत है।",
    "क्षमा करें, मैं समझा नहीं।",
    "यह एक दिलचस्प कहानी है।",
    "मुझे संगीत पसंद है।",
    "आपकी पसंदीदा फिल्म कौन सी है?",
    "मैं तुमसे सहमत हूँ।",
    "यह जानकारी बहुत उपयोगी है।",
    "हमें समय पर पहुँचना चाहिए।",
    "क्या आप इसे दोहरा सकते हैं?",
    "यह एक अच्छा विचार है।",
    "मुझे आपकी मदद की ज़रूरत है।",
    "हम कल मिलेंगे।",
    "यह सचमुच अद्भुत है!",
    "सावधान रहें।"
][3:8]

async def fetch_tts(session, text, call_num):
    payload = {
        "text": text,
        "lang_code": "h",
        "voice": "hf_alpha",
        "speed": 1,
        "api_key": "f65a86f5ad86f5d86f4ad86f4a8f58asf58as56fa8"
    }
    
    start_time = time.time()
    print(f"Starting call {call_num} with text: '{text}'")
    audio_data = None 
    try:
        async with session.post(url, headers=headers, json=payload) as response:
            response_status = response.status
            response_content_type = response.headers.get('Content-Type', '')
            audio_data = await response.read() # Capture audio data
            end_time = time.time()
            latency = end_time - start_time
            
            if response_status == 200 and 'audio/l16' in response_content_type.lower(): # Expecting raw PCM L16
                print(f"Call {call_num} successful. Text: '{text}'. Latency: {latency:.4f} seconds.")
                return latency, text, None, audio_data
            else:
                error_message = f"Call {call_num} failed. Text: '{text}'. Status: {response_status}, Content-Type: {response_content_type}. Latency: {latency:.4f} seconds."
                print(error_message)
                return latency, text, error_message, None
                
    except aiohttp.ClientError as e:
        current_time = time.time()
        latency_val = current_time - start_time
        error_message = f"Call {call_num} request exception for text '{text}': {e}. Latency: {latency_val:.4f} seconds."
        print(error_message)
        return latency_val, text, error_message, None
    except Exception as e:
        current_time = time.time()
        latency_val = current_time - start_time
        error_message = f"Call {call_num} an unexpected error occurred for text '{text}': {e}. Latency: {latency_val:.4f} seconds."
        print(error_message)
        return latency_val, text, error_message, None

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, text in enumerate(hindi_texts):
            tasks.append(fetch_tts(session, text, i + 1))
        
        results = await asyncio.gather(*tasks)
        
        print("\n--- Latency and Audio Quality Test Report ---")
        successful_calls = 0
        total_latency = 0
        min_latency = float('inf')
        max_latency = 0
        latencies = []
        failed_requests_details = []
        
        for i, result in enumerate(results):
            latency, text, error, audio_content = result # Unpack audio_content
            total_latency += latency
            latencies.append(latency)
            if error:
                failed_requests_details.append({"text": text, "error": error, "latency": latency})
            else:
                successful_calls += 1
                if latency < min_latency:
                    min_latency = latency
                if latency > max_latency:
                    max_latency = latency
                if audio_content and playsound: # Check if audio_content exists and playsound is available
                    try:
                        # audio_content is raw PCM bytes. Convert to numpy array then write as WAV for playsound.
                        # Assuming 16-bit mono PCM, which is what main.py is configured to send.
                        # Sample rate is 24000 Hz as defined in tts_service.py and used in main.py's media type.
                        sample_rate = 24000 # Should match server output
                        channels = 1      # Assuming mono
                        
                        # Convert bytes to int16 NumPy array
                        pcm_data_np = np.frombuffer(audio_content, dtype=np.int16)

                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav_file:
                            sf.write(tmp_wav_file.name, pcm_data_np, samplerate=sample_rate, channels=channels, subtype='PCM_16')
                            tmp_wav_path = tmp_wav_file.name
                        
                        print(f"\nPlaying audio for call {i+1} (Text: '{text}') from temporary WAV: {tmp_wav_path}")
                        playsound(tmp_wav_path)
                        print(f"Finished playing audio for call {i+1}.")
                        os.remove(tmp_wav_path) # Clean up the temporary file
                    except Exception as e:
                        print(f"Error playing audio for text '{text}': {e}")
                elif not audio_content and not error:
                     print(f"No audio content received for successful call {i+1} (Text: '{text}'), skipping playback.")
                elif not playsound:
                    print(f"Skipping audio playback for text '{text}' (playsound library not available or failed to import).")

        print(f"\nTotal calls made: {len(hindi_texts)}")
        print(f"Successful calls: {successful_calls}")
        failed_calls = len(hindi_texts) - successful_calls
        print(f"Failed calls: {failed_calls}")
        
        if successful_calls > 0:
            average_latency = total_latency / successful_calls
            print(f"Minimum latency for successful calls: {min_latency:.4f} seconds")
            print(f"Maximum latency for successful calls: {max_latency:.4f} seconds")
            print(f"Average latency for successful calls: {average_latency:.4f} seconds")
        else:
            print("No calls were successful.")

if __name__ == "__main__":
    print(f"Starting TTS latency test for {len(hindi_texts)} parallel calls to: {url}")
    asyncio.run(main())