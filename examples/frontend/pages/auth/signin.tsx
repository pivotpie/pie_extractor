import { getProviders, signIn, useSession } from 'next-auth/react';
import { GetServerSideProps } from 'next';
import { ClientSafeProvider } from 'next-auth/react/types';
import { useRouter } from 'next/router';
import { useEffect } from 'react';
import Head from 'next/head';
import { Box, Button, Container, Typography, Divider, CircularProgress } from '@mui/material';
import GoogleIcon from '@mui/icons-material/Google';
import GitHubIcon from '@mui/icons-material/GitHub';

// Helper function to get provider icon
const getProviderIcon = (providerId: string) => {
  switch (providerId.toLowerCase()) {
    case 'google':
      return <GoogleIcon />;
    case 'github':
      return <GitHubIcon />;
    default:
      return null;
  }
};

interface SignInProps {
  providers: Record<string, ClientSafeProvider>;
}

export default function SignIn({ providers }: SignInProps) {
  const { data: session, status } = useSession();
  const router = useRouter();
  const { error } = router.query;
  
  // Keep all hooks at the top level
  useEffect(() => {
    if (status === 'authenticated') {
      router.push('/dashboard');
    }
  }, [session, status, router]);

  // Show loading state
  if (status === 'loading') {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }
  
  // Handle case when no providers are available
  if (Object.keys(providers).length === 0) {
    return (
      <Container component="main" maxWidth="xs">
        <Head>
          <title>Sign In - Document Processor</title>
        </Head>
        <Box
          sx={{
            marginTop: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Typography component="h1" variant="h4" sx={{ mb: 4 }}>
            Document Processor
          </Typography>
          <Box sx={{ 
            p: 3, 
            bgcolor: 'warning.light',
            borderRadius: 1,
            textAlign: 'center'
          }}>
            <Typography color="error">
              No authentication providers are configured.
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Please check your server configuration and environment variables.
            </Typography>
          </Box>
        </Box>
      </Container>
    );
  }

  return (
    <Container component="main" maxWidth="xs">
      <Head>
        <title>Sign In - Document Processor</title>
      </Head>
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Typography component="h1" variant="h4" sx={{ mb: 4 }}>
          Document Processor
        </Typography>
        
        {error && (
          <Box 
            sx={{
              bgcolor: 'error.light',
              color: 'white',
              p: 2,
              borderRadius: 1,
              mb: 3,
              width: '100%',
              textAlign: 'center'
            }}
          >
            {error === 'AccessDenied' 
              ? 'Access denied. Please try again with a different account.' 
              : 'An error occurred during sign in. Please try again.'}
          </Box>
        )}
        
        <Box
          sx={{
            width: '100%',
            bgcolor: 'background.paper',
            p: 4,
            borderRadius: 2,
            boxShadow: 1,
          }}
        >
          <Typography component="h2" variant="h6" gutterBottom>
            Sign in to your account
          </Typography>
          
          <Divider sx={{ my: 3 }} />
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {Object.values(providers).map((provider) => (
              <Button
                key={provider.id}
                variant="outlined"
                fullWidth
                onClick={() => signIn(provider.id, { callbackUrl: '/dashboard' })}
                startIcon={getProviderIcon(provider.id)}
                sx={{
                  py: 1.5,
                  textTransform: 'none',
                  fontSize: '1rem',
                }}
              >
                Continue with {provider.name}
              </Button>
            ))}
          </Box>
          
          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              By continuing, you agree to our Terms of Service and Privacy Policy
            </Typography>
          </Box>
        </Box>
      </Box>
    </Container>
  );
}

export const getServerSideProps: GetServerSideProps = async (context) => {
  try {
    const providers = await getProviders();
    console.log('Available auth providers:', Object.keys(providers || {}));
    return {
      props: { 
        providers: providers || {}
      },
    };
  } catch (error) {
    console.error('Error fetching auth providers:', error);
    return {
      props: { providers: {} },
    };
  }
};
