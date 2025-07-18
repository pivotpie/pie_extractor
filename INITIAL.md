# OpenRouter API Manager with Image Processing

## FEATURE:
Build an intelligent API key management system for OpenRouter that:
1. Supports multiple API keys with automatic rotation
2. Implements a smart key selection algorithm that:
   - Only rotates keys when current key exceeds 40 requests AND a new instance starts
   - Tracks usage per key per day
   - Handles multiple concurrent instances
3. Provides a clean interface for:
   - Image processing using vision models (Llama 3.2 90B Vision)
   - Text processing using Deepseek R1
   - Automatic fallback mechanisms
4. Includes monitoring and logging of API usage

## EXAMPLES:
The `examples/` directory contains:
- `basic_usage.py` - Basic usage of the API manager
- `image_processing.py` - Example of image-to-text extraction
- `text_processing.py` - Example of text analysis
- `concurrent_usage.py` - Example of handling multiple instances

## DOCUMENTATION:
- [OpenRouter API Documentation](https://openrouter.ai/docs)
- [Llama 3.2 90B Vision Model](https://openrouter.ai/models/meta-llama/llama-3.2-90b-vision-instruct)
- [Deepseek R1 Documentation](https://huggingface.co/deepseek-ai/DeepSeek-R1)
- [SQLite Python Documentation](https://docs.python.org/3/library/sqlite3.html)

## OTHER CONSIDERATIONS:
1. **Rate Limiting**:
   - Free tier: 50 requests/day, 20 requests/minute
   - Implement exponential backoff for rate limiting
   - Cache responses when possible

2. **Error Handling**:
   - Handle API timeouts
   - Manage invalid API responses
   - Log errors with sufficient context

3. **Security**:
   - Never expose API keys in logs
   - Validate all inputs
   - Implement request signing if required

4. **Performance**:
   - Use connection pooling for database connections
   - Implement request batching where possible
   - Cache frequently accessed data

5. **Testing**:
   - Mock API responses for testing
   - Test edge cases (e.g., network failures)
   - Include performance benchmarks

6. **Deployment**:
   - Environment variable configuration
   - Logging setup
   - Monitoring and alerting

## SUCCESS CRITERIA:
1. Successfully process images using vision models
2. Maintain accurate API key usage tracking
3. Handle concurrent instances without key conflicts
4. Stay within rate limits
5. Provide clear error messages and logging
6. Include comprehensive tests
7. Document all public APIs and usage examples

## NEXT STEPS:
1. Set up project structure
2. Implement core API key management
3. Add image processing capabilities
4. Implement text processing features
5. Add monitoring and logging
6. Write tests and documentation
