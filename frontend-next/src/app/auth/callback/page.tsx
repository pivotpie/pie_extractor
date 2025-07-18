import { useEffect } from 'react';
import { useRouter } from 'next/navigation';


export default function OAuthCallback() {
  const router = useRouter();
  useEffect(() => {
    // NextAuth.js handles the callback, so just redirect to home (or dashboard)
    router.replace('/');
  }, [router]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-600">Completing authentication...</p>
        </div>
      </div>
    </div>
  );
}


