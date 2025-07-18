"use client";
// src/app/providers.tsx
import React, { useRef } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SessionProvider } from "next-auth/react";
import { AuthProvider } from "@/contexts/AuthContext";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  // Create QueryClient only on the client
  const queryClientRef = useRef<QueryClient>(undefined);
  if (!queryClientRef.current) {
    queryClientRef.current = new QueryClient();
  }

  return (
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <SessionProvider>
        <QueryClientProvider client={queryClientRef.current}>
          <AuthProvider>
            {children}
          </AuthProvider>
        </QueryClientProvider>
      </SessionProvider>
    </TooltipProvider>
  );
}
