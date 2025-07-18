import { useEffect } from 'react';
import { signOut, useSession } from 'next-auth/react';
import { useRouter } from 'next/router';

export default function SignOut() {
  const router = useRouter();
  const { status } = useSession();

  useEffect(() => {
    // Only attempt to sign out if we have an active session
    if (status === 'authenticated') {
      signOut({ callbackUrl: '/auth/signin', redirect: false }).then(() => {
        // After signing out, redirect to sign-in page
        router.push('/auth/signin');
      });
    } else {
      // If no active session, redirect to sign-in page
      router.push('/auth/signin');
    }
  }, [status, router]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: '#f8f9fa',
      padding: '20px',
      textAlign: 'center',
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '2rem',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        maxWidth: '500px',
        width: '100%',
      }}>
        <h1 style={{
          color: '#333',
          marginBottom: '1.5rem',
        }}>Signing Out...</h1>
        
        <p style={{
          color: '#6c757d',
          marginBottom: '1.5rem',
        }}>
          You are being signed out and redirected to the sign-in page.
        </p>
        
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          marginTop: '2rem',
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #3498db',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }}></div>
        </div>
      </div>
      
      <style jsx global>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
