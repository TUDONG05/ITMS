import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { DocumentsService } from './documents.service';

describe('DocumentsService', () => {
  let service: DocumentsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(DocumentsService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('sends trimmed search, position, format and server pagination', () => {
    service
      .listDocuments({
        search: '  Python  ',
        position: 'BACKEND',
        format: 'pdf',
        skip: 20,
        limit: 10,
      })
      .subscribe();
    const request = http.expectOne((request) => request.url === '/api/v1/documents');
    expect(request.request.params.get('search')).toBe('Python');
    expect(request.request.params.get('position')).toBe('BACKEND');
    expect(request.request.params.get('format')).toBe('pdf');
    expect(request.request.params.get('skip')).toBe('20');
    expect(request.request.params.get('limit')).toBe('10');
    request.flush({ items: [], total: 0, formats: [] });
  });

  it('omits empty filters and defaults pagination', () => {
    service.listDocuments({ search: '  ', position: null, format: '' }).subscribe();
    const request = http.expectOne((request) => request.url === '/api/v1/documents');
    expect(request.request.params.keys().sort()).toEqual(['limit', 'skip']);
    expect(request.request.params.get('limit')).toBe('20');
    expect(request.request.params.get('skip')).toBe('0');
    request.flush({ items: [], total: 0, formats: [] });
  });

  it('edits metadata without exposing URL as an editable field', () => {
    service.updateDocument('doc-1', { title: 'Updated', positions: [] }).subscribe();
    const update = http.expectOne('/api/v1/documents/doc-1');
    expect(update.request.method).toBe('PATCH');
    expect(update.request.body).toEqual({ title: 'Updated', positions: [] });
    update.flush({});
  });

  it('uploads the selected file and metadata together in one multipart request', () => {
    const file = new File(['document'], 'guide.pdf', { type: 'application/pdf' });
    service
      .uploadDocument(file, {
        title: 'Guide',
        description: 'A guide',
        positions: ['BACKEND', 'AI'],
      })
      .subscribe();
    const request = http.expectOne('/api/v1/documents/upload');
    expect(request.request.method).toBe('POST');
    const body = request.request.body as FormData;
    expect(body.get('file')).toBe(file);
    expect(body.get('title')).toBe('Guide');
    expect(body.get('description')).toBe('A guide');
    expect(body.get('positions')).toBe('["BACKEND","AI"]');
    request.flush({});
  });

  it('gets a document and exposes deletion conflicts to the caller', () => {
    service.getDocument('doc-1').subscribe();
    http.expectOne('/api/v1/documents/doc-1').flush({ id: 'doc-1' });
    let status = 0;
    service.deleteDocument('doc-1').subscribe({
      error: (error) => {
        status = error.status;
      },
    });
    const request = http.expectOne('/api/v1/documents/doc-1');
    expect(request.request.method).toBe('DELETE');
    request.flush({ detail: 'Document is in use' }, { status: 409, statusText: 'Conflict' });
    expect(status).toBe(409);
  });

  it('replaces a document file with metadata in one PUT multipart request', () => {
    const file = new File(['replacement'], 'new-guide.pdf', { type: 'application/pdf' });
    service
      .replaceDocumentFile('doc-1', file, {
        title: 'Updated guide',
        description: null,
        positions: ['BA'],
      })
      .subscribe();
    const request = http.expectOne('/api/v1/documents/doc-1/file');
    expect(request.request.method).toBe('PUT');
    const body = request.request.body as FormData;
    expect(body.get('file')).toBe(file);
    expect(body.get('title')).toBe('Updated guide');
    expect(body.get('positions')).toBe('["BA"]');
    expect(body.has('url')).toBe(false);
    request.flush({});
  });
});
