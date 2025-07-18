"""
Concurrent usage example for the OpenRouter API Manager.

This example demonstrates how the system handles multiple concurrent instances
with automatic API key management and rotation.
"""
import os
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from openrouter_manager import OpenRouterClient, APIKeyManager, InstanceManager

class Worker(threading.Thread):
    """Worker thread that processes tasks using the OpenRouter API."""
    
    def __init__(self, worker_id, api_key_manager):
        super().__init__()
        self.worker_id = worker_id
        self.api_key_manager = api_key_manager
        self.instance_manager = InstanceManager(api_key_manager)
        self.client = OpenRouterClient(self.instance_manager)
        
    def run(self):
        """Run the worker thread."""
        try:
            # Simulate different types of work
            work_type = random.choice(["text", "image"])
            
            if work_type == "text":
                # Process some text
                result = self.client.process_text(
                    f"This is a test from worker {self.worker_id}",
                    model="deepseek-ai/deepseek-r1"
                )
                print(f"Worker {self.worker_id} processed text: {result['text'][:50]}...")
            else:
                # Process an image (simulated)
                result = self.client.process_image(
                    image_path=f"test_image_{random.randint(1, 5)}.jpg",
                    model="meta-llama/llama-3.2-90b-vision-instruct"
                )
                print(f"Worker {self.worker_id} processed image: {result['text'][:50]}...")
                
            # Simulate work time
            time.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            print(f"Worker {self.worker_id} error: {e}")

def main(num_workers=5, max_workers=10):
    """Run multiple worker threads with shared API key management."""
    # Initialize the API key manager
    api_key_manager = APIKeyManager("api_keys.db")
    
    # Add some test API keys (in production, use environment variables)
    for i in range(1, 4):
        if os.getenv(f"OPENROUTER_API_KEY_{i}"):
            api_key_manager.add_api_key(os.getenv(f"OPENROUTER_API_KEY_{i}"))
    
    # Create and start worker threads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(num_workers):
            worker = Worker(i, api_key_manager)
            futures.append(executor.submit(worker.run))
        
        # Wait for all workers to complete
        for future in futures:
            future.result()
    
    # Print final usage statistics
    print("\nAPI Key Usage:")
    for key, usage in api_key_manager.get_usage_statistics().items():
        print(f"{key[-4:]}: {usage} requests")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run concurrent API workers.')
    parser.add_argument('--workers', type=int, default=5,
                        help='Number of worker threads to spawn')
    parser.add_argument('--max-workers', type=int, default=10,
                        help='Maximum number of concurrent workers')
    
    args = parser.parse_args()
    
    print(f"Starting {args.workers} workers with max {args.max_workers} concurrent...")
    main(num_workers=args.workers, max_workers=args.max_workers)
