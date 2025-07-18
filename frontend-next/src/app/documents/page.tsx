"use client";
import React, { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { 
  Plus, 
  Filter, 
  MoreVertical, 
  Eye, 
  Download, 
  Trash2,
  Clock,
  CheckCircle,
  AlertCircle,
  Brain,
  LogOut,
  User,
  Settings,
  Upload,
  FileText
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AppHeader from "@/components/AppHeader";
import DocumentUploadModal from "@/components/DocumentUploadModal";

interface Document {
  id: string;
  name: string;
  type: string;
  status: 'processing' | 'completed' | 'failed';
  uploadedAt: string;
  confidence?: number;
  size: string;
}

const DocumentList = () => {
  const { toast } = useToast();
  const { status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

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

  // Only render the document list for authenticated users
  if (status !== "authenticated") return null;

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"name" | "date" | "confidence">("date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  // Sample documents
  const [documents] = useState<Document[]>([
    {
      id: "1",
      name: "Invoice_Q4_2024.pdf",
      type: "invoice",
      status: "completed",
      uploadedAt: "2024-01-15T10:30:00Z",
      confidence: 96,
      size: "1.2 MB"
    },
    {
      id: "2",
      name: "Contract_ServiceAgreement.pdf",
      type: "contract",
      status: "processing",
      uploadedAt: "2024-01-15T09:45:00Z",
      size: "3.8 MB"
    },
    {
      id: "3",
      name: "Receipt_OfficeSupplies.jpg",
      type: "receipt",
      status: "completed",
      uploadedAt: "2024-01-14T16:22:00Z",
      confidence: 89,
      size: "856 KB"
    },
    {
      id: "4",
      name: "Tax_Form_W9_2024.pdf",
      type: "tax-form",
      status: "failed",
      uploadedAt: "2024-01-14T14:10:00Z",
      size: "924 KB"
    },
    {
      id: "5",
      name: "Insurance_Claim_Auto.pdf",
      type: "insurance",
      status: "completed",
      uploadedAt: "2024-01-14T11:05:00Z",
      confidence: 92,
      size: "2.1 MB"
    }
  ]);

  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <Clock className="h-4 w-4 text-yellow-500 animate-pulse" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <FileText className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleAISearch = (query: string) => {
    toast({
      title: "AI Search",
      description: `Searching with AI: "${query}"`,
    });
  };

  const handleSort = (column: "name" | "date" | "confidence") => {
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column);
      setSortOrder("desc");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("pie_extractor_auth");
    router.push("/login");
    toast({
      title: "Logged out successfully",
      description: "You have been logged out of your account.",
    });
  };

  const filteredDocuments = documents
    .filter(doc => {
      const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === "all" || doc.status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case "name":
          comparison = a.name.localeCompare(b.name);
          break;
        case "date":
          comparison = new Date(a.uploadedAt).getTime() - new Date(b.uploadedAt).getTime();
          break;
        case "confidence":
          comparison = (a.confidence || 0) - (b.confidence || 0);
          break;
      }
      
      return sortOrder === "asc" ? comparison : -comparison;
    });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 max-w-none">
          <AppHeader 
            showSearch={true}
            onSearch={handleSearch}
            onAISearch={handleAISearch}
            pageType="listView"
            rightContent={
              <div className="flex items-center gap-3">
                <Button 
                  onClick={() => setUploadModalOpen(true)} 
                  variant="gradient"
                  className="shadow-lg"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Upload Document
                </Button>
                
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
                    <DropdownMenuItem onClick={handleLogout}>
                      <LogOut className="h-4 w-4 mr-2" />
                      Logout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            }
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-none">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Documents</p>
                  <p className="text-2xl font-bold">{documents.length}</p>
                </div>
                <FileText className="h-8 w-8 text-primary" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Processing</p>
                  <p className="text-2xl font-bold">{documents.filter(d => d.status === 'processing').length}</p>
                </div>
                <Clock className="h-8 w-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Completed</p>
                  <p className="text-2xl font-bold">{documents.filter(d => d.status === 'completed').length}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Avg. Confidence</p>
                  <p className="text-2xl font-bold">
                    {Math.round(documents.filter(d => d.confidence).reduce((acc, d) => acc + (d.confidence || 0), 0) / documents.filter(d => d.confidence).length)}%
                  </p>
                </div>
                <Brain className="h-8 w-8 text-accent" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Documents Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Documents</CardTitle>
                <CardDescription>
                  Manage your uploaded documents and their extraction status
                </CardDescription>
              </div>
              <div className="flex items-center gap-4">
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-48">
                    <Filter className="h-4 w-4 mr-2" />
                    <SelectValue placeholder="Filter by status" />
                  </SelectTrigger>
                  <SelectContent className="bg-background border shadow-lg z-50">
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="processing">Processing</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Data Table */}
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left p-4 font-medium">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => handleSort("name")}
                        className="hover:bg-muted/30 p-0 h-auto font-medium text-foreground"
                      >
                        Document Name
                        {sortBy === "name" && (
                          <span className="ml-2">{sortOrder === "asc" ? "↑" : "↓"}</span>
                        )}
                      </Button>
                    </th>
                    <th className="text-left p-4 font-medium">Status</th>
                    <th className="text-left p-4 font-medium">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => handleSort("confidence")}
                        className="hover:bg-muted/30 p-0 h-auto font-medium text-foreground"
                      >
                        Confidence
                        {sortBy === "confidence" && (
                          <span className="ml-2">{sortOrder === "asc" ? "↑" : "↓"}</span>
                        )}
                      </Button>
                    </th>
                    <th className="text-left p-4 font-medium">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => handleSort("date")}
                        className="hover:bg-muted/30 p-0 h-auto font-medium text-foreground"
                      >
                        Upload Date
                        {sortBy === "date" && (
                          <span className="ml-2">{sortOrder === "asc" ? "↑" : "↓"}</span>
                        )}
                      </Button>
                    </th>
                    <th className="text-left p-4 font-medium">Size</th>
                    <th className="text-right p-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocuments.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center p-8 text-muted-foreground">
                        <div className="flex flex-col items-center gap-3">
                          <FileText className="h-12 w-12 text-muted-foreground" />
                          <div>
                            <h3 className="font-medium">No documents found</h3>
                            <p className="text-sm">
                              {searchQuery ? "Try adjusting your search" : "Upload your first document to get started"}
                            </p>
                          </div>
                          <Button onClick={() => setUploadModalOpen(true)} size="sm">
                            <Upload className="h-4 w-4 mr-2" />
                            Upload Document
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredDocuments.map((document) => (
                      <tr key={document.id} className="border-b hover:bg-muted/25 transition-colors">
                        <td className="p-4">
                          <Button
                            variant="link"
                            className="p-0 h-auto text-left justify-start font-medium text-primary hover:text-primary/80"
                            onClick={() => router.push(`/document/${document.id}`)}
                          >
                            {document.name}
                          </Button>
                          <div className="text-xs text-muted-foreground mt-1 capitalize">
                            {document.type.replace('-', ' ')}
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(document.status)}
                            <Badge 
                              variant={document.status === 'completed' ? 'default' : 
                                     document.status === 'processing' ? 'secondary' : 'destructive'}
                              className="capitalize"
                            >
                              {document.status}
                            </Badge>
                          </div>
                        </td>
                        <td className="p-4">
                          {document.confidence ? (
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{document.confidence}%</span>
                              <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500"
                                  style={{ width: `${document.confidence}%` }}
                                />
                              </div>
                            </div>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                        <td className="p-4 text-muted-foreground">
                          {new Date(document.uploadedAt).toLocaleDateString()}
                        </td>
                        <td className="p-4 text-muted-foreground text-sm">
                          {document.size}
                        </td>
                        <td className="p-4">
                          <div className="flex justify-end">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end" className="bg-background border shadow-lg z-50">
                                <DropdownMenuItem onClick={() => router.push(`/document/${document.id}`)}>
                                  <Eye className="h-4 w-4 mr-2" />
                                  View Details
                                </DropdownMenuItem>
                                <DropdownMenuItem>
                                  <Download className="h-4 w-4 mr-2" />
                                  Download
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem className="text-destructive">
                                  <Trash2 className="h-4 w-4 mr-2" />
                                  Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </main>

      {/* Upload Modal */}
      <DocumentUploadModal 
        open={uploadModalOpen} 
        onOpenChange={setUploadModalOpen} 
      />
    </div>
  );
};

export default DocumentList;