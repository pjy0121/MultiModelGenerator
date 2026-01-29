
import asyncio
import traceback
import google.generativeai as genai
from typing import List, Dict, Any
from .llm_client_interface import LLMClientInterface
from ..config import API_KEYS, NODE_EXECUTION_CONFIG
from ..utils import handle_llm_error

class GoogleLLMClient(LLMClientInterface):
    """Google AI Studio API client"""

    def __init__(self):
        """Initialize Google AI API client"""
        self.api_key = API_KEYS["google"]
        self.client = None
        
        if genai is None:
            return
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai
            except Exception:
                self.client = None
    
    def is_available(self) -> bool:
        """Check if Google AI API is available"""
        return genai is not None and self.client is not None and self.api_key is not None
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Return list of available Google AI models"""
        if not self.is_available():
            return []
        
        try:
            # Workaround for thinking field bug: direct REST API call
            import requests
            
            url = "https://generativelanguage.googleapis.com/v1beta/models"
            headers = {"x-goog-api-key": self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            models_data = data.get('models', [])
            
            available_models = []
            for model_data in models_data:
                model_name = model_data.get('name', '').replace('models/', '')
                supported_methods = model_data.get('supportedGenerationMethods', [])
                                
                # Filter only models capable of generation
                if 'generateContent' in supported_methods:
                    model_info = {
                        "value": model_name,
                        "label": model_name,
                        "provider": "google",
                        "model_type": model_name,
                        "disabled": False
                    }
                    available_models.append(model_info)            
            return available_models
            
        except Exception as e:
            return []
    
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = NODE_EXECUTION_CONFIG["max_tokens_default"]
    ):
        """Generate response via streaming (unified single interface)"""
        if not self.is_available():
            error_msg = handle_llm_error("google", model, Exception("API key not configured"), log_error=False)
            raise Exception(error_msg)
        
        try:
            # Add 'models/' prefix if not present in model name
            if not model.startswith('models/'):
                model = f'models/{model}'

            # Initialize generative model (temperature settings, etc.)
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            
            genai_model = genai.GenerativeModel(
                model, 
                generation_config=generation_config
            )
            
            print(f"🔄 Starting Google AI response generation...")

            # Async streaming response generation - real-time chunk transmission
            try:
                import concurrent.futures
                
                # Real-time streaming via queue
                chunk_queue = asyncio.Queue()

                # Store main event loop reference (for use in separate thread)
                main_loop = asyncio.get_event_loop()

                def _sync_generate_to_queue():
                    """Send synchronous streaming to queue in real-time"""
                    try:
                        response = genai_model.generate_content(prompt, stream=True)
                        for chunk in response:
                            if hasattr(chunk, 'text') and chunk.text:
                                # Request queue put to main loop
                                asyncio.run_coroutine_threadsafe(
                                    chunk_queue.put(chunk.text),
                                    main_loop
                                )
                        # Completion signal
                        asyncio.run_coroutine_threadsafe(
                            chunk_queue.put(None), 
                            main_loop
                        )
                    except Exception as e:
                        asyncio.run_coroutine_threadsafe(
                            chunk_queue.put(Exception(str(e))), 
                            main_loop
                        )
                
                # Execute in separate thread with ThreadPoolExecutor
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                main_loop.run_in_executor(executor, _sync_generate_to_queue)

                print(f"✅ Google AI streaming started")

                # Receive and send chunks from queue in real-time
                while True:
                    chunk = await chunk_queue.get()

                    # Completion signal
                    if chunk is None:
                        break

                    # Error check
                    if isinstance(chunk, Exception):
                        raise chunk

                    # Send chunk immediately
                    yield chunk
                    await asyncio.sleep(0)  # Yield control to other tasks
                
                executor.shutdown(wait=False)
                        
            except Exception as stream_e:
                error_detail = traceback.format_exc()
                print(f"⚠️ Google AI stream generation error: {stream_e}")
                print(f"⚠️ Detailed error info:\n{error_detail}")
                raise

        except Exception as e:
            error_msg = str(e)
            # Provide clearer explanation for specific error messages
            if "finish_message" in error_msg:
                error_msg = f"Error due to Google AI API structure change: {error_msg}"
            elif "Unknown field" in error_msg:
                error_msg = f"Error due to Google AI API field change: {error_msg}"

            raise Exception(f"Google AI streaming response generation failed: {error_msg}")
        