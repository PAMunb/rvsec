"""
LangChain LLM integration with comprehensive Ollama metrics collection.
"""
import time
from typing import Dict, List, Optional, Tuple, Any
from collections import deque

from langchain_community.chat_models import ChatOllama
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import HumanMessage

from rv_agent.data_structures import LLMMetrics
from rv_agent.config import PrototypeConfig


class RVAgentMetricsCollector(BaseCallbackHandler):
    """
    LangChain callback handler for collecting comprehensive Ollama metrics.
    
    Captures all Ollama performance metrics via generation_info for analysis
    and parameter optimization in the grid search.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of metrics to retain
        """
        self.metrics_history: deque = deque(maxlen=max_history)
        self.current_config: Dict[str, Any] = {}
        
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Capture LLM configuration at start of generation."""
        invocation_params = kwargs.get('invocation_params', {})
        self.current_config = {
            'model': invocation_params.get('model', 'unknown'),
            'temperature': invocation_params.get('temperature', 0.0),
            'top_p': invocation_params.get('top_p', 1.0),
            'top_k': invocation_params.get('top_k', 40)
        }
        
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """
        Collect comprehensive Ollama metrics from LLM response.
        
        Extracts detailed performance data from Ollama's generation_info,
        providing equivalent metrics to rv-llm's OllamaLLM implementation.
        """
        if not response.generations or not response.generations[0]:
            return
            
        generation = response.generations[0][0]
        gen_info = generation.generation_info or {}
        
        # Extract comprehensive Ollama metrics
        prompt_tokens = gen_info.get('prompt_eval_count', 0)
        output_tokens = gen_info.get('eval_count', 0)
        total_tokens = prompt_tokens + output_tokens
        
        # Time metrics (in nanoseconds from Ollama)
        prompt_duration = gen_info.get('prompt_eval_duration', 0)
        output_duration = gen_info.get('eval_duration', 0) 
        total_duration = gen_info.get('total_duration', 0)
        load_duration = gen_info.get('load_duration', 0)
        
        # Create comprehensive metrics record
        metrics = LLMMetrics(
            timestamp=time.time(),
            model_name=self.current_config.get('model', 'unknown'),
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            prompt_duration=prompt_duration,
            output_duration=output_duration,
            total_duration=total_duration,
            load_duration=load_duration,
            temperature=self.current_config.get('temperature', 0.0),
            top_p=self.current_config.get('top_p', 1.0),
            top_k=self.current_config.get('top_k', 40)
        )
        
        self.metrics_history.append(metrics)
        
    def get_latest_metrics(self) -> Optional[LLMMetrics]:
        """Get the most recent metrics."""
        return self.metrics_history[-1] if self.metrics_history else None
        
    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self.metrics_history.clear()


class VisionModelClient:
    """
    LangChain-based client for vision model coordinate generation.
    
    Handles qwen2.5vl:7b model interactions with parameter configuration
    and comprehensive metrics collection for grid search analysis.
    """
    
    def __init__(self, config: PrototypeConfig):
        """
        Initialize vision model client.
        
        Args:
            config: Prototype configuration
        """
        self.config = config
        self.metrics_collector = RVAgentMetricsCollector()
        
        # Initialize with default parameters (will be updated per test)
        self._llm = None
        self._current_params = None
        
    def _create_llm(self, temperature: float, top_p: float, top_k: int) -> ChatOllama:
        """Create LangChain ChatOllama instance with specific parameters."""
        return ChatOllama(
            model=self.config.PRIMARY_MODEL,
            base_url=self.config.BASE_URL,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            num_predict=self.config.MAX_TOKENS,
            callbacks=[self.metrics_collector],
            timeout=self.config.TIMEOUT_SECONDS
        )
    
    def generate_coordinates(self, 
                           image_path: str, 
                           temperature: float, 
                           top_p: float, 
                           top_k: int) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
        """
        Generate coordinates for a screenshot using vision model.
        
        Args:
            image_path: Path to screenshot image
            temperature: LLM temperature parameter
            top_p: LLM top-p parameter  
            top_k: LLM top-k parameter
            
        Returns:
            Tuple of (coordinates, error_message)
            coordinates: (x, y) tuple if successful, None if failed
            error_message: Error description if failed, None if successful
        """
        try:
            # Create LLM with specific parameters
            llm = self._create_llm(temperature, top_p, top_k)
            
            # Create coordinate generation prompt
            prompt = self._create_coordinate_prompt(image_path)
            
            # Generate response
            start_time = time.time()
            
            # Create message with image
            message = HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"file://{image_path}"}}
            ])
            
            response = llm.invoke([message])
            
            # Parse coordinates from response
            coordinates = self._parse_coordinates_from_response(response.content)
            
            return coordinates, None
            
        except Exception as e:
            return None, str(e)
    
    def _create_coordinate_prompt(self, image_path: str) -> str:
        """
        Create prompt for coordinate generation based on research findings.
        
        Uses coordinate validation approach proven effective in vision research.
        """
        return """You are an expert Android UI automation assistant. 

Analyze this Android app screenshot and identify a clickable UI element that would be good for testing.

Please respond with ONLY the coordinates in this exact format:
COORDINATES: (x, y)

Where x and y are the pixel coordinates of the center of a clickable element.

Choose an element that is:
1. Clearly clickable (button, menu item, etc.)
2. Visible and not obscured
3. Not a system UI element (status bar, navigation bar)
4. Likely to be functionally important for testing

Respond only with the coordinate format shown above, nothing else."""

    def _parse_coordinates_from_response(self, response: str) -> Optional[Tuple[int, int]]:
        """
        Parse coordinates from LLM response.
        
        Args:
            response: LLM response text
            
        Returns:
            (x, y) coordinates if parsed successfully, None otherwise
        """
        try:
            # Look for "COORDINATES: (x, y)" pattern
            import re
            
            # Try multiple patterns to be robust
            patterns = [
                r'COORDINATES:\s*\((\d+),\s*(\d+)\)',
                r'\((\d+),\s*(\d+)\)',
                r'(\d+),\s*(\d+)',
                r'x:\s*(\d+).*y:\s*(\d+)',
                r'X:\s*(\d+).*Y:\s*(\d+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    x, y = int(match.group(1)), int(match.group(2))
                    
                    # Sanity check: reasonable screen coordinates
                    if 0 <= x <= 2000 and 0 <= y <= 3000:  # Reasonable mobile screen bounds
                        return (x, y)
            
            return None
            
        except (ValueError, AttributeError, IndexError):
            return None
    
    def get_latest_metrics(self) -> Optional[LLMMetrics]:
        """Get metrics from the most recent generation."""
        return self.metrics_collector.get_latest_metrics()


def create_vision_client(config: PrototypeConfig) -> VisionModelClient:
    """Factory function to create vision model client."""
    return VisionModelClient(config)