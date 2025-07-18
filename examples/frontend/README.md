# Frontend Examples

This directory contains example React/Next.js components for building a document processing frontend that works with the Pie-Extractor backend.

## Getting Started

1. Navigate to this directory:
   ```bash
   cd examples/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn
   ```

3. Copy the environment file and update with your configuration:
   ```bash
   cp .env.local.example .env.local
   ```

4. Run the development server:
   ```bash
   npm run dev
   # or
   yarn dev
   ```

## Example Components

- `components/auth/` - Authentication components including social login
- `components/documents/` - Document listing and management
- `components/preview/` - Document preview with dynamic right panel
- `pages/` - Example page implementations
- `services/` - API service layer
- `types/` - TypeScript type definitions

## Integration with Backend

Update the API base URL in `.env.local` to point to your Pie-Extractor backend.

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [Material-UI Documentation](https://mui.com/material-ui/getting-started/)
- [React Query Documentation](https://tanstack.com/query/latest)
