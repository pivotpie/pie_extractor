import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/router';
import { authApi } from '@/services/api';
import { AuthState, User } from '@/types/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  resetError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [state, setState] = useState<{
    user: User | null;
    loading: boolean;
    error: string | null;
  }>({
    user: null,
    loading: true,
    error: null,
  });

  const router = useRouter();

  // Check if user is authenticated on initial load
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const session = await authApi.getSession();
        setState({ user: session.user, loading: false, error: null });
      } catch (error) {
        setState({ user: null, loading: false, error: null });
      }
    };

    checkAuth();
  }, []);

  const signIn = async (email: string, password: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const { user } = await authApi.signIn({ email, password });
      setState({ user, loading: false, error: null });
      router.push('/documents');
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to sign in',
      }));
      throw error;
    }
  };

  const signUp = async (name: string, email: string, password: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const { user } = await authApi.signUp({ name, email, password });
      setState({ user, loading: false, error: null });
      router.push('/documents');
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to sign up',
      }));
      throw error;
    }
  };

  const signOut = async () => {
    try {
      await authApi.signOut();
      setState({ user: null, loading: false, error: null });
      router.push('/login');
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to sign out',
      }));
      throw error;
    }
  };

  const resetError = () => {
    setState((prev) => ({ ...prev, error: null }));
  };

  return (
    <AuthContext.Provider
      value={{
        user: state.user,
        loading: state.loading,
        error: state.error,
        signIn,
        signUp,
        signOut,
        resetError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

/**
 * A higher-order component that provides authentication context to the wrapped component.
 * @param Component The component to wrap with authentication context
 * @returns A new component with authentication context
 */
export const withAuth = <P extends object>(
  Component: React.ComponentType<P>
) => {
  const AuthenticatedComponent = (props: P) => {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading && !user) {
        router.push(`/login?redirect=${encodeURIComponent(router.asPath)}`);
      }
    }, [user, loading, router]);

    if (loading || !user) {
      return <div>Loading...</div>; // Or a loading spinner
    }

    return <Component {...(props as P)} />;
  };

  return AuthenticatedComponent;
};

/**
 * A higher-order component that redirects to the dashboard if the user is already authenticated.
 * @param Component The component to wrap with guest protection
 * @returns A new component with guest protection
 */
export const withGuest = <P extends object>(
  Component: React.ComponentType<P>
) => {
  const GuestComponent = (props: P) => {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading && user) {
        const redirectTo = router.query.redirect || '/dashboard';
        router.push(redirectTo as string);
      }
    }, [user, loading, router]);

    if (loading || user) {
      return <div>Loading...</div>; // Or a loading spinner
    }

    return <Component {...(props as P)} />;
  };

  return GuestComponent;
};
