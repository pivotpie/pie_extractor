import { useSearchParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useState, useEffect } from 'react';

// In-memory console log buffer for this session
const LOG_BUFFER_SIZE = 50;
const logBuffer: string[] = [];
const origConsoleError = window.console.error;
const origConsoleWarn = window.console.warn;
const origConsoleLog = window.console.log;

// In-memory network log buffer
const NET_BUFFER_SIZE = 100;
const netBuffer: any[] = [];

function logInterceptor(type: string, ...args: any[]) {
  const entry = `[${type.toUpperCase()}] ${args.map(a => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' ')}`;
  logBuffer.push(entry);
  if (logBuffer.length > LOG_BUFFER_SIZE) logBuffer.shift();
}
window.console.error = (...args) => { logInterceptor('error', ...args); origConsoleError(...args); };
window.console.warn = (...args) => { logInterceptor('warn', ...args); origConsoleWarn(...args); };
window.console.log = (...args) => { logInterceptor('log', ...args); origConsoleLog(...args); };

// Monkey-patch fetch and XHR to capture status/type
const PATCHED_KEY = '__patchedNetworkCapture';
if (!(window as any)[PATCHED_KEY]) {
  // Patch fetch
  const origFetch = window.fetch;
  window.fetch = async (...args) => {
    const start = performance.now();
    let status = null;
    let responseType = null;
    let url = args[0];
    try {
      const resp = await origFetch(...args);
      status = resp.status;
      responseType = resp.type;
      netBuffer.push({
        url: (typeof url === 'string' ? url : (url && typeof url === 'object' && 'url' in url ? (url as any).url : String(url))),
        type: 'fetch',
        status,
        responseType,
        startTime: start,
        duration: performance.now() - start,
        transferSize: resp.headers.get('content-length') || 'N/A',
      });
      if (netBuffer.length > NET_BUFFER_SIZE) netBuffer.shift();
      return resp;
    } catch (e) {
      netBuffer.push({ url, type: 'fetch', status: 'error', responseType: 'error', startTime: start, duration: performance.now() - start, transferSize: 'N/A' });
      if (netBuffer.length > NET_BUFFER_SIZE) netBuffer.shift();
      throw e;
    }
  };
  // Patch XHR
  const origXHR = window.XMLHttpRequest;
  function PatchedXHR() {
    const xhr = new origXHR();
    let url = '';
    let start = 0;
    const origOpen = xhr.open;
    xhr.open = function(method, u, ...rest) {
      url = u;
      origOpen.call(xhr, method, u, ...rest);
    };
    xhr.addEventListener('loadstart', () => { start = performance.now(); });
    xhr.addEventListener('loadend', function() {
      netBuffer.push({
        url,
        type: 'xhr',
        status: xhr.status,
        responseType: xhr.responseType,
        startTime: start,
        duration: performance.now() - start,
        transferSize: xhr.response ? xhr.response.length : 'N/A',
      });
      if (netBuffer.length > NET_BUFFER_SIZE) netBuffer.shift();
    });
    return xhr;
  }
  window.XMLHttpRequest = PatchedXHR as any;
  (window as any)[PATCHED_KEY] = true;
}


export default function AuthError() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);
  const [networkDetails, setNetworkDetails] = useState<any[]>([]);
  const [allNetwork, setAllNetwork] = useState<any[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const message = searchParams.get('message') || 'An unknown authentication error occurred.';
  const errorCode = searchParams.get('code');
  const errorDescription = searchParams.get('error_description');
  const url = window.location.href;
  const timestamp = new Date().toLocaleString();

  useEffect(() => {
    setToken(localStorage.getItem('access_token'));
    setLogs([...logBuffer]);
    // Get recent network requests related to auth/oauth
    const entries = performance.getEntriesByType('resource')
      .filter((e: any) =>
        e.name.match(/auth|oauth|token|login|register/i)
      )
      .slice(-10)
      .map((e: any) => ({
        url: e.name,
        method: e.initiatorType,
        startTime: e.startTime,
        duration: e.duration,
        transferSize: e.transferSize
      }));
    setNetworkDetails(entries);
    // Get all network requests captured by monkey-patching
    setAllNetwork([...netBuffer]);
  }, []);

  const details = `Error: ${message}\nCode: ${errorCode || 'N/A'}\nDescription: ${errorDescription || 'N/A'}\nURL: ${url}\nTime: ${timestamp}\n\nAccess Token: ${token || 'N/A'}\n\nRecent Console Logs:\n${logs.join('\n')}\n\nRecent Network Requests (auth-related):\n${networkDetails.map(e => `${e.method} ${e.url} (${e.duration?.toFixed(1)}ms, ${e.transferSize}B)`).join('\n')}\n\nAll Network Requests:\n${allNetwork.map(e => `${e.type} ${e.url} [status: ${e.status}] [respType: ${e.responseType}] (${e.duration?.toFixed(1)}ms, ${e.transferSize}B)`).join('\n')}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(details);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-red-50">
      <div className="p-8 bg-white rounded-lg shadow-md border border-red-200 max-w-2xl w-full">
        <h2 className="text-2xl font-bold text-red-600 mb-4">Authentication Error</h2>
        <div className="mb-4 text-left">
          <p className="font-semibold">Message:</p>
          <p className="mb-2 text-gray-700 break-all">{message}</p>
          {errorCode && (
            <>
              <p className="font-semibold">Error Code:</p>
              <p className="mb-2 text-gray-700">{errorCode}</p>
            </>
          )}
          {errorDescription && (
            <>
              <p className="font-semibold">Description:</p>
              <p className="mb-2 text-gray-700 break-all">{errorDescription}</p>
            </>
          )}
          <p className="font-semibold">URL:</p>
          <p className="mb-2 text-gray-700 break-all">{url}</p>
          <p className="font-semibold">Timestamp:</p>
          <p className="mb-2 text-gray-700">{timestamp}</p>
          <p className="font-semibold">Access Token:</p>
          <p className="mb-2 text-gray-700 break-all">{token || 'N/A'}</p>
          <p className="font-semibold">Recent Console Logs:</p>
          <pre className="mb-2 bg-gray-100 rounded p-2 text-xs max-h-32 overflow-y-auto whitespace-pre-wrap">{logs.length ? logs.join('\n') : 'No logs captured.'}</pre>
          <p className="font-semibold">Recent Network Requests (auth-related):</p>
          <pre className="mb-2 bg-gray-100 rounded p-2 text-xs max-h-32 overflow-y-auto whitespace-pre-wrap">
            {networkDetails.length ? networkDetails.map((e, i) => `${e.method} ${e.url} (${e.duration?.toFixed(1)}ms, ${e.transferSize}B)`).join('\n') : 'No relevant network requests found.'}
          </pre>
          <p className="font-semibold">All Network Requests (last {allNetwork.length}):</p>
          <div className="mb-2 bg-gray-100 rounded p-2 text-xs max-h-48 overflow-y-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="text-left">Type</th>
                  <th className="text-left">Status</th>
                  <th className="text-left">RespType</th>
                  <th className="text-left">URL</th>
                  <th className="text-left">Duration (ms)</th>
                  <th className="text-left">Size</th>
                </tr>
              </thead>
              <tbody>
                {allNetwork.map((e, i) => (
                  <tr key={i} className="border-b border-gray-200">
                    <td>{e.type}</td>
                    <td>{e.status}</td>
                    <td>{e.responseType}</td>
                    <td className="break-all max-w-[200px]">{e.url}</td>
                    <td>{e.duration ? e.duration.toFixed(1) : 'N/A'}</td>
                    <td>{e.transferSize}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="flex flex-row gap-2 mb-4">
          <Button onClick={handleCopy} className="bg-gray-200 hover:bg-gray-300 text-gray-800">
            {copied ? 'Copied!' : 'Copy All Details'}
          </Button>
          <Button onClick={() => navigate('/login')} className="bg-red-600 hover:bg-red-700 text-white">
            Back to Login
          </Button>
        </div>
      </div>
    </div>
  );
}
