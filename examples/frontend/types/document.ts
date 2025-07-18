export type DocumentType = 'invoice' | 'receipt' | 'contract' | 'financial' |  'statement' |  'agreement' | 'other';

export type DocumentStatus = 'processing' | 'completed' | 'error' | 'queued';

export interface DocumentMetadata {
  id: string;
  name: string;
  type: DocumentType;
  status: DocumentStatus;
  createdAt: string;
  updatedAt: string;
  size: number;
  mimeType: string;
  pageCount?: number;
  extractedData?: Record<string, any>;
  previewUrl?: string;
  thumbnailUrl?: string;
  error?: string;
}

export interface InvoiceData {
  vendor: string;
  invoiceNumber: string;
  date: string;
  dueDate?: string;
  totalAmount: number;
  taxAmount?: number;
  lineItems: Array<{
    description: string;
    quantity: number;
    unitPrice: number;
    amount: number;
  }>;
}

export interface FinancialData {
  accountNumber: string;
  statementDate: string;
  startDate: string;
  endDate: string;
  openingBalance: number;
  closingBalance: number;
  transactions: Array<{
    date: string;
    description: string;
    amount: number;
    type: 'credit' | 'debit';
    balance: number;
  }>;
}

export interface LegalDocumentData {
  title: string;
  parties: string[];
  effectiveDate: string;
  expirationDate?: string;
  summary: string;
  keyClauses: Array<{
    title: string;
    content: string;
    page: number;
  }>;
}

export type ExtractedDocumentData = 
  | { type: 'invoice'; data: InvoiceData }
  | { type: 'financial'; data: FinancialData }
  | { type: 'legal'; data: LegalDocumentData }
  | { type: 'other'; data: Record<string, any> };

export interface DocumentWithData extends DocumentMetadata {
  extractedData?: ExtractedDocumentData;
}

export interface DocumentListResponse {
  documents: DocumentMetadata[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface UploadDocumentResponse {
  id: string;
  status: DocumentStatus;
  message?: string;
}
