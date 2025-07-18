import React, { createContext, useContext, ReactNode } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';
import { User } from '@/lib/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string }) => Promise<void>;
  logout: () => void;
  loginWithOAuth: (provider: 'github' | 'google') => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { data: session, status } = useSession();
  const user = session?.user as User | null;
  const loading = status === 'loading';

  const login = async (credentials: { email: string; password: string }) => {
    // Use NextAuth credentials provider
    await signIn('credentials', {
      email: credentials.email,
      password: credentials.password,
      callbackUrl: '/',
      redirect: true,
    });
  };

  const register = async (data: { email: string; password: string; full_name: string }) => {
    // Register with backend, then auto-login
    await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8002'}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    await signIn('credentials', {
      email: data.email,
      password: data.password,
      callbackUrl: '/',
      redirect: true,
    });
  };


  const logout = () => {
    signOut({ callbackUrl: '/login' });
  };

  const loginWithOAuth = (provider: 'github' | 'google') => {
    signIn(provider, { callbackUrl: '/' });
  };


  const value = {
    user,
    loading,
    login,
    register,
    logout,
    loginWithOAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
