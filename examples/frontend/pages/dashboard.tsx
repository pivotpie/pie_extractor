import { useState } from 'react';
import { 
  Box, 
  Container, 
  Grid, 
  Paper, 
  Typography, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemAvatar, 
  Avatar, 
  Divider, 
  Chip, 
  IconButton,
  Tabs,
  Tab,
  Badge,
  Card,
  CardContent,
  Button,
  TextField,
  InputAdornment,
  Skeleton,
} from '@mui/material';
import { 
  InsertDriveFile as FileIcon, 
  Search as SearchIcon,
  CloudUpload as UploadIcon,
  Refresh as RefreshIcon,
  PictureAsPdf as PdfIcon,
  Receipt as ReceiptIcon,
  Description as DocumentIcon,
  AccountBalance as BankIcon,
  Gavel as LegalIcon,
  MoreHoriz as MoreIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Share as ShareIcon,
} from '@mui/icons-material';
import { generateMockDocuments, getMockDocumentWithData, mockStats } from '@/services/mockData';
import { formatBytes, formatDate, formatDateRange } from '@/utils/formatters';

// Mock data
const documents = generateMockDocuments(15);

export default function Dashboard() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDoc, setSelectedDoc] = useState(documents[0]?.id || null);
  const [isLoading, setIsLoading] = useState(false);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setSelectedTab(newValue);
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'processing': return 'info';
      case 'error': return 'error';
      case 'queued': return 'warning';
      default: return 'default';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'invoice':
      case 'receipt':
        return <ReceiptIcon color="primary" />;
      case 'financial':
        return <BankIcon color="secondary" />;
      case 'contract':
      case 'agreement':
        return <LegalIcon color="warning" />;
      default:
        return <DocumentIcon />;
    }
  };

  const filteredDocuments = documents.filter(doc => 
    doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedDocument = selectedDoc ? getMockDocumentWithData(selectedDoc) : null;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'grey.50' }}>
      {/* Sidebar */}
      <Box sx={{ width: 280, borderRight: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6" noWrap>Documents</Typography>
          <TextField
            fullWidth
            size="small"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={handleSearch}
            sx={{ mt: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" />
                </InputAdornment>
              ),
            }}
          />
          <Button 
            fullWidth 
            variant="contained" 
            startIcon={<UploadIcon />} 
            sx={{ mt: 2 }}
          >
            Upload
          </Button>
        </Box>
        
        <Tabs 
          value={selectedTab} 
          onChange={handleTabChange}
          variant="fullWidth"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab 
            label={
              <Badge badgeContent={mockStats.total} color="primary" max={99}>
                <span>All</span>
              </Badge>
            } 
          />
          <Tab label="Recent" />
          <Tab label="Starred" />
        </Tabs>
        
        <List sx={{ overflowY: 'auto', height: 'calc(100vh - 200px)' }}>
          {filteredDocuments.map((doc) => (
            <div key={doc.id}>
              <ListItem 
                button 
                selected={selectedDoc === doc.id}
                onClick={() => setSelectedDoc(doc.id)}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: 'action.selected',
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                  },
                }}
              >
                <ListItemAvatar>
                  <Avatar sx={{ bgcolor: 'grey.100' }}>
                    {getTypeIcon(doc.type)}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Typography noWrap sx={{ fontWeight: selectedDoc === doc.id ? 'bold' : 'normal' }}>
                      {doc.name}
                    </Typography>
                  }
                  secondary={
                    <>
                      <Box component="span" sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                        <Chip 
                          label={doc.type} 
                          size="small" 
                          variant="outlined"
                          sx={{ textTransform: 'capitalize', height: 20 }}
                        />
                        <Chip 
                          label={doc.status} 
                          size="small" 
                          color={getStatusColor(doc.status) as any}
                          sx={{ textTransform: 'capitalize', height: 20 }}
                        />
                      </Box>
                      <Typography variant="caption" display="block" color="text.secondary">
                        {formatBytes(doc.size)} • {formatDate(doc.createdAt)}
                      </Typography>
                    </>
                  }
                  primaryTypographyProps={{ noWrap: true }}
                  secondaryTypographyProps={{ component: 'div' }}
                />
              </ListItem>
              <Divider component="li" />
            </div>
          ))}
        </List>
      </Box>

      {/* Main content */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {selectedDocument ? (
          <>
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="h6" noWrap>{selectedDocument.name}</Typography>
                  <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                    <Chip 
                      label={selectedDocument.type} 
                      size="small" 
                      variant="outlined"
                      sx={{ textTransform: 'capitalize' }}
                    />
                    <Chip 
                      label={selectedDocument.status} 
                      size="small" 
                      color={getStatusColor(selectedDocument.status) as any}
                      sx={{ textTransform: 'capitalize' }}
                    />
                    <Typography variant="body2" color="text.secondary">
                      {formatBytes(selectedDocument.size)} • {formatDate(selectedDocument.createdAt)}
                    </Typography>
                  </Box>
                </Box>
                <Box>
                  <IconButton><DownloadIcon /></IconButton>
                  <IconButton><ShareIcon /></IconButton>
                  <IconButton color="error"><DeleteIcon /></IconButton>
                </Box>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
              {/* Document preview */}
              <Box sx={{ flex: 1, p: 2, overflow: 'auto', bgcolor: 'grey.100' }}>
                <Paper sx={{ 
                  height: '100%', 
                  display: 'flex', 
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  p: 4,
                  bgcolor: 'white',
                  boxShadow: 1,
                }}>
                  <PdfIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
                  <Typography variant="h6" gutterBottom>Document Preview</Typography>
                  <Typography color="text.secondary" align="center" sx={{ maxWidth: 400, mb: 3 }}>
                    This is a placeholder for the document preview. In a real application, this would display the actual document.
                  </Typography>
                  <Button variant="outlined" startIcon={<DownloadIcon />}>
                    Download Original
                  </Button>
                </Paper>
              </Box>

              {/* Extracted data panel */}
              <Box sx={{ width: 350, borderLeft: 1, borderColor: 'divider', p: 2, bgcolor: 'background.paper', overflowY: 'auto' }}>
                <Typography variant="subtitle1" gutterBottom>Extracted Data</Typography>
                
                {selectedDocument.extractedData ? (
                  <Card variant="outlined" sx={{ mb: 2 }}>
                    <CardContent>
                      {selectedDocument.extractedData.type === 'invoice' && (
                        <>
                          <Typography variant="h6" gutterBottom>Invoice Details</Typography>
                          <Typography variant="body2" color="text.secondary">
                            Vendor: {selectedDocument.extractedData.data.vendor}<br />
                            Invoice #: {selectedDocument.extractedData.data.invoiceNumber}<br />
                            Date: {formatDate(selectedDocument.extractedData.data.date)}<br />
                            Total: ${selectedDocument.extractedData.data.totalAmount.toFixed(2)}<br />
                          </Typography>
                        </>
                      )}
                      
                      {selectedDocument.extractedData.type === 'financial' && (
                        <>
                          <Typography variant="h6" gutterBottom>Financial Statement</Typography>
                          <Typography variant="body2" color="text.secondary">
                            Account: {selectedDocument.extractedData.data.accountNumber}<br />
                            Period: {formatDateRange(selectedDocument.extractedData.data.startDate, selectedDocument.extractedData.data.endDate)}<br />
                            Balance: ${selectedDocument.extractedData.data.closingBalance.toFixed(2)}<br />
                          </Typography>
                        </>
                      )}
                      
                      {selectedDocument.extractedData.type === 'legal' && (
                        <>
                          <Typography variant="h6" gutterBottom>{selectedDocument.extractedData.data.title}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            Parties: {selectedDocument.extractedData.data.parties.join(', ')}<br />
                            Effective: {formatDate(selectedDocument.extractedData.data.effectiveDate)}<br />
                            {selectedDocument.extractedData.data.expirationDate && (
                              <>Expires: {formatDate(selectedDocument.extractedData.data.expirationDate)}<br /></>
                            )}
                          </Typography>
                        </>
                      )}
                      
                      {selectedDocument.extractedData.type === 'other' && (
                        <Typography variant="body2" color="text.secondary">
                          No specific data extracted from this document.
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No data extracted yet. Processing may still be in progress.
                  </Typography>
                )}
                
                <Typography variant="subtitle2" sx={{ mt: 3, mb: 1 }}>Actions</Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Button size="small" variant="outlined" startIcon={<RefreshIcon />}>
                    Reprocess
                  </Button>
                  <Button size="small" variant="outlined" startIcon={<MoreIcon />}>
                    More Actions
                  </Button>
                </Box>
              </Box>
            </Box>
          </>
        ) : (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <Typography color="text.secondary">Select a document to view details</Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
}


