import { ReactNode } from 'react';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';

interface AuthGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
}

const AuthGuard = ({ children, fallback = null }: AuthGuardProps) => {
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        {fallback || <RedirectToSignIn />}
      </SignedOut>
    </>
  );
};

export default AuthGuard;