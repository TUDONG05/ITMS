import { TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';
import {
  DocumentsService,
  DocumentListResponse,
  LibraryDocument,
} from '../../core/api/documents.service';
import { DocumentPickerComponent } from './document-picker.component';

const doc = (id: string): LibraryDocument => ({
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
});
const result = (id: string): DocumentListResponse => ({
  items: [doc(id)],
  total: 21,
  formats: ['pdf'],
});

describe('Document picker', () => {
  const service = { listDocuments: vi.fn(() => of(result('first'))) };
  beforeEach(async () => {
    vi.clearAllMocks();
    service.listDocuments.mockReturnValue(of(result('first')));
    await TestBed.configureTestingModule({
      imports: [DocumentPickerComponent],
      providers: [{ provide: DocumentsService, useValue: service }],
    })
      .overrideComponent(DocumentPickerComponent, { set: { template: '' } })
      .compileComponents();
  });

  it('keeps selected items across pages and confirms only on explicit save', () => {
    const fixture = TestBed.createComponent(DocumentPickerComponent);
    fixture.componentRef.setInput('selectedDocuments', [doc('existing')]);
    fixture.componentRef.setInput('visible', true);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    const confirmed = vi.fn();
    component.confirmed.subscribe(confirmed);
    component['toggle'](doc('first'));
    component['page'] = 2;
    service.listDocuments.mockReturnValue(of(result('second')));
    component['load']();
    component['toggle'](doc('second'));
    expect(confirmed).not.toHaveBeenCalled();
    expect(service.listDocuments).toHaveBeenLastCalledWith(
      expect.objectContaining({ skip: 10, limit: 10 }),
    );
    component['confirm']();
    expect(confirmed.mock.calls[0][0].map((item: LibraryDocument) => item.id)).toEqual([
      'existing',
      'first',
      'second',
    ]);
    fixture.destroy();
  });

  it('does not change the parent selection when a draft item is removed', () => {
    const selected = [doc('existing')];
    const fixture = TestBed.createComponent(DocumentPickerComponent);
    fixture.componentRef.setInput('selectedDocuments', selected);
    fixture.componentRef.setInput('visible', true);
    fixture.detectChanges();
    fixture.componentInstance['toggle'](doc('existing'));
    expect(selected).toHaveLength(1);
    expect(fixture.componentInstance['draft']().size).toBe(0);
    fixture.destroy();
  });

  it('retains current selections after load failure and supports retry', () => {
    service.listDocuments.mockReturnValue(throwError(() => new Error('Unavailable')));
    const fixture = TestBed.createComponent(DocumentPickerComponent);
    fixture.componentRef.setInput('selectedDocuments', [doc('existing')]);
    fixture.componentRef.setInput('visible', true);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    expect(component['error']()).toBe(true);
    expect(component['draft']().has('existing')).toBe(true);
    service.listDocuments.mockReturnValue(of(result('retry')));
    component['load']();
    expect(component['error']()).toBe(false);
    expect(component['items']()[0].id).toBe('retry');
    fixture.destroy();
  });

  it('cancels pending requests on close and ignores stale results', () => {
    const pending = new Subject<DocumentListResponse>();
    service.listDocuments.mockReturnValue(pending);
    const fixture = TestBed.createComponent(DocumentPickerComponent);
    fixture.componentRef.setInput('visible', true);
    fixture.detectChanges();
    fixture.componentRef.setInput('visible', false);
    fixture.detectChanges();
    pending.next(result('stale'));
    expect(fixture.componentInstance['items']()).toEqual([]);
    fixture.destroy();
  });
});
