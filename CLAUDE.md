# Project Rules and Conventions

## Project Overview
This project implements an intelligent API key management system for OpenRouter that handles multiple models, with a focus on image processing and text analysis workflows.

## Code Structure
- Keep files under 500 lines of code
- Organize code into logical modules (client, models, utils)
- Use type hints for better code clarity (Python 3.10+)
- Follow clean architecture principles

## Frontend Conventions
- Use React with TypeScript
- Follow component-based architecture
- Use functional components with hooks
- Implement responsive design with Tailwind CSS
- Follow atomic design principles for components

## Backend Conventions
- Use Python 3.10+
- Follow RESTful API design principles
- Implement proper error handling and logging
- Use dependency injection for testability
- Document all API endpoints with OpenAPI/Swagger

## Testing Requirements
- Write unit tests for all major components
- Aim for 80%+ test coverage
- Use pytest for backend testing
- Use Jest and React Testing Library for frontend tests
- Include integration tests for API interactions
- Mock external API calls in tests

## Style Conventions
- Follow PEP 8 for Python code
- Use ESLint and Prettier for frontend code
- Use Google-style docstrings for Python
- Use JSDoc for JavaScript/TypeScript documentation
- Maximum line length: 100 characters
- Use f-strings for Python string formatting

## Documentation Standards
- Document all public classes and functions
- Include usage examples in docstrings
- Keep README.md updated with setup instructions
- Document all environment variables
- Maintain CHANGELOG.md for version history
- Use TypeScript interfaces/types for frontend props

## API Key Management
- Never commit API keys to version control
- Use environment variables for sensitive data
- Implement secure key rotation
- Log key usage for monitoring and auditing
- Validate API keys before use
- Implement rate limiting for API endpoints

## Error Handling
- Use custom exceptions for expected errors
- Include meaningful error messages
- Implement structured logging
- Handle rate limits gracefully
- Include error codes in API responses
- Log stack traces for debugging

## Performance
- Implement caching where appropriate (Redis recommended)
- Use async/await for I/O bound operations
- Batch requests when possible
- Monitor API usage and quotas
- Implement connection pooling for database/API connections
- Optimize frontend bundle size

## Dependency Management
### Backend (Python)
- Keep all dependencies in `requirements.txt` and `requirements-dev.txt`
- Pin all dependency versions for reproducibility
- Use `pip-tools` for dependency management
- Document any version-specific requirements

### Frontend (JavaScript/TypeScript)
- Use `package.json` for dependency management
- Use exact versions (`1.2.3`) for production dependencies
- Document any peer dependencies
- Keep `node_modules` in `.gitignore`

## Security
- Validate all inputs (frontend and backend)
- Sanitize outputs to prevent XSS
- Use HTTPS for all API calls
- Implement proper CORS policies
- Use environment variables for sensitive data
- Regularly update dependencies for security patches
- Implement CSRF protection
- Use secure session management

## Version Control
- Follow Conventional Commits specification
- Use meaningful commit messages
- Create feature branches from `main`
- Open pull requests for code review
- Require code reviews before merging
- Keep the `main` branch always deployable
- Use semantic versioning (SemVer)

## Development Workflow
1. Create a new branch for each feature/fix
2. Write tests for new functionality
3. Run linters and tests before committing
4. Update documentation as needed
5. Create a pull request
6. Address review comments
7. Squash and merge when approved

## Environment Setup
- Document all required environment variables in `.env.example`
- Never commit `.env` files
- Use `python-dotenv` for local development
- Document required system dependencies
- Include setup scripts where possible

## Code Review Guidelines
- Check for security vulnerabilities
- Verify error handling
- Ensure proper test coverage
- Review for performance implications
- Check for code duplication
- Verify documentation is up to date
- Ensure cross-browser compatibility (frontend)

## Monitoring and Logging
- Implement structured logging
- Include request IDs for tracing
- Log errors with appropriate severity levels
- Monitor application health
- Set up alerts for critical errors
- Log performance metrics

## Deployment
- Use containerization (Docker)
- Document deployment process
- Implement CI/CD pipelines
- Use infrastructure as code
- Include rollback procedures
- Monitor production environment

## Maintenance
- Keep dependencies up to date
- Regularly review and update documentation
- Address security vulnerabilities promptly
- Monitor performance metrics
- Archive or remove unused code
- Keep third-party integrations updated
