import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

export default function OAuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    // NextAuth.js handles the callback, so just redirect to home (or dashboard)
    navigate('/', { replace: true });
  }, [navigate]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin" />
          <p className="text-gray-600">Completing authentication...</p>
        </div>
      </div>
    </div>
  );
}

