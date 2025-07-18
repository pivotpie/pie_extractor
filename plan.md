# OpenRouter Multi-Model Image Processing & API Key Management Plan

## Current Status
### Core API Implementation
- [x] Research OpenRouter's multimodal and text-only model capabilities and limits
- [x] Decide on best vision and text models for workflow (Llama 3.2 Vision, Deepseek R1)
- [x] Design workflow: extract text from image with vision model, process with text model
- [x] Define API key management logic (switch on new instance AND threshold exceeded)
- [x] Implement SQLite-based API key usage tracking and assignment
- [x] Integrate image extraction and text processing workflow with API key management logic
- [x] Implement core API key management and model workflow integration
- [x] Implement dynamic model selection and fallback logic in `ModelManager`
- [x] Implement core `OpenRouterClient` with request handling and retry logic
- [x] Test demo with multiple instances and API keys
- [x] Test fallback logic for vision and reasoning models
- [x] Implement `APIKeyManager` class with secure key storage
- [x] Implement `InstanceManager` for concurrent instance handling
- [x] Implement basic `OpenRouterClient` with core features

### Frontend Implementation
- [x] Scaffold frontend directory and initial config files
- [x] Implement TypeScript types for documents and authentication
- [x] Implement API service for document and authentication operations
- [x] Implement authentication context and hooks
- [x] Implement document list UI with status and details
- [x] Implement document preview page with dynamic right panel
- [x] Implement frontend authentication (GitHub & Google OAuth)
- [x] Deduplicate utility functions (formatDate, formatBytes)
- [x] Fix React hydration errors in dashboard

### Pending Tasks
#### Core Implementation
- [ ] Enhance `OpenRouterClient` with advanced features:
  - [ ] Rate limiting
  - [ ] Connection pooling
  - [ ] Streaming responses
  - [ ] Enhanced error handling
  - [ ] Automatic model fallback
  - [ ] Request batching

#### Testing & Quality
- [ ] Set up pytest framework
- [ ] Write unit tests for core components
- [ ] Add integration tests with mock API
- [ ] Implement CI/CD pipeline
- [ ] Achieve 80%+ test coverage
- [ ] Add end-to-end tests

#### Documentation
- [ ] Document setup, usage, and scaling considerations
- [ ] Update API documentation
- [ ] Create usage examples
- [ ] Maintain requirements.txt and requirements-dev.txt
- [ ] Ensure dependency update instructions are present in CLAUDE.md
- [ ] Update frontend example code snippets in `examples/frontend/`
- [ ] Document API key management strategy
- [ ] Document rate limiting and quota considerations

## Current Focus
1. Complete core implementation:
   - Finalize `APIKeyManager` with SQLite backend
   - Implement `InstanceManager` for concurrent operations
   - Enhance `OpenRouterClient` with remaining features

2. Testing infrastructure:
   - Set up testing framework
   - Add comprehensive test coverage
   - Implement CI/CD pipeline

3. Documentation:
   - Complete API documentation
   - Add usage examples
   - Document deployment process

## Key Implementation Details
### Models & API
- **Vision Model**: "meta-llama/llama-3.2-11b-vision-instruct:free"
- **Reasoning Model**: "deepseek/deepseek-r1-0528:free"
- **API Limits**: 
  - 50 requests/day total across all free models (increases to 1000 with $10+ balance)
  - 20 requests/minute rate limit
  - Each API request (image or text) counts as one request

### Key Management
- **Rotation Logic**:
  1. Switch only when current key has ≥40 requests
  2. Only on new instance initialization
- **Persistence**:
  - SQLite database for tracking API key usage
  - Instance-specific key assignments persisted until restart

### Intelligent Document Processing (IDP) System
1. **Document Ingestion Layer**
   - File type detection and routing
   - Document preprocessing
   - Batch processing support

2. **Vision Processing Layer**
   - Document analysis using vision models
   - Text block detection with coordinates
   - Layout understanding

3. **DeepSeek Integration**
   - Document understanding and structuring
   - Contextual analysis
   - Entity and relationship extraction

4. **Post-Processing Layer**
   - Text normalization
   - Structure reconstruction
   - Quality validation

5. **EDMS Integration**
   - Document storage
   - Metadata management
   - Search and retrieval

## Project Structure
```
Pie-Extractor/
├── CLAUDE.md                 # Project rules and conventions
├── INITIAL.md                # Feature requirements and specifications
├── PIE_EXTRACTOR_PLAN.md     # High-level project overview
├── plan.md                   # This file - Implementation plan & status
├── examples/                 # Example usage patterns
│   ├── frontend/            # Next.js frontend example
│   ├── basic_usage.py       # Basic API manager usage
│   ├── image_processing.py  # Image processing examples
│   ├── text_processing.py   # Text processing examples
│   └── concurrent_usage.py  # Concurrent instance handling
└── openrouter_manager/      # Core implementation
    ├── __init__.py
    ├── api.py              # API client
    ├── models.py          # Data models
    ├── key_manager.py     # API key management
    └── utils.py           # Helper functions
```

## Coding Standards & Conventions
All code must adhere to the following standards:

### Style & Formatting
- Follow PEP 8 style guide
- Maximum line length: 100 characters
- Use f-strings for string formatting
- Use type hints for all function signatures
- Follow consistent import ordering (standard library, third-party, local)

### Documentation
- Use Google-style docstrings for all public classes and functions
- Include examples in docstrings where helpful
- Document all environment variables
- Keep README.md updated with setup and usage instructions

### Error Handling
- Use custom exceptions for expected error cases
- Include meaningful error messages
- Implement proper logging (INFO for operations, DEBUG for debugging, ERROR for failures)
- Handle rate limits gracefully with exponential backoff

### Testing
- Write unit tests for all major components
- Aim for 80%+ test coverage
- Use pytest for testing framework
- Include integration tests for API interactions
- Mock external dependencies in tests

### Security
- Never commit API keys or sensitive data to version control
- Use environment variables for configuration
- Validate all inputs
- Sanitize all outputs
- Use HTTPS for all API calls
- Implement proper error handling to avoid information leakage

### Performance
- Implement caching where appropriate
- Use async/await for I/O bound operations
- Batch API requests when possible
- Monitor API usage and quotas

### Version Control
- Write clear, descriptive commit messages
- Create feature branches for new features
- Open pull requests for code review
- Keep the main branch in a deployable state

## OpenRouter Free Tier Notes
- Each API call (text/image) counts as one request
- Free tier limits: 20 req/min and 50 req/day (combined across all free models per account)
- If account balance ≥ $10, daily limit increases to 1000
- Limits are not per model, but per account
- For demos, monitor status and plan for contingencies as uptime is not guaranteed

## Model Management
- Vision models (e.g., Llama 3.2 90B Vision Instruct) support image upload via base64 or URL
- Deepseek R1 is text-only
- Multiple models can be used in a workflow by specifying the model ID per API call
- Extraction and training can be separated by model

## API Key Management Strategy
- Track API key usage centrally (SQLite)
- Switch keys only when:
  1. Usage for current key ≥ threshold (e.g., 40/day)
  2. A new instance is started
- Each instance keeps its key for its lifetime
- Sample code provided for SQLite-based tracking