import React, { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { 
  Upload, 
  FileText, 
  Image, 
  File, 
  Brain,
  Check,
  X,
  AlertCircle,
  Zap
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface UploadedFile {
  id: string;
  file: File;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  preview?: string;
}

interface DocumentUploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const DocumentUploadModal = ({ open, onOpenChange }: DocumentUploadModalProps) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
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

  const handleClose = () => {
    setUploadedFiles([]);
    setIsDragOver(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            Upload Documents
          </DialogTitle>
          <DialogDescription>
            AI-powered data extraction - Upload your documents and let our AI extract key information automatically.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Upload Area */}
          <Card>
            <CardContent className="p-6">
              <div
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-200
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
                  <div className="bg-primary/10 p-3 rounded-full">
                    <Upload className="h-6 w-6 text-primary" />
                  </div>
                  
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold">
                      Drop your documents here
                    </h3>
                    <p className="text-muted-foreground text-sm">
                      or click to browse your files
                    </p>
                  </div>

                  <input
                    type="file"
                    multiple
                    accept=".pdf,.jpg,.jpeg,.png,.tiff,.doc,.docx"
                    onChange={handleFileInput}
                    className="hidden"
                    id="file-upload-modal"
                  />
                  <label htmlFor="file-upload-modal">
                    <Button variant="gradient" className="cursor-pointer">
                      <Upload className="h-4 w-4 mr-2" />
                      Choose Files
                    </Button>
                  </label>

                  <div className="flex flex-wrap gap-2 mt-4">
                    <Badge variant="outline" className="text-xs">PDF</Badge>
                    <Badge variant="outline" className="text-xs">JPG/PNG</Badge>
                    <Badge variant="outline" className="text-xs">TIFF</Badge>
                    <Badge variant="outline" className="text-xs">Word Docs</Badge>
                  </div>
                  
                  <p className="text-xs text-muted-foreground">
                    Supports documents up to 50MB
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Processing Features */}
          <div className="grid md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="bg-primary/10 p-1 rounded">
                    <Brain className="h-4 w-4 text-primary" />
                  </div>
                  <h3 className="font-semibold text-sm">AI Extraction</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  Advanced OCR and ML models extract text and data with 95%+ accuracy.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="bg-accent/10 p-1 rounded">
                    <Zap className="h-4 w-4 text-accent" />
                  </div>
                  <h3 className="font-semibold text-sm">Smart Classification</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  Automatically identifies document types and extracts relevant fields.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="bg-success/10 p-1 rounded">
                    <Check className="h-4 w-4 text-success" />
                  </div>
                  <h3 className="font-semibold text-sm">Quality Assurance</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  Confidence scoring and validation ensure accurate extraction.
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Uploaded Files */}
          {uploadedFiles.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Processing Queue</CardTitle>
                <CardDescription className="text-sm">
                  Monitor the progress of your data extraction
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {uploadedFiles.map((uploadedFile) => (
                  <div key={uploadedFile.id} className="border rounded-lg p-3">
                    <div className="flex items-center gap-3">
                      {uploadedFile.preview ? (
                        <img 
                          src={uploadedFile.preview} 
                          alt="Preview" 
                          className="w-10 h-10 object-cover rounded"
                        />
                      ) : (
                        <div className="w-10 h-10 bg-muted rounded flex items-center justify-center">
                          {getFileIcon(uploadedFile.file.type)}
                        </div>
                      )}
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="font-medium truncate text-sm">{uploadedFile.file.name}</h4>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(uploadedFile.status)}
                            <span className="text-xs capitalize text-muted-foreground">
                              {uploadedFile.status}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeFile(uploadedFile.id)}
                              className="h-5 w-5"
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span>{(uploadedFile.file.size / 1024 / 1024).toFixed(1)} MB</span>
                          
                          {uploadedFile.status !== 'failed' && (
                            <div className="flex-1 max-w-48">
                              <Progress value={uploadedFile.progress} className="h-1.5" />
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
                
                <div className="flex justify-end gap-2 pt-3 border-t">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleClose}
                  >
                    Close
                  </Button>
                  <Button 
                    variant="gradient"
                    size="sm"
                    disabled={uploadedFiles.some(f => f.status === 'uploading' || f.status === 'processing')}
                    onClick={() => {
                      // Clear completed files and allow more uploads
                      setUploadedFiles(prev => prev.filter(f => f.status === 'uploading' || f.status === 'processing'));
                    }}
                  >
                    Upload More
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default DocumentUploadModal;