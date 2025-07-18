import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ReloadIcon } from '@radix-ui/react-icons';
import api from '@/lib/api';

const ConnectionTest = () => {
  const [testResult, setTestResult] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const testConnection = async () => {
    setIsLoading(true);
    setError('');
    setTestResult('');
    
    try {
      // Test basic API connection
      const response = await api.get('/api/test/frontend');
      setTestResult(JSON.stringify(response.data, null, 2));
      
      // Test health check endpoint
      const healthResponse = await api.get('/api/health');
      console.log('Health check response:', healthResponse.data);
      
      // Test auth endpoint
      const authResponse = await api.get('/api/v1/auth/me');
      console.log('Auth response:', authResponse.data);
      
    } catch (err: any) {
      console.error('Connection test failed:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to connect to the server';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>Backend Connection Test</CardTitle>
          <CardDescription>
            Test the connection between the frontend and backend
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Button 
              onClick={testConnection}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <ReloadIcon className="mr-2 h-4 w-4 animate-spin" />
                  Testing...
                </>
              ) : 'Test Connection'}
            </Button>
          </div>
          
          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-md">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}
          
          {testResult && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Test Results</h3>
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
                <pre className="text-sm overflow-auto">
                  {testResult}
                </pre>
              </div>
              <p className="text-sm text-green-600 dark:text-green-400">
                ✓ Successfully connected to the backend!
              </p>
            </div>
          )}
          
          <div className="text-sm text-gray-500 dark:text-gray-400">
            <p>This page tests the connection to the backend API.</p>
            <p>Base URL: {import.meta.env.VITE_API_URL || 'Not set'}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ConnectionTest;
