import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Search, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import AIChatModal from "./AIChatModal";

interface AppHeaderProps {
  title?: string;
  subtitle?: string | React.ReactNode;
  showBackButton?: boolean;
  backTo?: string;
  rightContent?: React.ReactNode;
  className?: string;
  logoSize?: "small" | "medium" | "large";
  showSearch?: boolean;
  onSearch?: (query: string) => void;
  onAISearch?: (query: string) => void;
  searchPlaceholder?: string;
  pageType?: "documentDetail" | "listView";
}

const AppHeader: React.FC<AppHeaderProps> = ({
  title = "Pie-Extractor",
  subtitle = "Data Extraction Platform",
  showBackButton = false,
  backTo = "/",
  rightContent,
  className = "",
  logoSize = "medium",
  showSearch = false,
  onSearch,
  onAISearch,
  searchPlaceholder,
  pageType = "listView"
}) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [showAIModal, setShowAIModal] = useState(false);
  const [searchBarRect, setSearchBarRect] = useState<DOMRect | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Generate dynamic placeholder text based on pageType
  const dynamicPlaceholder = searchPlaceholder || 
    (pageType === "documentDetail" 
      ? "Type to Search, Press / to ask AI or ? to ask about this Document"
      : "Type to Search, Press / to ask AI");

  const handleSearchKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    // Only allow "?" shortcut on document detail pages
    const allowQuestionMark = pageType === "documentDetail";
    const isValidShortcut = event.key === "/" || (event.key === "?" && allowQuestionMark);
    
    if (isValidShortcut && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      console.log("Key pressed in search bar:", event.key);
      
      // Get search bar position for smooth transition
      if (searchInputRef.current) {
        const rect = searchInputRef.current.getBoundingClientRect();
        console.log("Search bar rect:", rect);
        setSearchBarRect(rect);
      }
      
      console.log("Opening AI modal");
      setShowAIModal(true);
    }
  };

  const handleBackClick = () => {
    navigate(backTo);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // For regular search (non-AI), just call onSearch
      if (onSearch) {
        onSearch(searchQuery);
      }
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    
    // Trigger search as user types for regular search
    if (onSearch) {
      onSearch(value);
    }
  };


  const handleModalClose = () => {
    setShowAIModal(false);
    setSearchBarRect(null);
  };

  const logoSizeClasses = {
    small: "w-8 h-8 p-1.5",
    medium: "w-12 h-12 p-2.5", 
    large: "w-16 h-16 p-3"
  };

  const titleSizeClasses = {
    small: "text-lg",
    medium: "text-xl",
    large: "text-2xl"
  };

  const subtitleSizeClasses = {
    small: "text-xs",
    medium: "text-sm",
    large: "text-sm"
  };

  return (
    <div className={`flex items-center gap-6 ${className}`}>
      {/* Left section - Logo and title */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {showBackButton && (
          <Button variant="ghost" size="icon" onClick={handleBackClick}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
        )}
        <div className={`rounded-lg border-2 border-primary/20 bg-gradient-to-br from-background to-muted shadow-lg ${logoSizeClasses[logoSize]}`}>
          <img 
            src="/lovable-uploads/d1138bec-ecad-4dd7-8175-8c954345d283.png" 
            alt="Pie-Extractor Logo" 
            className="w-full h-full object-contain"
          />
        </div>
        <div className="hidden sm:block">
          <h1 className={`font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent ${titleSizeClasses[logoSize]}`}>
            {title}
          </h1>
          {subtitle && (
            <div className={`text-muted-foreground ${subtitleSizeClasses[logoSize]}`}>
              {subtitle}
            </div>
          )}
        </div>
      </div>

      {/* Center section - Search bar */}
      {showSearch && (
        <div className="flex-1 max-w-2xl mx-auto">
          <form onSubmit={handleSearchSubmit} className="relative">
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-accent/20 rounded-full blur-sm opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div className="relative flex items-center">
                <Search className="absolute left-4 h-5 w-5 text-muted-foreground z-10" />
                <Sparkles className="absolute right-4 h-4 w-4 text-primary/60 z-10" />
                <Input
                  ref={searchInputRef}
                  id="header-search"
                  type="text"
                  placeholder={dynamicPlaceholder}
                  value={searchQuery}
                  onChange={handleSearchChange}
                  onKeyDown={handleSearchKeyDown}
                  className="pl-12 pr-12 py-3 h-12 rounded-full border-2 bg-background/50 backdrop-blur-sm transition-all focus:bg-background border-border hover:border-primary/50 focus:border-primary"
                />
              </div>
            </div>
          </form>
        </div>
      )}

      {/* Right section */}
      {rightContent && (
        <div className="flex items-center gap-3 flex-shrink-0">
          {rightContent}
        </div>
      )}

      {/* AI Chat Modal */}
      <AIChatModal
        isOpen={showAIModal}
        onClose={handleModalClose}
        initialQuery={searchQuery}
        onSearch={onSearch}
        onAISearch={onAISearch}
        searchBarRect={searchBarRect}
      />
    </div>
  );
};

export default AppHeader;