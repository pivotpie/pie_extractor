import React, { useState } from "react";
import AppHeader from "@/components/AppHeader";

const Index = () => {
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    console.log("Regular search:", query);
  };

  const handleAISearch = (query: string) => {
    console.log("AI search:", query);
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="p-6">
        <AppHeader 
          showSearch={true}
          onSearch={handleSearch}
          onAISearch={handleAISearch}
          pageType="documentDetail"
        />
      </div>
      <div className="flex items-center justify-center flex-1 mt-20">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">Welcome to Your Blank App</h1>
          <p className="text-xl text-muted-foreground mb-4">Start building your amazing project here!</p>
          <p className="text-sm text-muted-foreground">Press <kbd className="px-2 py-1 bg-muted rounded">/ </kbd> or <kbd className="px-2 py-1 bg-muted rounded">?</kbd> to test the AI modal animation</p>
        </div>
      </div>
    </div>
  );
};

export default Index;
