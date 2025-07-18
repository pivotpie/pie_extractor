'use client';

import { useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { useState, useEffect } from 'react';
import Link from 'next/link';

interface NetworkEntry {
  name: string;
  duration: number;
  transferSize: number;
  startTime: number;
  initiatorType?: string;
}

interface ErrorDetails {
  error: string;
  errorCode: string;
  errorDescription: string;
  timestamp: string;
}

export default function AuthError() {
  const searchParams = useSearchParams();
  const [showDetails, setShowDetails] = useState(false);
  const [copied, setCopied] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [networkLogs, setNetworkLogs] = useState<NetworkEntry[]>([]);

  const error = searchParams?.get('error') ?? '';
  const errorDescription = searchParams?.get('error_description') ?? '';
  const errorCode = searchParams?.get('code') ?? '';
  const timestamp = new Date().toISOString();

  const errorDetails: ErrorDetails = {
    error,
    errorCode,
    errorDescription,
    timestamp
  };

  useEffect(() => {
    // Only run in browser
    if (typeof window === 'undefined') return;

    // Capture console errors
    const originalError = console.error;
    console.error = (...args: any[]) => {
      const logEntry = `[${new Date().toISOString()}] ${args.join(' ')}`;
      setLogs(prev => [...prev, logEntry].slice(-50));
      return originalError.apply(console, args);
    };

    // Capture network requests
    try {
      const entries = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      const authRequests = entries
        .filter(e => e.name.includes('/auth/') || e.name.includes('/api/'))
        .map(e => ({
          name: e.name,
          duration: e.duration,
          transferSize: e.transferSize,
          startTime: e.startTime,
          initiatorType: e.initiatorType
        }));
      
      setNetworkLogs(authRequests);
    } catch (e) {
      console.error('Failed to capture network requests:', e);
    }

    return () => {
      console.error = originalError;
    };
  }, []);

  const copyToClipboard = () => {
    const text = `Error: ${error}
Code: ${errorCode || 'N/A'}
Description: ${errorDescription || 'N/A'}
Timestamp: ${timestamp}

--- Logs ---
${logs.join('\n')}

--- Network Requests ---
${networkLogs.map((entry) => `${entry.name} (${entry.duration.toFixed(1)}ms)`).join('\n')}`;

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md bg-card p-8 rounded-lg shadow-lg border border-border">
        <h1 className="text-2xl font-bold text-foreground mb-4">Authentication Error</h1>
        <p className="text-muted-foreground mb-6">
          {errorDescription || 'An unexpected error occurred during authentication.'}
        </p>

        <div className="space-y-4">
          <Link href="/login" className="block">
            <Button className="w-full">Return to Login</Button>
          </Link>

          <Button
            variant="outline"
            className="w-full"
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? 'Hide Details' : 'Show Details'}
          </Button>

          {showDetails && (
            <div className="space-y-4">
              <div className="p-4 bg-muted/50 rounded-md">
                <h3 className="font-medium mb-2">Error Details</h3>
                <pre className="text-xs text-muted-foreground overflow-auto">
                  {JSON.stringify({ error, errorCode, errorDescription, timestamp }, null, 2)}
                </pre>
              </div>

              {logs.length > 0 && (
                <div className="bg-muted/50 p-4 rounded-md">
                  <h3 className="font-medium mb-2">Recent Logs</h3>
                  <div className="bg-background p-2 rounded text-xs font-mono overflow-auto max-h-32">
                    {logs.map((log, i) => (
                      <div key={i} className="break-all">
                        {log}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {networkLogs.length > 0 && (
                <div className="bg-muted/50 p-4 rounded-md">
                  <h3 className="font-medium mb-2">Network Requests</h3>
                  <div className="space-y-1 text-xs">
                    {networkLogs.map((entry, i) => (
                      <div key={i} className="flex justify-between">
                        <span className="truncate max-w-[70%]">{entry.name}</span>
                        <span className="text-muted-foreground">
                          {entry.duration.toFixed(1)}ms
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="text-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={copyToClipboard}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              {copied ? 'Copied to clipboard!' : 'Copy Error Details'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
