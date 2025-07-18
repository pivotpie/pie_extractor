import { DocumentMetadata, DocumentListResponse, UploadDocumentResponse, DocumentWithData } from '@/types/document';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || 'An error occurred');
  }

  return response.json();
}

/**
 * Document API service for handling all document-related operations
 */
export const documentApi = {
  /**
   * Upload a document
   */
  async uploadDocument(file: File): Promise<UploadDocumentResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || 'Failed to upload document');
    }

    return response.json();
  },

  /**
   * Get a list of documents with pagination
   */
  async getDocuments(
    page = 1,
    pageSize = 10,
    status?: string
  ): Promise<DocumentListResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      pageSize: pageSize.toString(),
      ...(status && { status }),
    });

    return fetchWithAuth(`/documents?${params.toString()}`);
  },

  /**
   * Get document by ID
   */
  async getDocumentById(id: string): Promise<DocumentWithData> {
    return fetchWithAuth(`/documents/${id}`);
  },

  /**
   * Delete a document
   */
  async deleteDocument(id: string): Promise<void> {
    await fetchWithAuth(`/documents/${id}`, {
      method: 'DELETE',
    });
  },

  /**
   * Get document preview URL
   */
  getPreviewUrl(id: string, page = 1): string {
    return `${API_BASE_URL}/documents/${id}/preview?page=${page}`;
  },

  /**
   * Get document thumbnail URL
   */
  getThumbnailUrl(id: string): string {
    return `${API_BASE_URL}/documents/${id}/thumbnail`;
  },

  /**
   * Update document metadata
   */
  async updateDocument(
    id: string,
    updates: Partial<DocumentMetadata>
  ): Promise<DocumentMetadata> {
    return fetchWithAuth(`/documents/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  /**
   * Search documents
   */
  async searchDocuments(
    query: string,
    page = 1,
    pageSize = 10
  ): Promise<DocumentListResponse> {
    const params = new URLSearchParams({
      q: query,
      page: page.toString(),
      pageSize: pageSize.toString(),
    });

    return fetchWithAuth(`/documents/search?${params.toString()}`);
  },

  /**
   * Get document extraction results
   */
  async getExtractionResults(id: string): Promise<any> {
    return fetchWithAuth(`/documents/${id}/extract`);
  },

  /**
   * Reprocess a document
   */
  async reprocessDocument(id: string): Promise<{ status: string }> {
    return fetchWithAuth(`/documents/${id}/reprocess`, {
      method: 'POST',
    });
  },

  /**
   * Export document data
   */
  async exportDocument(
    id: string,
    format: 'json' | 'csv' | 'pdf' = 'json'
  ): Promise<Blob> {
    const response = await fetch(
      `${API_BASE_URL}/documents/${id}/export?format=${format}`,
      {
        credentials: 'include',
        headers: {
          Accept: 'application/octet-stream',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || 'Failed to export document');
    }

    return response.blob();
  },

  /**
   * Get document statistics
   */
  async getStatistics(): Promise<{
    total: number;
    byType: Record<string, number>;
    byStatus: Record<string, number>;
    recentUploads: DocumentMetadata[];
  }> {
    return fetchWithAuth('/documents/statistics');
  },

  /**
   * Batch delete documents
   */
  async batchDelete(ids: string[]): Promise<{ success: boolean }> {
    return fetchWithAuth('/documents/batch-delete', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    });
  },
};

/**
 * Authentication API service
 */
export const authApi = {
  /**
   * Sign in with email and password
   */
  async signIn(credentials: { email: string; password: string }) {
    const response = await fetch(`${API_BASE_URL}/auth/signin`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || 'Sign in failed');
    }

    return response.json();
  },

  /**
   * Sign up a new user
   */
  async signUp(userData: {
    name: string;
    email: string;
    password: string;
  }) {
    const response = await fetch(`${API_BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || 'Sign up failed');
    }

    return response.json();
  },

  /**
   * Sign out the current user
   */
  async signOut() {
    const response = await fetch(`${API_BASE_URL}/auth/signout`, {
      method: 'POST',
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to sign out');
    }
  },

  /**
   * Get the current user's session
   */
  async getSession() {
    const response = await fetch(`${API_BASE_URL}/auth/session`, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to get session');
    }

    return response.json();
  },

  /**
   * Request a password reset
   */
  async requestPasswordReset(email: string) {
    const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || 'Failed to request password reset');
    }

    return response.json();
  },

  /**
   * Reset password with a token
   */
  async resetPassword(token: string, newPassword: string) {
    const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token, newPassword }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || 'Failed to reset password');
    }

    return response.json();
  },
};

/**
 * User profile API service
 */
export const userApi = {
  /**
   * Get current user's profile
   */
  async getProfile() {
    return fetchWithAuth('/user/profile');
  },

  /**
   * Update user's profile
   */
  async updateProfile(updates: {
    name?: string;
    email?: string;
    avatar?: File;
  }) {
    const formData = new FormData();
    
    if (updates.name) formData.append('name', updates.name);
    if (updates.email) formData.append('email', updates.email);
    if (updates.avatar) formData.append('avatar', updates.avatar);

    const response = await fetch(`${API_BASE_URL}/user/profile`, {
      method: 'PATCH',
      body: formData,
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || 'Failed to update profile');
    }

    return response.json();
  },

  /**
   * Change user's password
   */
  async changePassword(currentPassword: string, newPassword: string) {
    return fetchWithAuth('/user/change-password', {
      method: 'POST',
      body: JSON.stringify({ currentPassword, newPassword }),
    });
  },

  /**
   * Get user's activity log
   */
  async getActivityLog(page = 1, pageSize = 10) {
    const params = new URLSearchParams({
      page: page.toString(),
      pageSize: pageSize.toString(),
    });

    return fetchWithAuth(`/user/activity?${params.toString()}`);
  },
};
