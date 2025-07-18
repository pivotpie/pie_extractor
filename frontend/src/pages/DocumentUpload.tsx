import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Upload, 
  FileText, 
  Image, 
  File, 
  Brain,
  ArrowLeft,
  Check,
  X,
  AlertCircle,
  Zap
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AppHeader from "@/components/AppHeader";

interface UploadedFile {
  id: string;
  file: File;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  preview?: string;
}

const DocumentUpload = () => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      handleFiles(files);
    }
  };

  const handleFiles = (files: File[]) => {
    const validFiles = files.filter(file => {
      const validTypes = [
        'application/pdf',
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/tiff',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      ];
      
      if (!validTypes.includes(file.type)) {
        toast({
          title: "Invalid File Type",
          description: `${file.name} is not a supported file type.`,
          variant: "destructive",
        });
        return false;
      }
      
      if (file.size > 50 * 1024 * 1024) { // 50MB limit
        toast({
          title: "File Too Large",
          description: `${file.name} exceeds the 50MB limit.`,
          variant: "destructive",
        });
        return false;
      }
      
      return true;
    });

    const newFiles: UploadedFile[] = validFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      status: 'uploading',
      progress: 0,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
    }));

    setUploadedFiles(prev => [...prev, ...newFiles]);
    
    // Simulate upload and processing
    newFiles.forEach(uploadedFile => {
      simulateFileProcessing(uploadedFile.id);
    });
  };

  const simulateFileProcessing = async (fileId: string) => {
    // Upload simulation
    for (let progress = 0; progress <= 100; progress += 10) {
      await new Promise(resolve => setTimeout(resolve, 100));
      setUploadedFiles(prev => prev.map(file => 
        file.id === fileId 
          ? { ...file, progress, status: progress === 100 ? 'processing' : 'uploading' }
          : file
      ));
    }

    // Processing simulation
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Random success/failure for demo
    const isSuccess = Math.random() > 0.2; // 80% success rate
    
    setUploadedFiles(prev => prev.map(file => 
      file.id === fileId 
        ? { ...file, status: isSuccess ? 'completed' : 'failed', progress: 100 }
        : file
    ));

    if (isSuccess) {
      toast({
        title: "Document Processed",
        description: "AI extraction completed successfully.",
      });
    } else {
      toast({
        title: "Processing Failed",
        description: "Please try uploading the document again.",
        variant: "destructive",
      });
    }
  };

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
  };

  const getFileIcon = (fileType: string) => {
    if (fileType.startsWith('image/')) {
      return <Image className="h-5 w-5" />;
    } else if (fileType === 'application/pdf') {
      return <FileText className="h-5 w-5" />;
    }
    return <File className="h-5 w-5" />;
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'completed':
        return <Check className="h-4 w-4 text-success" />;
      case 'failed':
        return <X className="h-4 w-4 text-destructive" />;
      case 'processing':
        return <Brain className="h-4 w-4 text-primary animate-pulse" />;
      default:
        return <Upload className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 max-w-none">
          <AppHeader 
            title="Upload Documents"
            subtitle="AI-powered data extraction"
            showBackButton={true}
            backTo="/documents"
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-none">
        <div className="max-w-4xl mx-auto space-y-8">
          
          {/* Upload Area */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-primary" />
                Intelligent Data Extraction
              </CardTitle>
              <CardDescription>
                Upload your documents and let our AI extract key information automatically. 
                Supports PDFs, images, and Office documents up to 50MB.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className={`
                  border-2 border-dashed rounded-lg p-12 text-center transition-colors duration-200
                  ${isDragOver 
                    ? "border-primary bg-primary/5" 
                    : "border-border hover:border-primary/50"
                  }
                `}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <div className="flex flex-col items-center gap-4">
                  <div className="bg-primary/10 p-4 rounded-full">
                    <Upload className="h-8 w-8 text-primary" />
                  </div>
                  
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold">
                      Drop your documents here
                    </h3>
                    <p className="text-muted-foreground">
                      or click to browse your files
                    </p>
                  </div>

                  <input
                    type="file"
                    multiple
                    accept=".pdf,.jpg,.jpeg,.png,.tiff,.doc,.docx"
                    onChange={handleFileInput}
                    className="hidden"
                    id="file-upload"
                  />
                  <label htmlFor="file-upload">
                    <Button variant="gradient" className="cursor-pointer">
                      <Upload className="h-4 w-4 mr-2" />
                      Choose Files
                    </Button>
                  </label>

                  <div className="flex flex-wrap gap-2 mt-4">
                    <Badge variant="outline">PDF</Badge>
                    <Badge variant="outline">JPG/PNG</Badge>
                    <Badge variant="outline">TIFF</Badge>
                    <Badge variant="outline">Word Docs</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Processing Features */}
          <div className="grid md:grid-cols-3 gap-6">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="bg-primary/10 p-2 rounded-lg">
                    <Brain className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="font-semibold">AI Extraction</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  Advanced OCR and ML models extract text, tables, and structured data with 95%+ accuracy.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="bg-accent/10 p-2 rounded-lg">
                    <Zap className="h-5 w-5 text-accent" />
                  </div>
                  <h3 className="font-semibold">Smart Classification</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  Automatically identifies document types and extracts relevant fields for each category.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="bg-success/10 p-2 rounded-lg">
                    <Check className="h-5 w-5 text-success" />
                  </div>
                  <h3 className="font-semibold">Quality Assurance</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  Confidence scoring and validation ensure accurate data extraction every time.
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Uploaded Files */}
          {uploadedFiles.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Processing Queue</CardTitle>
                <CardDescription>
                  Monitor the progress of your data extraction
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {uploadedFiles.map((uploadedFile) => (
                  <div key={uploadedFile.id} className="border rounded-lg p-4">
                    <div className="flex items-center gap-4">
                      {uploadedFile.preview ? (
                        <img 
                          src={uploadedFile.preview} 
                          alt="Preview" 
                          className="w-12 h-12 object-cover rounded"
                        />
                      ) : (
                        <div className="w-12 h-12 bg-muted rounded flex items-center justify-center">
                          {getFileIcon(uploadedFile.file.type)}
                        </div>
                      )}
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium truncate">{uploadedFile.file.name}</h4>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(uploadedFile.status)}
                            <span className="text-sm capitalize text-muted-foreground">
                              {uploadedFile.status}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeFile(uploadedFile.id)}
                              className="h-6 w-6"
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{(uploadedFile.file.size / 1024 / 1024).toFixed(1)} MB</span>
                          
                          {uploadedFile.status !== 'failed' && (
                            <div className="flex-1 max-w-xs">
                              <Progress value={uploadedFile.progress} className="h-2" />
                            </div>
                          )}
                          
                          {uploadedFile.status === 'failed' && (
                            <div className="flex items-center gap-1 text-destructive">
                              <AlertCircle className="h-3 w-3" />
                              <span>Processing failed</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                
                <div className="flex justify-end gap-2 pt-4 border-t">
                  <Button variant="outline" onClick={() => navigate("/documents")}>
                    View All Documents
                  </Button>
                  <Button 
                    variant="gradient"
                    disabled={uploadedFiles.some(f => f.status === 'uploading' || f.status === 'processing')}
                  >
                    Process More Documents
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
};

export default DocumentUpload;