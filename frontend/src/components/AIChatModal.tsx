import React, { useState, useEffect, useRef } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Sparkles, Send, X, User, Bot } from "lucide-react";

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

interface AIChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialQuery?: string;
  onSearch?: (query: string) => void;
  onAISearch?: (query: string) => void;
  searchBarRect?: DOMRect | null;
}

const AIChatModal: React.FC<AIChatModalProps> = ({
  isOpen,
  onClose,
  initialQuery = "",
  onSearch,
  onAISearch,
  searchBarRect
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery(initialQuery);
      // Focus input after animation completes
      setTimeout(() => {
        inputRef.current?.focus();
      }, 300);
    }
  }, [isOpen, initialQuery]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: query,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Simulate AI response (replace with actual AI integration)
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `I understand you're asking: "${query}". This is a demo AI response. In a real implementation, this would connect to your AI service.`,
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1500);

    // Call the appropriate search function
    if (onAISearch) {
      onAISearch(query);
    }

    setQuery("");
  };

  const handleClose = () => {
    onClose();
    // Clear messages after modal closes
    setTimeout(() => {
      setMessages([]);
      setQuery("");
    }, 300);
  };

  console.log("AIChatModal render - isOpen:", isOpen, "searchBarRect:", searchBarRect);
  
  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent 
        className="max-w-4xl h-[80vh] p-0 overflow-hidden"
        style={{
          transformOrigin: searchBarRect 
            ? `${searchBarRect.left + searchBarRect.width / 2}px ${searchBarRect.top + searchBarRect.height / 2}px`
            : 'center center',
          animation: isOpen ? 'scale-in 0.3s cubic-bezier(0.16, 1, 0.3, 1)' : undefined
        }}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <DialogHeader className="p-6 pb-4 border-b bg-gradient-to-r from-primary/5 to-accent/5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-primary/10">
                  <Sparkles className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <DialogTitle className="text-xl font-semibold">AI Assistant</DialogTitle>
                  <DialogDescription className="text-sm text-muted-foreground">
                    Ask anything about your documents or search through them
                  </DialogDescription>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={handleClose}>
                <X className="h-5 w-5" />
              </Button>
            </div>
          </DialogHeader>

          {/* Messages Area */}
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-4">
              {messages.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <Bot className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p className="text-lg font-medium mb-2">Welcome to AI Assistant</p>
                  <p className="text-sm">Ask me anything about your documents or search through them. I'm here to help!</p>
                </div>
              )}
              
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 animate-fade-in ${message.isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {!message.isUser && (
                    <div className="p-2 rounded-full bg-primary/10 h-fit">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] p-4 rounded-2xl ${
                      message.isUser
                        ? 'bg-primary text-primary-foreground ml-12'
                        : 'bg-muted'
                    }`}
                  >
                    <p className="text-sm">{message.text}</p>
                    <span className="text-xs opacity-70 mt-2 block">
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  {message.isUser && (
                    <div className="p-2 rounded-full bg-primary/10 h-fit">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                  )}
                </div>
              ))}
              
              {isLoading && (
                <div className="flex gap-3 animate-fade-in">
                  <div className="p-2 rounded-full bg-primary/10 h-fit">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="bg-muted p-4 rounded-2xl max-w-[80%]">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input Area */}
          <div className="p-6 pt-4 border-t bg-background/50 backdrop-blur-sm">
            <form onSubmit={handleSubmit} className="flex gap-3">
              <div className="flex-1 relative group">
                <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-accent/20 rounded-full blur-sm opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative flex items-center">
                  <Search className="absolute left-4 h-5 w-5 text-muted-foreground z-10" />
                  <Input
                    ref={inputRef}
                    type="text"
                    placeholder="Ask me anything or search your documents..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="pl-12 pr-4 py-3 h-12 rounded-full border-2 bg-background/50 backdrop-blur-sm transition-all focus:bg-background border-border hover:border-primary/50 focus:border-primary"
                    disabled={isLoading}
                  />
                </div>
              </div>
              <Button 
                type="submit" 
                size="icon" 
                className="h-12 w-12 rounded-full"
                disabled={!query.trim() || isLoading}
              >
                <Send className="h-5 w-5" />
              </Button>
            </form>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default AIChatModal;