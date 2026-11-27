import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import {
  CheckOutline,
  CloseOutline,
  DoubleLeftOutline,
  DoubleRightOutline,
  DownOutline,
  LeftOutline,
  LoadingOutline,
  RightOutline,
} from '@ant-design/icons-angular/icons';
import { provideNzIcons } from 'ng-zorro-antd/icon';
import { NzMessageService } from 'ng-zorro-antd/message';
import { Observable, Subject, of, throwError } from 'rxjs';
import {
  DocumentListResponse,
  DocumentsService,
  LibraryDocument,
} from '../../core/api/documents.service';
import { DocumentManagementComponent } from './document-management.component';

const DOCUMENT: LibraryDocument = {
  id: 'document-1',
  title: 'Hướng dẫn Python',
  description: 'Tài liệu nhập môn',
  url: 'https://example.com/guide.pdf',
  format: 'pdf',
  positions: ['BACKEND'],
  original_filename: null,
  size_bytes: null,
  usage_count: 0,
  created_by: 'admin-1',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('DocumentManagementComponent', () => {
  let fixture: ComponentFixture<DocumentManagementComponent>;
  let component: DocumentManagementComponent;
  const listDocuments = vi.fn();
  const replaceDocumentFile = vi.fn();
  const updateDocument = vi.fn();
  const uploadDocument = vi.fn();
  const deleteDocument = vi.fn();
  const message = { success: vi.fn(), error: vi.fn() };

  beforeEach(() => {
    listDocuments
      .mockReset()
      .mockReturnValue(of({ items: [DOCUMENT], total: 1, formats: ['pdf', 'docx'] }));
    replaceDocumentFile.mockReset().mockReturnValue(of(DOCUMENT));
    updateDocument.mockReset().mockReturnValue(of(DOCUMENT));
    uploadDocument.mockReset().mockReturnValue(of(DOCUMENT));
    deleteDocument.mockReset().mockReturnValue(of(undefined));
    message.error.mockReset();
    TestBed.configureTestingModule({
      imports: [DocumentManagementComponent],
      providers: [
        provideNoopAnimations(),
        provideNzIcons([
          CheckOutline,
          CloseOutline,
          DoubleLeftOutline,
          DoubleRightOutline,
          DownOutline,
          LeftOutline,
          LoadingOutline,
          RightOutline,
        ]),
        {
          provide: DocumentsService,
          useValue: {
            listDocuments,
            replaceDocumentFile,
            updateDocument,
            uploadDocument,
            deleteDocument,
          },
        },
        { provide: NzMessageService, useValue: message },
      ],
    });
    fixture = TestBed.createComponent(DocumentManagementComponent);
    component = fixture.componentInstance;
  });

  async function render(): Promise<void> {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  it('opens a PDF preview in the page and clears it on close', async () => {
    await render();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Hướng dẫn Python');
    expect(text).toContain('Backend Developer');
    expect(text).toContain('PDF');
    const previewButton = Array.from(fixture.nativeElement.querySelectorAll('button')).find(
      (button) => (button as HTMLButtonElement).textContent?.trim() === 'Xem',
    ) as HTMLButtonElement;
    previewButton.click();
    await render();
    expect(document.body.querySelector('iframe')?.getAttribute('src')).toBe(DOCUMENT.url);
    expect(
      document.body.querySelector('a[href="https://example.com/guide.pdf"]')?.getAttribute('rel'),
    ).toBe('noopener noreferrer');
    component['closePreview']();
    expect(component['previewDocument']()).toBeNull();
    expect(component['previewUrl']()).toBeNull();
    expect(component['safeUrl']('javascript:alert(1)')).toBeNull();
    expect(component['safeUrl']('//example.com/file')).toBeNull();
    expect(component['safeUrl']('/api/v1/uploads/training/file.pdf')).toBe(
      '/api/v1/uploads/training/file.pdf',
    );
  });

  it('uses image previews and gives unsupported files a fallback without embedding unsafe URLs', () => {
    component['openPreview']({ ...DOCUMENT, format: 'png' });
    expect(component['previewKind']()).toBe('image');
    component['openPreview']({ ...DOCUMENT, format: 'zip' });
    expect(component['previewKind']()).toBe('unsupported');
    expect(component['previewUrl']()).toBeNull();
    component['closePreview']();
    component['openPreview']({ ...DOCUMENT, url: 'javascript:alert(1)' });
    expect(component['previewDocument']()).toBeNull();
  });

  it('resets server pagination when filtering and cancels an older list response', () => {
    let cancelled = false;
    const old = new Observable<DocumentListResponse>(() => () => {
      cancelled = true;
    });
    listDocuments
      .mockReturnValueOnce(old)
      .mockReturnValueOnce(of({ items: [], total: 0, formats: ['pdf', 'docx'] }));
    component.ngOnInit();
    component['page'].set(3);
    component['setPositionFilter']('AI');
    expect(cancelled).toBe(true);
    expect(component['page']()).toBe(1);
    expect(listDocuments).toHaveBeenLastCalledWith(
      expect.objectContaining({ position: 'AI', skip: 0, limit: 10 }),
    );
    expect(component['formats']()).toEqual(['pdf', 'docx']);
  });

  it('shows a recoverable list failure instead of stale documents', () => {
    listDocuments
      .mockReturnValueOnce(throwError(() => ({ error: { detail: 'Không thể kết nối' } })))
      .mockReturnValueOnce(of({ items: [DOCUMENT], total: 1, formats: ['pdf'] }));
    component.ngOnInit();
    expect(component['documents']()).toEqual([]);
    expect(component['listError']()).toBe('Không thể kết nối');
    component['loadDocuments']();
    expect(component['documents']()).toEqual([DOCUMENT]);
    expect(component['listError']()).toBeNull();
  });

  it('debounces name search and sends only the latest term', () => {
    vi.useFakeTimers();
    try {
      component['onSearch']('Py');
      vi.advanceTimersByTime(200);
      expect(listDocuments).not.toHaveBeenCalled();
      component['onSearch']('Python');
      vi.advanceTimersByTime(300);
      expect(listDocuments).toHaveBeenCalledTimes(1);
      expect(listDocuments).toHaveBeenCalledWith(
        expect.objectContaining({ search: 'Python', skip: 0 }),
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it('moves back to the last available page after deleting the last document on a page', () => {
    listDocuments
      .mockReturnValueOnce(of({ items: [], total: 10, formats: ['pdf'] }))
      .mockReturnValueOnce(of({ items: [DOCUMENT], total: 10, formats: ['pdf'] }));
    component['page'].set(2);
    component['loadDocuments']();
    expect(component['page']()).toBe(1);
    expect(listDocuments).toHaveBeenCalledTimes(2);
    expect(component['documents']()).toEqual([DOCUMENT]);
  });

  it('edits metadata and keeps the modal open on failure so the admin can retry', () => {
    updateDocument
      .mockReturnValueOnce(throwError(() => ({ error: { detail: 'Tên không hợp lệ' } })))
      .mockReturnValueOnce(of(DOCUMENT));
    component['openEdit'](DOCUMENT);
    component['form'].patchValue({ title: 'Updated', positions: [] });
    component['saveDocument']();
    expect(component['editorOpen']()).toBe(true);
    expect(component['saveError']()).toBe('Tên không hợp lệ');
    expect(component['saving']()).toBe(false);
    component['saveDocument']();
    expect(updateDocument).toHaveBeenCalledWith(
      DOCUMENT.id,
      expect.objectContaining({ title: 'Updated', positions: [] }),
    );
    expect(component['editorOpen']()).toBe(false);
    expect(replaceDocumentFile).not.toHaveBeenCalled();
    expect(updateDocument).toHaveBeenLastCalledWith(DOCUMENT.id, {
      title: 'Updated',
      description: DOCUMENT.description,
      positions: [],
    });
  });

  it('requires a real file for creation and has no link source or editable URL controls', async () => {
    await render();
    component['openCreate']();
    component['form'].setValue({
      title: '  Hướng dẫn  ',
      description: '  Nội dung  ',
      positions: [],
    });
    component['saveDocument']();
    expect(uploadDocument).not.toHaveBeenCalled();
    expect(component['fileError']()).toContain('Vui lòng chọn');
    expect(Object.keys(component['form'].controls)).toEqual(['title', 'description', 'positions']);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(document.querySelector('input[formControlName="url"]')).toBeNull();
    expect(document.querySelector('input[name="document-source"]')).toBeNull();
    const file = new File(['guide'], 'guide.pdf', { type: 'application/pdf' });
    component['selectFile']({ target: { files: [file] } } as unknown as Event);
    expect(uploadDocument).not.toHaveBeenCalled();
    component['saveDocument']();
    expect(uploadDocument).toHaveBeenCalledWith(file, {
      title: 'Hướng dẫn',
      description: 'Nội dung',
      positions: [],
    });
  });

  it('rejects files above 4 MB and permits clearing an invalid replacement before a metadata-only edit', () => {
    component['openEdit'](DOCUMENT);
    const input = {
      files: [new File([new Uint8Array(4 * 1024 * 1024 + 1)], 'large.pdf')],
      value: 'large.pdf',
    };
    component['selectFile']({ target: input } as unknown as Event);
    component['saveDocument']();
    expect(component['fileError']()).toContain('4 MB');
    expect(updateDocument).not.toHaveBeenCalled();
    expect(replaceDocumentFile).not.toHaveBeenCalled();
    component['clearSelectedFile'](input as unknown as HTMLInputElement);
    component['saveDocument']();
    expect(updateDocument).toHaveBeenCalled();
    expect(replaceDocumentFile).not.toHaveBeenCalled();
  });

  it('replaces an existing file and metadata together and retains the editor on failure for retry', () => {
    replaceDocumentFile
      .mockReturnValueOnce(throwError(() => ({ error: { detail: 'Không lưu được tệp mới' } })))
      .mockReturnValueOnce(of(DOCUMENT));
    component['openEdit']({ ...DOCUMENT, usage_count: 3 });
    const file = new File(['replacement'], 'new.pdf', { type: 'application/pdf' });
    component['selectFile']({ target: { files: [file] } } as unknown as Event);
    component['form'].patchValue({ title: 'New guide', positions: ['AI'] });
    component['saveDocument']();
    expect(replaceDocumentFile).toHaveBeenCalledWith(DOCUMENT.id, file, {
      title: 'New guide',
      description: DOCUMENT.description,
      positions: ['AI'],
    });
    expect(updateDocument).not.toHaveBeenCalled();
    expect(component['saveError']()).toBe('Không lưu được tệp mới');
    expect(component['editorOpen']()).toBe(true);
    component['saveDocument']();
    expect(component['editorOpen']()).toBe(false);
  });

  it('blocks duplicate saves and closing the editor while upload is pending', () => {
    const pending = new Subject<LibraryDocument>();
    uploadDocument.mockReturnValue(pending);
    component['openCreate']();
    component['form'].patchValue({ title: 'Guide' });
    component['selectFile']({
      target: { files: [new File(['content'], 'guide.pdf')] },
    } as unknown as Event);
    component['saveDocument']();
    component['saveDocument']();
    component['closeEditor']();
    expect(uploadDocument).toHaveBeenCalledTimes(1);
    expect(component['editorOpen']()).toBe(true);
    pending.next(DOCUMENT);
    pending.complete();
    expect(component['editorOpen']()).toBe(false);
  });

  it('retries only unsaved files after a partial upload failure', () => {
    const first = new File(['first'], 'first.pdf');
    const second = new File(['second'], 'second.pdf');
    uploadDocument
      .mockReturnValueOnce(of(DOCUMENT))
      .mockReturnValueOnce(throwError(() => new Error('Upload failed')));
    component['openCreate']();
    component['selectFile']({ target: { files: [first, second] } } as unknown as Event);
    component['saveDocument']();
    expect(component['editorOpen']()).toBe(true);
    expect(component['selectedFiles']()).toEqual([second]);
    expect(uploadDocument).toHaveBeenNthCalledWith(
      1,
      first,
      expect.objectContaining({ title: 'first.pdf' }),
    );
    component['saveDocument']();
    expect(uploadDocument).toHaveBeenCalledTimes(3);
    expect(uploadDocument).toHaveBeenLastCalledWith(
      second,
      expect.objectContaining({ title: 'second.pdf' }),
    );
    expect(component['editorOpen']()).toBe(false);
  });

  it('does not delete documents in use and displays a backend conflict for a stale usage count', () => {
    component['deleteDocument']({ ...DOCUMENT, usage_count: 2 });
    expect(deleteDocument).not.toHaveBeenCalled();
    deleteDocument
      .mockReturnValueOnce(
        throwError(() => ({ status: 409, error: { detail: 'Tài liệu đang được sử dụng' } })),
      )
      .mockReturnValueOnce(of(undefined));
    component['deleteDocument'](DOCUMENT);
    expect(message.error).toHaveBeenCalledWith('Tài liệu đang được sử dụng');
    expect(component['deletingId']()).toBeNull();
    component['deleteDocument'](DOCUMENT);
    expect(listDocuments).toHaveBeenCalled();
  });
});
