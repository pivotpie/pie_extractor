# Authentication with Clerk

This document outlines the authentication system implementation using Clerk for the Pie-Extractor application.

## Overview

The authentication system uses [Clerk](https://clerk.com/) for handling user authentication, including:
- Email/password login
- Social logins (Google, GitHub, etc.)
- Session management
- User profile management

## Setup

### Environment Variables

Create a `.env` file in the frontend directory with the following variables:

```bash
# API Configuration
VITE_API_URL=http://localhost:8002/api/v1
VITE_FRONTEND_URL=http://localhost:8080

# Clerk Configuration
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
```

### Required Dependencies

- `@clerk/clerk-react`: Core Clerk React components and hooks
- `@clerk/types`: TypeScript types for Clerk
- `@vitejs/plugin-react`: React plugin for Vite
- `react-router-dom`: For routing and navigation

## Key Components

### 1. Main Application Setup (`main.tsx`)

Wraps the application with the `ClerkProvider` to provide authentication context:

```tsx
import { ClerkProvider } from '@clerk/clerk-react';

// ...

<ClerkProvider publishableKey={import.meta.env.VITE_CLERK_PUBLISHABLE_KEY}>
  <App />
</ClerkProvider>
```

### 2. Authentication Pages

#### Sign In Page (`SignInPage` component)
- Path: `/sign-in`
- Uses Clerk's `<SignIn>` component
- Customized with the application's theme

#### Sign Up Page (`SignUpPage` component)
- Path: `/sign-up`
- Uses Clerk's `<SignUp>` component
- Customized with the application's theme

### 3. Protected Routes

Uses the `AuthGuard` component to protect routes that require authentication:

```tsx
<Route
  path="/protected-route"
  element={
    <AuthGuard>
      <ProtectedComponent />
    </AuthGuard>
  }
/>
```

## Authentication Flow

1. **User Visits Protected Route**
   - If not authenticated, redirected to `/sign-in`
   - After successful authentication, redirected back to the original route

2. **Sign In**
   - User can sign in with email/password or social providers
   - Session is established upon successful authentication

3. **Sign Out**
   - User can sign out from any page
   - Session is terminated

## Social Login Configuration

Social logins are configured in the Clerk Dashboard:

1. Go to [Clerk Dashboard](https://dashboard.clerk.com/)
2. Select your application
3. Navigate to "User & Authentication" > "Social Connections"
4. Enable and configure desired social providers (Google, GitHub, etc.)

## API Integration

For API requests that require authentication, include the session token in the `Authorization` header:

```typescript
import { useAuth } from '@clerk/clerk-react';

function ApiComponent() {
  const { getToken } = useAuth();

  const fetchData = async () => {
    const token = await getToken();
    const response = await fetch('/api/protected-route', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    // Handle response
  };
}
```

## Error Handling

Common authentication errors are handled by Clerk's built-in components. For custom error handling:

```typescript
try {
  // Authentication logic
} catch (error) {
  if (error.errors?.[0]?.code === 'session_expired') {
    // Handle expired session
  }
}
```

## Testing

1. **Development Mode**
   - Run `npm run dev`
   - Visit `http://localhost:8080`
   - Test sign up, sign in, and protected routes

2. **Production**
   - Ensure all environment variables are set
   - Build with `npm run build`
   - Deploy the build output

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   - Ensure all required variables are set in `.env`
   - Restart the development server after changes

2. **CORS Issues**
   - Verify backend CORS settings allow requests from your frontend URL
   - Check network tab in browser devtools for CORS errors

3. **Session Issues**
   - Clear browser cookies and local storage
   - Verify Clerk dashboard configuration

## Security Considerations

- Never commit sensitive keys to version control
- Use HTTPS in production
- Regularly rotate API keys and secrets
- Monitor authentication logs in Clerk dashboard

## Resources

- [Clerk Documentation](https://clerk.com/docs)
- [React Integration Guide](https://clerk.com/docs/nextjs/get-started-with-nextjs)
- [API Reference](https://clerk.com/docs/reference/clerkjs)
