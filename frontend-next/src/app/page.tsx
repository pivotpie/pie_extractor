"use client";
import React, { useState, useEffect } from "react";
import AppHeader from "@/components/AppHeader";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";

const Index = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/documents");
    } else if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    console.log("Regular search:", query);
  };

  const handleAISearch = (query: string) => {
    console.log("AI search:", query);
  };

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="p-8 bg-white rounded-lg shadow-md">
          <div className="flex flex-col items-center space-y-4">
            <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-600">Checking authentication...</p>
          </div>
        </div>
      </div>
    );
  }

  // Render nothing else; redirects are handled in useEffect
  return null;

  // Optionally, show nothing (or a fallback) while redirecting
  return null;
};

export default Index;
