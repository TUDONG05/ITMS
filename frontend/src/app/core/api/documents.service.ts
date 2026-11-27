import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { InternshipPosition } from './internship.service';

export interface LibraryDocument {
  id: string;
  title: string;
  description: string | null;
  url: string;
  format: string;
  positions: InternshipPosition[];
  original_filename: string | null;
  size_bytes: number | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  usage_count: number;
}

export interface DocumentListResponse {
  items: LibraryDocument[];
  total: number;
  formats: string[];
}

export interface DocumentQuery {
  search?: string;
  position?: InternshipPosition | '' | null;
  format?: string | null;
  skip?: number;
  limit?: number;
}

export interface DocumentPayload {
  title: string;
  description?: string | null;
  positions?: InternshipPosition[];
}

export interface DocumentUploadPayload {
  title: string;
  description?: string | null;
  positions?: InternshipPosition[];
}

@Injectable({ providedIn: 'root' })
export class DocumentsService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/v1/documents';

  listDocuments(query: DocumentQuery = {}): Observable<DocumentListResponse> {
    let params = new HttpParams().set('skip', query.skip ?? 0).set('limit', query.limit ?? 20);
    if (query.search?.trim()) params = params.set('search', query.search.trim());
    if (query.position) params = params.set('position', query.position);
    if (query.format) params = params.set('format', query.format);
    return this.http.get<DocumentListResponse>(this.base, { params });
  }

  getDocument(id: string): Observable<LibraryDocument> {
    return this.http.get<LibraryDocument>(`${this.base}/${id}`);
  }

  updateDocument(id: string, payload: Partial<DocumentPayload>): Observable<LibraryDocument> {
    return this.http.patch<LibraryDocument>(`${this.base}/${id}`, payload);
  }

  deleteDocument(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  uploadDocument(file: File, payload: DocumentUploadPayload): Observable<LibraryDocument> {
    return this.http.post<LibraryDocument>(`${this.base}/upload`, this.fileForm(file, payload));
  }

  replaceDocumentFile(
    id: string,
    file: File,
    payload: DocumentUploadPayload,
  ): Observable<LibraryDocument> {
    return this.http.put<LibraryDocument>(`${this.base}/${id}/file`, this.fileForm(file, payload));
  }

  private fileForm(file: File, payload: DocumentUploadPayload): FormData {
    const form = new FormData();
    form.append('file', file);
    form.append('title', payload.title);
    if (payload.description) form.append('description', payload.description);
    form.append('positions', JSON.stringify(payload.positions ?? []));
    return form;
  }
}
