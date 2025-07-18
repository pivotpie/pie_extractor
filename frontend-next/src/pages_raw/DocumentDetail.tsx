import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  ArrowLeft, 
  Brain, 
  Download, 
  Edit, 
  Save, 
  MessageSquare,
  FileText,
  CheckCircle,
  AlertCircle,
  Clock,
  Eye,
  Copy,
  ExternalLink,
  Search,
  Sparkles,
  ChevronDown,
  ChevronUp,
  BarChart3,
  Scale,
  Receipt,
  Building2,
  Trash2,
  Plus,
  User,
  Settings,
  LogOut
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AppHeader from "@/components/AppHeader";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";

interface ExtractedData {
  [key: string]: string | number | any;
}

interface DocumentData {
  id: string;
  name: string;
  type: string;
  status: 'processing' | 'completed' | 'failed' | 'pending';
  uploadDate: string;
  pages: number;
  confidence: number;
  size: string;
  extractedData: ExtractedData;
  aiSummary: string;
  insights: string[];
  preview?: string;
}

interface DocumentBunch {
  id: string;
  name: string;
  documents: DocumentData[];
}

const DocumentDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [document, setDocument] = useState<DocumentData | null>(null);
  const [documentBunch, setDocumentBunch] = useState<DocumentBunch | null>(null);
  const [activeDocumentId, setActiveDocumentId] = useState<string>("");
  const [isEditing, setIsEditing] = useState(false);
  const [chatQuery, setChatQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<Array<{type: 'user' | 'ai', message: string}>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [rightPanelExpanded, setRightPanelExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState("fields");

  useEffect(() => {
    // Simulate loading document bunch data
    const mockDocumentBunch: DocumentBunch = {
      id: "bunch-1",
      name: "Q1 2024 Invoices",
      documents: [
        {
          id: id || "1",
          name: "Invoice_2024_001.pdf",
          type: "invoice",
          status: "completed",
          uploadDate: "2024-01-15T10:30:00Z",
          pages: 2,
          confidence: 96,
          size: "1.2 MB",
          preview: "/placeholder.svg",
          extractedData: {
            vendorName: "TechSupply Corp",
            vendorAddress: "123 Business Ave, Tech City, TC 12345",
            invoiceNumber: "INV-2024-001",
            invoiceDate: "2024-01-10",
            dueDate: "2024-02-09",
            totalAmount: 1250.00,
            subtotal: 1100.00,
            tax: 150.00,
            currency: "USD",
            paymentTerms: "Net 30",
            lineItems: [
              { description: "Software License - Annual", quantity: 1, unitPrice: 800.00, total: 800.00 },
              { description: "Professional Services", quantity: 6, unitPrice: 50.00, total: 300.00 }
            ]
          },
          aiSummary: "This is an invoice from TechSupply Corp for software licenses and professional services totaling $1,250. The invoice is dated January 10, 2024, with payment due by February 9, 2024 (Net 30 terms). The invoice includes a software license fee and 6 hours of professional services.",
          insights: [
            "Payment due in 15 days from today",
            "Regular vendor - 12th invoice this year",
            "Amount is 15% higher than previous invoice",
            "Professional services hours increased from usual 4 to 6"
          ]
        },
        {
          id: "2",
          name: "Invoice_2024_002.pdf",
          type: "invoice",
          status: "completed",
          uploadDate: "2024-01-20T14:20:00Z",
          pages: 1,
          confidence: 94,
          size: "0.8 MB",
          preview: "/placeholder.svg",
          extractedData: {
            vendorName: "DataFlow Systems",
            invoiceNumber: "DFS-2024-045",
            totalAmount: 875.00
          },
          aiSummary: "Invoice from DataFlow Systems for cloud services.",
          insights: ["Regular monthly service charge", "On-time payment history"]
        },
        {
          id: "3",
          name: "Bank_Statement_Jan2024.pdf",
          type: "bank-statement",
          status: "completed",
          uploadDate: "2024-02-01T09:15:00Z",
          pages: 5,
          confidence: 98,
          size: "2.1 MB",
          preview: "/placeholder.svg",
          extractedData: {
            accountNumber: "****1234",
            statementPeriod: "January 2024",
            openingBalance: 15750.00,
            closingBalance: 18650.00
          },
          aiSummary: "Bank statement showing positive cash flow with net increase of $2,900.",
          insights: ["Healthy cash flow", "3 large deposits", "Regular operational expenses"]
        }
      ]
    };
    setDocumentBunch(mockDocumentBunch);
    setActiveDocumentId(id || "1");
    const activeDoc = mockDocumentBunch.documents.find(doc => doc.id === (id || "1"));
    setDocument(activeDoc || null);
  }, [id]);

  const handleSave = () => {
    setIsEditing(false);
    toast({
      title: "Document Updated",
      description: "Your changes have been saved successfully.",
    });
  };

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatQuery.trim()) return;

    setIsLoading(true);
    setChatHistory(prev => [...prev, { type: 'user', message: chatQuery }]);
    
    // Simulate AI response
    setTimeout(() => {
      const responses = [
        "Based on the document analysis, the vendor TechSupply Corp has been a consistent partner with regular monthly invoices.",
        "The payment terms are Net 30, which means payment is due within 30 days of the invoice date (February 9, 2024).",
        "This invoice shows an increase in professional services hours compared to previous invoices, suggesting expanded project scope.",
        "The software license fee represents the largest component at $800 of the total $1,250 invoice amount."
      ];
      
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      setChatHistory(prev => [...prev, { type: 'ai', message: randomResponse }]);
      setChatQuery("");
      setIsLoading(false);
    }, 1000);
  };

  if (!document || !documentBunch) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Clock className="h-8 w-8 text-muted-foreground mx-auto mb-4 animate-spin" />
          <p className="text-muted-foreground">Loading document...</p>
        </div>
      </div>
    );
  }

  const getStatusIcon = (status: DocumentData['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-success" />;
      case 'processing':
        return <Clock className="h-5 w-5 text-primary animate-spin" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-destructive" />;
      default:
        return <Clock className="h-5 w-5 text-warning" />;
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied to clipboard",
      description: "Text has been copied to your clipboard.",
    });
  };

  const handleDocumentChange = (docId: string) => {
    setActiveDocumentId(docId);
    const selectedDoc = documentBunch?.documents.find(doc => doc.id === docId);
    setDocument(selectedDoc || null);
    navigate(`/documents/${docId}`);
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // Implement search logic
  };

  const handleAISearch = (query: string) => {
    setSearchQuery(query);
    setChatQuery(query);
    // Implement AI search logic
  };

  const getDocumentTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'invoice':
      case 'order':
      case 'quotation':
      case 'receipt':
        return <Receipt className="h-4 w-4" />;
      case 'bank-statement':
      case 'financial-statement':
        return <BarChart3 className="h-4 w-4" />;
      case 'legal-document':
      case 'agreement':
        return <Scale className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const isFinancialType = (type: string) => {
    return ['invoice', 'order', 'quotation', 'receipt'].includes(type.toLowerCase());
  };

  const isBankingType = (type: string) => {
    return ['bank-statement', 'financial-statement'].includes(type.toLowerCase());
  };

  const isLegalType = (type: string) => {
    return ['legal-document', 'agreement'].includes(type.toLowerCase());
  };

  const shouldShowSummaryTab = (type: string) => {
    return isFinancialType(type) || isBankingType(type);
  };

  const handleAskAI = () => {
    // Focus on search bar and set prompt
    const searchInput = window.document.getElementById("header-search") as HTMLInputElement;
    if (searchInput) {
      searchInput.focus();
      setSearchQuery("Ask AI about this Document/s");
      handleAISearch("Ask AI about this Document/s");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header with Search - Match ListView height */}
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 max-w-none">
          <AppHeader
            title={documentBunch.name}
            subtitle={`${documentBunch.documents.length} documents`}
            showBackButton
            backTo="/documents"
            showSearch
            onSearch={handleSearch}
            onAISearch={handleAISearch}
            pageType="documentDetail"
            rightContent={
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <User className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="bg-background border shadow-lg z-50">
                  <DropdownMenuItem>
                    <Settings className="h-4 w-4 mr-2" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => {
                    localStorage.removeItem("pie_extractor_auth");
                    navigate("/login");
                  }}>
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            }
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex h-[calc(100vh-136px)]">
        
        {/* Left Column - 70% - Document Preview Tabs */}
        <div className="w-[70%] border-r bg-card/20">
          <div className="h-full flex flex-col">
            
            {/* Document Tabs */}
            <div className="border-b bg-background/50">
              <div className="flex items-center overflow-x-auto">
                {documentBunch.documents.map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() => handleDocumentChange(doc.id)}
                    className={`
                      flex items-center gap-2 px-4 py-3 border-b-2 whitespace-nowrap text-sm font-medium transition-colors
                      ${activeDocumentId === doc.id
                        ? 'border-primary text-primary bg-primary/5'
                        : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50'
                      }
                    `}
                  >
                    {getDocumentTypeIcon(doc.type)}
                    <span className="truncate max-w-[150px]">{doc.name}</span>
                    {getStatusIcon(doc.status)}
                  </button>
                ))}
              </div>
            </div>

            {/* Document Preview - Full width */}
            <div className="flex-1 p-6 overflow-auto">
              <div className="w-full h-full">
                <div className="bg-card border rounded-lg shadow-sm h-full min-h-[600px] flex items-center justify-center">
                  <div className="text-center text-muted-foreground">
                    <FileText className="h-16 w-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium">Document Preview</p>
                    <p className="text-sm">{document.name}</p>
                    <p className="text-xs mt-1">{document.pages} pages • {document.size}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - 30% - Dynamic Content */}
        <div className="w-[30%] bg-background">
          <div className="h-full flex flex-col">
            
            {/* Panel Header */}
            <div className="border-b p-4 bg-card/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getDocumentTypeIcon(document.type)}
                  <h3 className="font-semibold capitalize">{document.type} Analysis</h3>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setRightPanelExpanded(!rightPanelExpanded)}
                >
                  {rightPanelExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            {/* Dynamic Content */}
            {rightPanelExpanded && (
              <div className="flex-1 overflow-auto">
                
                {/* Financial Documents (Invoice/Orders/Quotation/Receipt) */}
                {isFinancialType(document.type) && (
                  <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
                    <TabsList className="grid w-full grid-cols-2 m-4 mb-0">
                      <TabsTrigger value="fields">Fields & Tables</TabsTrigger>
                      <TabsTrigger value="summary">Summary</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="fields" className="flex-1 p-4 mt-0">
                      <div className="space-y-4">
                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm">Editable Fields</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <div className="space-y-3">
                              <div>
                                <Label htmlFor="vendorName">Vendor Name</Label>
                                <Input 
                                  id="vendorName"
                                  value={document.extractedData.vendorName || ''}
                                  onChange={(e) => setDocument(prev => prev ? {
                                    ...prev,
                                    extractedData: { ...prev.extractedData, vendorName: e.target.value }
                                  } : null)}
                                />
                              </div>
                              <div>
                                <Label htmlFor="vendorAddress">Vendor Address</Label>
                                <Textarea
                                  id="vendorAddress"
                                  value={document.extractedData.vendorAddress || ''}
                                  onChange={(e) => setDocument(prev => prev ? {
                                    ...prev,
                                    extractedData: { ...prev.extractedData, vendorAddress: e.target.value }
                                  } : null)}
                                  className="min-h-[60px]"
                                />
                              </div>
                              <div>
                                <Label htmlFor="invoiceNumber">Invoice Number</Label>
                                <Input
                                  id="invoiceNumber"
                                  value={document.extractedData.invoiceNumber || ''}
                                  onChange={(e) => setDocument(prev => prev ? {
                                    ...prev,
                                    extractedData: { ...prev.extractedData, invoiceNumber: e.target.value }
                                  } : null)}
                                />
                              </div>
                              <div>
                                <Label htmlFor="totalAmount">Total Amount</Label>
                                <Input
                                  id="totalAmount"
                                  type="number"
                                  value={document.extractedData.totalAmount || ''}
                                  onChange={(e) => setDocument(prev => prev ? {
                                    ...prev,
                                    extractedData: { ...prev.extractedData, totalAmount: parseFloat(e.target.value) }
                                  } : null)}
                                />
                              </div>
                              <div>
                                <Label htmlFor="invoiceDate">Invoice Date</Label>
                                <Input
                                  id="invoiceDate"
                                  type="date"
                                  value={document.extractedData.invoiceDate || ''}
                                  onChange={(e) => setDocument(prev => prev ? {
                                    ...prev,
                                    extractedData: { ...prev.extractedData, invoiceDate: e.target.value }
                                  } : null)}
                                />
                              </div>
                              <div>
                                <Label htmlFor="dueDate">Due Date</Label>
                                <Input
                                  id="dueDate"
                                  type="date"
                                  value={document.extractedData.dueDate || ''}
                                  onChange={(e) => setDocument(prev => prev ? {
                                    ...prev,
                                    extractedData: { ...prev.extractedData, dueDate: e.target.value }
                                  } : null)}
                                />
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="summary" className="flex-1 p-4 mt-0">
                      <div className="space-y-4">
                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center justify-between">
                              AI Summary
                              <Button 
                                variant="outline" 
                                size="sm"
                                onClick={handleAskAI}
                                className="flex items-center gap-2"
                              >
                                <Sparkles className="h-3 w-3" />
                                Ask AI about this Document/s
                              </Button>
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <p className="text-sm leading-relaxed">{document.aiSummary}</p>
                          </CardContent>
                        </Card>
                        
                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm">Insights</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-2">
                            {document.insights.map((insight, index) => (
                              <div key={index} className="flex items-start gap-2 text-sm">
                                <Sparkles className="h-3 w-3 text-accent mt-0.5 flex-shrink-0" />
                                <p className="leading-relaxed">{insight}</p>
                              </div>
                            ))}
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                  </Tabs>
                )}

                {/* Banking/Financial Statements */}
                {isBankingType(document.type) && (
                  <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
                    <TabsList className="grid w-full grid-cols-2 m-4 mb-0">
                      <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
                      <TabsTrigger value="summary">Summary</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="dashboard" className="flex-1 p-4 mt-0">
                      <div className="space-y-4">
                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <BarChart3 className="h-4 w-4" />
                              Financial Overview
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-3">
                            <div className="grid grid-cols-1 gap-3">
                              <div className="bg-muted/50 p-3 rounded-lg">
                                <p className="text-xs text-muted-foreground">Opening Balance</p>
                                <p className="text-lg font-bold">${document.extractedData.openingBalance?.toFixed(2)}</p>
                              </div>
                              <div className="bg-success/10 p-3 rounded-lg">
                                <p className="text-xs text-muted-foreground">Closing Balance</p>
                                <p className="text-lg font-bold text-success">${document.extractedData.closingBalance?.toFixed(2)}</p>
                              </div>
                              <div className="bg-primary/10 p-3 rounded-lg">
                                <p className="text-xs text-muted-foreground">Net Change</p>
                                <p className="text-lg font-bold text-primary">
                                  +${(document.extractedData.closingBalance - document.extractedData.openingBalance).toFixed(2)}
                                </p>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="summary" className="flex-1 p-4 mt-0">
                      <div className="space-y-4">
                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm">AI Summary</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <p className="text-sm leading-relaxed">{document.aiSummary}</p>
                          </CardContent>
                        </Card>
                        
                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-sm">Insights</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-2">
                            {document.insights.map((insight, index) => (
                              <div key={index} className="flex items-start gap-2 text-sm">
                                <Sparkles className="h-3 w-3 text-accent mt-0.5 flex-shrink-0" />
                                <p className="leading-relaxed">{insight}</p>
                              </div>
                            ))}
                          </CardContent>
                        </Card>
                      </div>
                    </TabsContent>
                  </Tabs>
                )}

                {/* Legal Documents */}
                {isLegalType(document.type) && (
                  <div className="p-4 space-y-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <Scale className="h-4 w-4" />
                          Document Summary
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm leading-relaxed">{document.aiSummary}</p>
                      </CardContent>
                    </Card>
                    
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Key Insights</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {document.insights.map((insight, index) => (
                          <div key={index} className="flex items-start gap-2 text-sm">
                            <Sparkles className="h-3 w-3 text-accent mt-0.5 flex-shrink-0" />
                            <p className="leading-relaxed">{insight}</p>
                          </div>
                        ))}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <MessageSquare className="h-4 w-4" />
                          RAG Chat
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="space-y-2 max-h-40 overflow-y-auto">
                          {chatHistory.map((message, index) => (
                            <div key={index} className={`text-xs p-2 rounded ${
                              message.type === 'user' ? 'bg-primary text-primary-foreground ml-4' : 'bg-muted mr-4'
                            }`}>
                              {message.message}
                            </div>
                          ))}
                        </div>
                        <form onSubmit={handleChatSubmit} className="space-y-2">
                          <Textarea
                            placeholder="Ask about this legal document..."
                            value={chatQuery}
                            onChange={(e) => setChatQuery(e.target.value)}
                            className="min-h-[60px] resize-none text-sm"
                          />
                          <Button 
                            type="submit" 
                            size="sm"
                            className="w-full"
                            disabled={isLoading || !chatQuery.trim()}
                          >
                            {isLoading ? "AI thinking..." : "Ask AI"}
                          </Button>
                        </form>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {/* Other Document Types */}
                {!isFinancialType(document.type) && !isBankingType(document.type) && !isLegalType(document.type) && (
                  <div className="p-4 space-y-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Document Summary</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm leading-relaxed">{document.aiSummary}</p>
                      </CardContent>
                    </Card>
                    
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Insights</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {document.insights.map((insight, index) => (
                          <div key={index} className="flex items-start gap-2 text-sm">
                            <Sparkles className="h-3 w-3 text-accent mt-0.5 flex-shrink-0" />
                            <p className="leading-relaxed">{insight}</p>
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Line Items Section - Full Width at Bottom */}
      {document.extractedData.lineItems && isFinancialType(document.type) && (
        <section className="border-t bg-background">
          <div className="container mx-auto px-4 py-6 max-w-none">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Line Items</CardTitle>
                <CardDescription>
                  Edit individual line items for this {document.type}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-3 font-medium">Description</th>
                        <th className="text-right p-3 font-medium">Quantity</th>
                        <th className="text-right p-3 font-medium">Unit Price</th>
                        <th className="text-right p-3 font-medium">Total</th>
                        <th className="text-center p-3 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {document.extractedData.lineItems.map((item: any, index: number) => (
                        <tr key={index} className="border-b hover:bg-muted/25">
                          <td className="p-3">
                            <Input
                              value={item.description}
                              onChange={(e) => {
                                const newLineItems = [...document.extractedData.lineItems];
                                newLineItems[index] = { ...item, description: e.target.value };
                                setDocument(prev => prev ? {
                                  ...prev,
                                  extractedData: { ...prev.extractedData, lineItems: newLineItems }
                                } : null);
                              }}
                              className="border-none bg-transparent"
                            />
                          </td>
                          <td className="p-3">
                            <Input
                              type="number"
                              value={item.quantity}
                              onChange={(e) => {
                                const newLineItems = [...document.extractedData.lineItems];
                                newLineItems[index] = { ...item, quantity: parseFloat(e.target.value) };
                                setDocument(prev => prev ? {
                                  ...prev,
                                  extractedData: { ...prev.extractedData, lineItems: newLineItems }
                                } : null);
                              }}
                              className="text-right border-none bg-transparent"
                            />
                          </td>
                          <td className="p-3">
                            <Input
                              type="number"
                              step="0.01"
                              value={item.unitPrice}
                              onChange={(e) => {
                                const newLineItems = [...document.extractedData.lineItems];
                                newLineItems[index] = { ...item, unitPrice: parseFloat(e.target.value) };
                                setDocument(prev => prev ? {
                                  ...prev,
                                  extractedData: { ...prev.extractedData, lineItems: newLineItems }
                                } : null);
                              }}
                              className="text-right border-none bg-transparent"
                            />
                          </td>
                          <td className="p-3 text-right font-medium">
                            ${(item.quantity * item.unitPrice).toFixed(2)}
                          </td>
                          <td className="p-3 text-center">
                            <Button 
                              variant="ghost" 
                              size="sm"
                              onClick={() => {
                                const newLineItems = document.extractedData.lineItems.filter((_: any, i: number) => i !== index);
                                setDocument(prev => prev ? {
                                  ...prev,
                                  extractedData: { ...prev.extractedData, lineItems: newLineItems }
                                } : null);
                              }}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex justify-between items-center mt-4 pt-4 border-t">
                  <Button 
                    variant="outline"
                    onClick={() => {
                      const newItem = { description: "", quantity: 1, unitPrice: 0, total: 0 };
                      const newLineItems = [...document.extractedData.lineItems, newItem];
                      setDocument(prev => prev ? {
                        ...prev,
                        extractedData: { ...prev.extractedData, lineItems: newLineItems }
                      } : null);
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Line Item
                  </Button>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Total: </p>
                    <p className="text-lg font-bold">
                      ${document.extractedData.lineItems.reduce((sum: number, item: any) => sum + (item.quantity * item.unitPrice), 0).toFixed(2)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      )}
    </div>
  );
};

export default DocumentDetail;