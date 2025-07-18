import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSignIn, useSignUp, useAuth } from '@clerk/clerk-react';
import type { ClerkAPIError } from '@clerk/types';
import { Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface OAuthCallbackParams {
  strategy?: string;
  redirect_url?: string;
  code?: string;
  state?: string;
}

const SSOCallback = () => {
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { signIn, setActive } = useSignIn();
  const { signUp } = useSignUp();
  const { isLoaded, userId, getToken } = useAuth();

  // Helper function to handle OAuth errors
  const handleOAuthError = useCallback((error: unknown, context: string) => {
    console.error(`OAuth Error (${context}):`, error);
    
    let errorMessage = 'There was an error signing in. Please try again.';
    
    // Type guard to check if error is a Clerk API error
    const isClerkError = (err: any): err is { errors: ClerkAPIError[] } => {
      return Array.isArray(err?.errors) && err.errors.every((e: any) => e?.message);
    };
    
    if (isClerkError(error) && error.errors?.[0]?.message) {
      errorMessage = error.errors[0].message;
    } else if (error instanceof Error) {
      errorMessage = error.message;
    }
    
    toast({
      title: 'Authentication Error',
      description: errorMessage,
      variant: 'destructive',
    });
    
    navigate('/sign-in');
  }, [navigate, toast]);

  // Handle the OAuth callback
  const handleOAuthCallback = useCallback(async () => {
    if (!isLoaded || !signIn) {
      console.log('Clerk or signIn not ready');
      return;
    }

    try {
      // Check if we have OAuth parameters in the URL
      const oauthParams: OAuthCallbackParams = {
        strategy: searchParams.get('strategy') || undefined,
        redirect_url: searchParams.get('redirect_url') || undefined,
        code: searchParams.get('code') || undefined,
        state: searchParams.get('state') || undefined,
      };

      console.log('OAuth callback parameters:', oauthParams);

      // If we have a code, try to complete the OAuth flow
      if (oauthParams.code && oauthParams.state) {
        console.log('Completing OAuth flow...');
        
        try {
          // First, try to get an active session
          const session = await signIn.create({
            strategy: 'ticket',
            ticket: oauthParams.code,
          });

          if (session.status === 'complete') {
            console.log('OAuth flow completed successfully');
            await setActive({ session: session.createdSessionId });
            
            // Get a fresh token to verify the session
            const token = await getToken();
            console.log('Session token obtained:', token ? 'Yes' : 'No');
            
            // Force a full page reload to ensure all auth state is properly set
            window.location.href = '/';
            return;
          }
        } catch (error) {
          console.error('Error completing OAuth flow:', error);
          handleOAuthError(error, 'completing OAuth flow');
          return;
        }
      }

      // If we get here, we don't have the expected OAuth parameters
      // Try to handle it as a regular sign-in/sign-up flow
      console.log('Handling as regular sign-in/sign-up flow');
      
      if (userId) {
        console.log('User already signed in, redirecting to home');
        navigate('/');
        return;
      }

      // Check sign-in state
      if (signIn.status === 'complete') {
        console.log('Sign in complete, setting active session');
        await setActive({ session: signIn.createdSessionId });
        window.location.href = '/';
        return;
      }

      // Check sign-up state
      if (signUp?.status === 'complete') {
        console.log('Sign up complete, setting active session');
        await setActive({ session: signUp.createdSessionId });
        window.location.href = '/';
        return;
      }

      // If we get here, we couldn't handle the OAuth flow
      console.error('Could not handle OAuth callback. State:', {
        hasSignIn: !!signIn,
        signInStatus: signIn?.status,
        hasSignUp: !!signUp,
        signUpStatus: signUp?.status,
        hasUserId: !!userId,
        searchParams: Object.fromEntries(searchParams.entries())
      });

      // Try to recover by redirecting to the home page
      toast({
        title: 'Completing sign in...',
        description: 'Please wait while we complete your sign in.',
      });
      window.location.href = '/';
      
    } catch (error) {
      handleOAuthError(error, 'handling OAuth callback');
    } finally {
      setLoading(false);
    }
  }, [isLoaded, signIn, signUp, userId, setActive, getToken, searchParams, navigate, toast, handleOAuthError]);

  useEffect(() => {
    if (!isLoaded) {
      console.log('Clerk not yet loaded');
      return;
    }

    console.log('Setting up OAuth callback handler');
    const timer = setTimeout(handleOAuthCallback, 1000);
    
    return () => {
      console.log('Cleaning up OAuth callback handler');
      clearTimeout(timer);
    };
  }, [isLoaded, handleOAuthCallback]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Completing sign in...</p>
        </div>
      </div>
    );
  }

  // Default fallback
  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="text-center">
        <h2 className="text-xl font-semibold mb-2">Redirecting...</h2>
        <p className="text-muted-foreground">Please wait while we redirect you.</p>
      </div>
    </div>
  );
};

export default SSOCallback;
