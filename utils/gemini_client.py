import google.generativeai as genai
from typing import Optional, Dict, Any
import time
from config import Config

from utils.langfuse_client import langfuse
from utils.trace_context import get_trace_id


class GeminiClient:
    """
    Manages interactions with Google Gemini LLM.
    Provides token tracking and response time metrics.
    """
    
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini API
        genai.configure(api_key=Config.GEMINI_API_KEY)
        
        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=Config.GEMINI_MODEL,
            generation_config={
                "temperature": Config.GEMINI_TEMPERATURE,
                "max_output_tokens": Config.GEMINI_MAX_TOKENS,
            }
        )
        
        # Metrics tracking
        self.total_tokens = 0
        self.total_requests = 0
        self.request_history = []
        
        # Persistent chat session
        self.active_chat = None
        self.chat_system_instruction = None
    
    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        trace_id = get_trace_id()

        # Prepare full prompt
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"

        try:
            # --- LANGFUSE GENERATION (OFFICIAL v2 API) ---
            with langfuse.start_as_current_observation(
                as_type="generation",
                name="gemini.generate",
                model=Config.GEMINI_MODEL,
                
                input={
                    "prompt": prompt,
                    "system_instruction": system_instruction,
                },
            ) as generation:

                # --- ACTUAL GEMINI CALL ---
                response = self.model.generate_content(full_prompt)

                response_time = time.time() - start_time

                input_tokens = (
                    response.usage_metadata.prompt_token_count
                    if hasattr(response, "usage_metadata")
                    else 0
                )
                output_tokens = (
                    response.usage_metadata.candidates_token_count
                    if hasattr(response, "usage_metadata")
                    else 0
                )
                total_tokens = input_tokens + output_tokens

                # Update internal metrics
                self.total_tokens += total_tokens
                self.total_requests += 1

                self.request_history.append({
                    "timestamp": time.time(),
                    "response_time": response_time,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "model": Config.GEMINI_MODEL,
                })

                # --- UPDATE LANGFUSE GENERATION ---
                generation.update(
                    output=response.text,
                    usage={
                        "input": input_tokens,
                        "output": output_tokens,
                    },
                    metadata={
                        "response_time_sec": response_time,
                        "finish_reason": (
                            response.candidates[0].finish_reason.name
                            if response.candidates
                            else None
                        ),
                    },
                )

                return {
                    "status": "success",
                    "text": response.text,
                    "response_time": response_time,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "finish_reason": (
                        response.candidates[0].finish_reason.name
                        if response.candidates
                        else None
                    ),
                }

        except Exception as e:
            response_time = time.time() - start_time
            error_str = str(e)

            # Detect quota errors
            error_type = "unknown"
            retry_after = None
            quota_info = {}

            if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                error_type = "quota_exceeded"

                import re
                retry_match = re.search(r"retry.*?(\d+(?:\.\d+)?)\s*[sS]", error_str)
                if retry_match:
                    retry_after = float(retry_match.group(1))

                limit_match = re.search(r"limit:\s*(\d+)", error_str)
                if limit_match:
                    quota_info["limit"] = int(limit_match.group(1))

            # --- LANGFUSE ERROR OBSERVATION ---
            with langfuse.start_as_current_observation(
                as_type="generation",
                name="gemini.generate.error",
              
            ) as generation:
                generation.update(
                    metadata={
                        "error": error_str,
                        "error_type": error_type,
                        "retry_after": retry_after,
                        "quota_info": quota_info,
                        "response_time_sec": response_time,
                    }
                )

            return {
                "status": "error",
                "text": "",
                "response_time": response_time,
                "error": error_str,
                "error_type": error_type,
                "retry_after": retry_after,
                "quota_info": quota_info,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            }

    
    def generate_structured(self, prompt: str, system_instruction: Optional[str] = None, 
                          response_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a structured response (JSON) from the LLM
        
        Args:
            prompt: The user prompt/query
            system_instruction: Optional system instruction
            response_format: Expected format description
            
        Returns:
            dict: Contains response, tokens, and timing
        """
        # Add JSON formatting instruction
        format_instruction = "\n\nRespond with valid JSON only. Do not include markdown code blocks or explanations."
        if response_format:
            format_instruction += f"\n\nExpected format:\n{response_format}"
        
        enhanced_prompt = prompt + format_instruction
        
        return self.generate(enhanced_prompt, system_instruction)
    
    def chat(self, message: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message in an ongoing conversation
        
        Args:
            message: The new message to send
            system_instruction: System instruction (only applied on first message of conversation)
            
        Returns:
            dict: Contains response, tokens, and timing
        """
        start_time = time.time()
        
        try:
            # Initialize chat session on first message
            if self.active_chat is None:
                self.active_chat = self.model.start_chat(history=[])
                self.chat_system_instruction = system_instruction
                
                # Set system instruction on first message
                if system_instruction:
                    self.active_chat.send_message(f"System: {system_instruction}")
            
            # Send the new message
            response = self.active_chat.send_message(message)
            
            # Calculate metrics
            response_time = time.time() - start_time
            
            input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
            output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
            total_tokens = input_tokens + output_tokens
            
            # Update tracking
            self.total_tokens += total_tokens
            self.total_requests += 1
            
            request_data = {
                "timestamp": time.time(),
                "response_time": response_time,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "model": Config.GEMINI_MODEL
            }
            self.request_history.append(request_data)
            
            return {
                "status": "success",
                "text": response.text,
                "response_time": response_time,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            error_str = str(e)
            
            # Check for quota/rate limit errors
            error_type = "unknown"
            retry_after = None
            quota_info = {}
            
            if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                error_type = "quota_exceeded"
                
                # Try to extract retry delay
                import re
                retry_match = re.search(r'retry.*?(\d+(?:\.\d+)?)\s*[sS]', error_str)
                if retry_match:
                    retry_after = float(retry_match.group(1))
                
                # Extract quota limit info
                limit_match = re.search(r'limit:\s*(\d+)', error_str)
                if limit_match:
                    quota_info["limit"] = int(limit_match.group(1))
            
            return {
                "status": "error",
                "text": "",
                "response_time": response_time,
                "error": error_str,
                "error_type": error_type,
                "retry_after": retry_after,
                "quota_info": quota_info,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            }
    
    def reset_chat(self):
        """Reset the conversation to start fresh"""
        self.active_chat = None
        self.chat_system_instruction = None
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics about LLM usage
        
        Returns:
            dict: Metrics including total tokens, requests, and averages
        """
        if not self.request_history:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_time": 0,
                "avg_tokens_per_request": 0,
                "avg_response_time": 0
            }
        
        total_time = sum(req["response_time"] for req in self.request_history)
        avg_time = total_time / len(self.request_history)
        avg_tokens = self.total_tokens / len(self.request_history)
        
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_time": total_time,
            "avg_tokens_per_request": avg_tokens,
            "avg_response_time": avg_time,
            "request_history": self.request_history
        }
    
    def reset_metrics(self):
        """Reset all metrics tracking"""
        self.total_tokens = 0
        self.total_requests = 0
        self.request_history = []