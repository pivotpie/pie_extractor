import { DocumentMetadata, DocumentType, DocumentStatus, InvoiceData, FinancialData, LegalDocumentData } from '@/types/document';

// Generate a random date within the last 30 days
const randomDate = () => {
  const now = new Date();
  const pastDate = new Date(now);
  pastDate.setDate(now.getDate() - Math.floor(Math.random() * 30));
  return pastDate.toISOString();
};

// Generate a random document status
const randomStatus = (): DocumentStatus => {
  const statuses: DocumentStatus[] = ['processing', 'completed', 'error', 'queued'];
  return statuses[Math.floor(Math.random() * statuses.length)];
};

// Generate a random document type
const randomType = (): DocumentType => {
  const types: DocumentType[] = ['invoice', 'receipt', 'contract', 'financial', 'other'];
  return types[Math.floor(Math.random() * types.length)];
};

// Generate mock invoice data
const generateInvoice = (): InvoiceData => ({
  vendor: ['Acme Inc.', 'Globex Corp', 'Soylent Corp', 'Initech', 'Umbrella Corp'][Math.floor(Math.random() * 5)],
  invoiceNumber: `INV-${Math.floor(1000 + Math.random() * 9000)}`,
  date: randomDate(),
  dueDate: randomDate(),
  totalAmount: parseFloat((Math.random() * 1000).toFixed(2)),
  taxAmount: parseFloat((Math.random() * 100).toFixed(2)),
  lineItems: Array.from({ length: Math.floor(Math.random() * 5) + 1 }, (_, i) => ({
    description: `Item ${i + 1}`,
    quantity: Math.floor(Math.random() * 10) + 1,
    unitPrice: parseFloat((Math.random() * 100).toFixed(2)),
    amount: parseFloat((Math.random() * 500).toFixed(2)),
  })),
});

// Generate mock financial data
const generateFinancial = (): FinancialData => ({
  accountNumber: `ACCT-${Math.floor(10000000 + Math.random() * 90000000)}`,
  statementDate: randomDate(),
  startDate: randomDate(),
  endDate: randomDate(),
  openingBalance: parseFloat((Math.random() * 10000).toFixed(2)),
  closingBalance: parseFloat((Math.random() * 10000).toFixed(2)),
  transactions: Array.from({ length: Math.floor(Math.random() * 10) + 1 }, (_, i) => ({
    date: randomDate(),
    description: ['Deposit', 'Withdrawal', 'Payment', 'Transfer', 'Fee'][Math.floor(Math.random() * 5)],
    amount: parseFloat((Math.random() * 1000).toFixed(2)),
    type: Math.random() > 0.5 ? 'credit' : 'debit',
    balance: parseFloat((Math.random() * 10000).toFixed(2)),
  })),
});

// Generate mock legal document data
const generateLegal = (): LegalDocumentData => ({
  title: ['Non-Disclosure Agreement', 'Employment Contract', 'Service Agreement', 'Lease Agreement', 'Partnership Agreement'][Math.floor(Math.random() * 5)],
  parties: ['Acme Inc.', 'John Doe', 'Jane Smith', 'Acme Corp', 'XYZ Ltd'].slice(0, Math.floor(Math.random() * 3) + 2),
  effectiveDate: randomDate(),
  expirationDate: Math.random() > 0.3 ? randomDate() : undefined,
  summary: 'This is a sample legal document summary. It contains important terms and conditions that all parties must agree to.',
  keyClauses: Array.from({ length: Math.floor(Math.random() * 3) + 1 }, (_, i) => ({
    title: `Clause ${i + 1}`,
    content: `This is the content of clause ${i + 1}. It outlines specific terms and conditions that are legally binding.`,
    page: i + 1,
  })),
});

// Generate a single mock document
const generateMockDocument = (id: string): DocumentMetadata => {
  const type = randomType();
  const status = randomStatus();
  const now = new Date().toISOString();
  
  return {
    id,
    name: `${type.charAt(0).toUpperCase() + type.slice(1)}_${Math.floor(1000 + Math.random() * 9000)}.pdf`,
    type,
    status,
    createdAt: randomDate(),
    updatedAt: now,
    size: Math.floor(Math.random() * 5000000) + 100000, // 100KB - 5MB
    mimeType: 'application/pdf',
    pageCount: Math.floor(Math.random() * 20) + 1,
    previewUrl: `/sample-preview-${Math.floor(Math.random() * 3) + 1}.jpg`,
    thumbnailUrl: `/sample-thumb-${Math.floor(Math.random() * 3) + 1}.jpg`,
    ...(status === 'error' ? { error: 'Failed to process document' } : {}),
  };
};

// Generate a list of mock documents
export const generateMockDocuments = (count: number = 20): DocumentMetadata[] => {
  return Array.from({ length: count }, (_, i) => generateMockDocument(`doc-${i + 1}`));
};

// Get mock document with extracted data
export const getMockDocumentWithData = (id: string) => {
  const doc = generateMockDocument(id);
  let extractedData;

  switch (doc.type) {
    case 'invoice':
    case 'receipt':
      extractedData = { type: 'invoice', data: generateInvoice() };
      break;
    case 'financial':
    case 'statement':
      extractedData = { type: 'financial', data: generateFinancial() };
      break;
    case 'contract':
    case 'agreement':
      extractedData = { type: 'legal', data: generateLegal() };
      break;
    default:
      extractedData = { type: 'other', data: { message: 'No specific data extracted' } };
  }

  return {
    ...doc,
    extractedData,
  };
};

// Mock user data
export const mockUser = {
  id: 'user-123',
  name: 'John Doe',
  email: 'john.doe@example.com',
  image: 'https://i.pravatar.cc/150?img=32',
  role: 'user',
};

// Mock statistics
export const mockStats = {
  total: 42,
  byType: {
    invoice: 12,
    receipt: 8,
    contract: 10,
    financial: 7,
    other: 5,
  },
  byStatus: {
    processing: 3,
    completed: 35,
    error: 2,
    queued: 2,
  },
  recentUploads: generateMockDocuments(5),
};
