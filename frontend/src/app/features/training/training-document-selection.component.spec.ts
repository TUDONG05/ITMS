import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { NzMessageService } from 'ng-zorro-antd/message';
import { TrainingManagementComponent } from './training-management.component';
import { TrainingService, LearningContent } from '../../core/api/training.service';
import { LibraryDocument } from '../../core/api/documents.service';

function document(id: string): LibraryDocument {
  return {
    id,
    title: id,
    url: `https://example.com/${id}.pdf`,
    format: 'pdf',
    positions: [],
    description: null,
    original_filename: null,
    size_bytes: null,
    created_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    usage_count: 0,
  };
}

function content(): LearningContent {
  const doc = document('original');
  return {
    id: 'content-1',
    phase_id: 'phase-1',
    title: 'A lesson',
    type: 'LESSON',
    description: null,
    content: null,
    resource_url: JSON.stringify([doc.url, 'https://example.com/manual.pdf']),
    document_ids: [doc.id],
    documents: [doc],
    order_no: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}

describe('Training document library selection', () => {
  const api = {
    createContent: vi.fn(() => of(content())),
    updateContent: vi.fn(() => of(content())),
    uploadFiles: vi.fn(() =>
      of({ urls: [document('upload').url], documents: [document('upload')] }),
    ),
  };
  beforeEach(async () => {
    vi.clearAllMocks();
    await TestBed.configureTestingModule({
      imports: [TrainingManagementComponent],
      providers: [
        { provide: TrainingService, useValue: api },
        { provide: NzMessageService, useValue: { success: vi.fn(), error: vi.fn() } },
      ],
    })
      .overrideComponent(TrainingManagementComponent, { set: { template: '' } })
      .compileComponents();
  });

  it('uses the filename as the title without uploading or entering content', () => {
    const fixture = TestBed.createComponent(TrainingManagementComponent);
    const c = fixture.componentInstance;
    c.openCreateContentModal('phase-1');
    c.confirmLibraryDocuments([{ ...document('shared'), original_filename: 'Backend.docx' }]);
    expect(api.uploadFiles).not.toHaveBeenCalled();
    expect(api.createContent).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Backend.docx',
        type: 'DOCUMENT',
        description: null,
        content: null,
        document_ids: ['shared'],
        resource_url: null,
        phase_id: 'phase-1',
      }),
    );
    fixture.destroy();
  });

  it('requires a document selection', () => {
    const fixture = TestBed.createComponent(TrainingManagementComponent);
    fixture.componentInstance.openCreateContentModal('phase-1');
    expect(fixture.componentInstance['isDocumentPickerOpen']()).toBe(true);
    fixture.componentInstance.saveContent();
    expect(api.createContent).not.toHaveBeenCalled();
    fixture.destroy();
  });

  it('creates a separate content for each selected file', () => {
    const fixture = TestBed.createComponent(TrainingManagementComponent);
    const c = fixture.componentInstance;
    c.openCreateContentModal('phase-1');
    c.confirmLibraryDocuments([document('first'), document('second')]);
    expect(api.createContent).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ title: 'first', document_ids: ['first'], order_no: 1 }),
    );
    expect(api.createContent).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ title: 'second', document_ids: ['second'], order_no: 2 }),
    );
    fixture.destroy();
  });

  it('updates a selected file while keeping existing manual resources', () => {
    const fixture = TestBed.createComponent(TrainingManagementComponent);
    const c = fixture.componentInstance;
    c.openEditContentModal(content());
    c.confirmLibraryDocuments([document('replacement')]);
    expect(api.updateContent).toHaveBeenCalledWith(
      'content-1',
      expect.objectContaining({
        title: 'replacement',
        type: 'DOCUMENT',
        document_ids: ['replacement'],
        resource_url: JSON.stringify(['https://example.com/manual.pdf']),
      }),
    );
    fixture.destroy();
  });

  it('retries only the files that failed to save', () => {
    api.createContent
      .mockReturnValueOnce(of(content()))
      .mockReturnValueOnce(throwError(() => new Error('Failed')));
    const fixture = TestBed.createComponent(TrainingManagementComponent);
    const c = fixture.componentInstance;
    c.openCreateContentModal('phase-1');
    c.confirmLibraryDocuments([document('first'), document('second')]);
    expect(c['selectedLibraryDocuments']().map((d) => d.id)).toEqual(['second']);
    c.saveContent();
    expect(api.createContent).toHaveBeenCalledTimes(3);
    expect(api.createContent).toHaveBeenLastCalledWith(
      expect.objectContaining({ document_ids: ['second'] }),
    );
    fixture.destroy();
  });
});
