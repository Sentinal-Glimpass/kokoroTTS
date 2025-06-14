import asyncio
import time
import aiohttp
import json

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
][:2]

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
    try:
        async with session.post(url, headers=headers, json=payload) as response:
            response_status = response.status
            response_content_type = response.headers.get('Content-Type', '')
            # Ensure the response body is read to properly calculate timing
            await response.read()
            end_time = time.time()
            latency = end_time - start_time
            
            if response_status == 200 and 'audio/wav' in response_content_type.lower():
                print(f"Call {call_num} successful. Text: '{text}'. Latency: {latency:.4f} seconds.")
                return latency, text, None
            else:
                error_message = f"Call {call_num} failed. Text: '{text}'. Status: {response_status}, Content-Type: {response_content_type}. Latency: {latency:.4f} seconds."
                print(error_message)
                return latency, text, error_message
                
    except aiohttp.ClientError as e:
        end_time = time.time()
        latency = end_time - start_time
        error_message = f"Call {call_num} request exception for text '{text}': {e}. Latency: {latency:.4f} seconds."
        print(error_message)
        return latency, text, error_message
    except Exception as e:
        end_time = time.time()
        latency = end_time - start_time
        error_message = f"Call {call_num} an unexpected error occurred for text '{text}': {e}. Latency: {latency:.4f} seconds."
        print(error_message)
        return latency, text, error_message

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, text in enumerate(hindi_texts):
            tasks.append(fetch_tts(session, text, i + 1))
        
        results = await asyncio.gather(*tasks)
        
        print("\n--- Latency Test Report ---")
        successful_calls = 0
        total_latency = 0
        min_latency = float('inf')
        max_latency = 0
        
        for latency, text, error in results:
            if error is None:
                successful_calls += 1
                total_latency += latency
                if latency < min_latency:
                    min_latency = latency
                if latency > max_latency:
                    max_latency = latency
            else:
                print(f"  Error for text '{text}': {error}")

        print(f"\nTotal calls made: {len(hindi_texts)}")
        print(f"Successful calls: {successful_calls}")
        print(f"Failed calls: {len(hindi_texts) - successful_calls}")
        
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