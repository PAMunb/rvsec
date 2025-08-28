#!/usr/bin/env python3
"""
Simple GPU memory manager for vision model benchmarks.
Handles model loading/unloading with limited VRAM (16GB).
"""

import subprocess
import time
import logging
from typing import Optional, List

class SimpleGPUManager:
    """Simple GPU memory management - just ollama stop + sleep."""
    
    def __init__(self, wait_time: int = 20):
        self.wait_time = wait_time
        self.current_model: Optional[str] = None
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for GPU manager."""
        logger = logging.getLogger("SimpleGPUManager")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def switch_model(self, new_model: str) -> bool:
        """
        Switch to a new model with simple memory management.
        
        Args:
            new_model: Name of the model to load
            
        Returns:
            True if switch was successful
        """
        
        if self.current_model == new_model:
            self.logger.info(f"Model {new_model} already active")
            return True
        
        self.logger.info(f"Switching from {self.current_model} to {new_model}")
        
        # Stop all models to free memory
        self.stop_all_models()
        
        # Wait for memory to clear
        self.logger.info(f"Waiting {self.wait_time} seconds for GPU memory to clear...")
        time.sleep(self.wait_time)
        
        # Test new model
        success = self.test_model(new_model)
        
        if success:
            self.current_model = new_model
            self.logger.info(f"✅ Successfully switched to {new_model}")
        else:
            self.logger.error(f"❌ Failed to switch to {new_model}")
            
        return success
    
    def stop_all_models(self) -> None:
        """Stop all ollama models."""
        
        self.logger.info("🛑 Stopping all Ollama models...")
        
        try:
            # First, get list of running models
            ps_result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if ps_result.returncode == 0:
                # Parse running models from ps output
                lines = ps_result.stdout.strip().split('\n')[1:]  # Skip header
                running_models = []
                
                for line in lines:
                    if line.strip():
                        model_name = line.split()[0]  # First column is model name
                        running_models.append(model_name)
                
                # Stop each running model
                for model in running_models:
                    self.logger.info(f"🛑 Stopping model: {model}")
                    stop_result = subprocess.run(
                        ["ollama", "stop", model],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if stop_result.returncode == 0:
                        self.logger.info(f"✅ Stopped model: {model}")
                    else:
                        self.logger.warning(f"⚠️ Failed to stop {model}: {stop_result.stderr}")
                
                if not running_models:
                    self.logger.info("No models were running")
                else:
                    self.logger.info(f"Stopped {len(running_models)} model(s)")
                    
            else:
                self.logger.warning(f"Failed to get running models: {ps_result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout stopping models")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error stopping models: {e}")
        except FileNotFoundError:
            self.logger.error("ollama command not found")
        
        self.current_model = None
    
    def test_model(self, model_name: str) -> bool:
        """
        Test if a model can be loaded and responds.
        
        Args:
            model_name: Name of the model to test
            
        Returns:
            True if model loaded and responding
        """
        
        self.logger.info(f"🧪 Testing model: {model_name}")
        
        try:
            from ollama import Client
            client = Client(host="http://localhost:11434")
            
            # Simple test message
            test_response = client.chat(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": "Test"
                    }
                ],
                options={"num_predict": 5},  # Very short response
                stream=False
            )
            
            if test_response and test_response.message:
                self.logger.info(f"✅ Model {model_name} loaded and responding")
                return True
            else:
                self.logger.error(f"❌ Model {model_name} not responding properly")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to test model {model_name}: {e}")
            return False
    
    def cleanup(self) -> None:
        """Final cleanup - stop all models."""
        
        self.logger.info("🧹 Final cleanup...")
        self.stop_all_models()
        time.sleep(5)  # Extra wait for cleanup


def test_models_sequentially(models: List[str], test_function, gpu_manager: SimpleGPUManager, **kwargs):
    """
    Test multiple models sequentially with GPU management.
    
    Args:
        models: List of model names to test
        test_function: Function to call for each model (model_name, **kwargs)
        gpu_manager: GPU manager instance
        **kwargs: Additional arguments to pass to test_function
        
    Returns:
        Dictionary of results by model name
    """
    
    logger = logging.getLogger("SequentialModelTester")
    results = {}
    
    logger.info(f"🚀 Starting sequential testing of {len(models)} models")
    
    for i, model_name in enumerate(models, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTING MODEL {i}/{len(models)}: {model_name}")
        logger.info(f"{'='*60}")
        
        # Switch to the model with memory management
        if not gpu_manager.switch_model(model_name):
            logger.error(f"❌ Failed to load model {model_name} - skipping")
            results[model_name] = None
            continue
        
        try:
            # Run the test function
            logger.info(f"🧪 Running tests for {model_name}...")
            result = test_function(model_name, **kwargs)
            results[model_name] = result
            
            logger.info(f"✅ Completed testing {model_name}")
            
        except Exception as e:
            logger.error(f"❌ Error testing {model_name}: {e}")
            results[model_name] = None
        
        # Progress update
        logger.info(f"📊 Progress: {i}/{len(models)} models completed")
        
        # Brief pause between models (in addition to the switch delay)
        if i < len(models):
            logger.info("⏱️ Brief pause before next model...")
            time.sleep(3)
    
    # Final cleanup
    logger.info("🧹 Final cleanup of all models...")
    gpu_manager.cleanup()
    
    # Summary
    successful = sum(1 for r in results.values() if r is not None)
    logger.info(f"🏁 Sequential testing completed: {successful}/{len(models)} models successful")
    
    return results