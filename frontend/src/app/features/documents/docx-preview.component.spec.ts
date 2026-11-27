import { TestBed } from '@angular/core/testing';
import JSZip from 'jszip';
import { DocxPreviewComponent } from './docx-preview.component';

describe('DocxPreviewComponent', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('renders a local DOCX in an isolated frame without using an Office service', async () => {
    const zip = new JSZip();
    zip.file(
      '_rels/.rels',
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
    );
    zip.file(
      '[Content_Types].xml',
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
    );
    zip.file(
      'word/document.xml',
      '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Thông tin thực tập</w:t></w:r></w:p></w:body></w:document>',
    );
    const data = await zip.generateAsync({ type: 'arraybuffer' });
    const fetchFile = vi.fn().mockResolvedValue({ ok: true, arrayBuffer: async () => data });
    vi.stubGlobal('fetch', fetchFile);
    const fixture = TestBed.createComponent(DocxPreviewComponent);
    fixture.componentRef.setInput('url', '/api/v1/uploads/training/test.docx');
    fixture.detectChanges();
    await fixture.componentInstance['load']();
    expect(fixture.componentInstance['error']()).toBe(false);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fetchFile).toHaveBeenCalledWith(
      '/api/v1/uploads/training/test.docx',
      expect.objectContaining({ credentials: 'same-origin' }),
    );
    const frame = fixture.nativeElement.querySelector('iframe');
    expect(frame?.getAttribute('srcdoc')).toContain('Thông tin thực tập');
    expect(frame?.getAttribute('sandbox')).toBe('');
    fixture.destroy();
  });

  it('shows an error and can retry an unreadable document', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network')));
    const fixture = TestBed.createComponent(DocxPreviewComponent);
    await fixture.componentInstance['load']();
    expect(fixture.componentInstance['error']()).toBe(true);
    expect(fixture.componentInstance['loading']()).toBe(false);
    expect(fixture.componentInstance['content']()).toBeNull();
    fixture.destroy();
  });

  it('aborts loading when the preview closes', async () => {
    let signal: AbortSignal | undefined;
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url, options) => {
        signal = options.signal;
        return new Promise(() => undefined);
      }),
    );
    const fixture = TestBed.createComponent(DocxPreviewComponent);
    void fixture.componentInstance['load']();
    fixture.destroy();
    expect(signal?.aborted).toBe(true);
  });
});
