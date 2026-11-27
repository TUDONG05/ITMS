import { AfterViewInit, Component, DestroyRef, Input, inject, signal } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Component({
  selector: 'app-docx-preview',
  standalone: true,
  template: `
    @if (loading()) {
      <p role="status">Đang tải nội dung DOCX…</p>
    }
    @if (error()) {
      <p role="alert">Không thể xem trước file DOCX. Vui lòng mở file gốc để xem nội dung.</p>
      <button type="button" (click)="load()">Thử lại</button>
    }
    @if (content(); as html) {
      <iframe [srcdoc]="html" sandbox="" title="Nội dung tài liệu DOCX"></iframe>
    }
  `,
  styles: `
    iframe {
      width: 100%;
      height: 70vh;
      border: 0;
    }
  `,
})
export class DocxPreviewComponent implements AfterViewInit {
  @Input({ required: true }) url = '';
  private readonly sanitizer = inject(DomSanitizer);
  private readonly destroyRef = inject(DestroyRef);
  private request?: AbortController;
  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly content = signal<SafeHtml | null>(null);

  constructor() {
    this.destroyRef.onDestroy(() => this.request?.abort());
  }

  ngAfterViewInit(): void {
    void this.load();
  }

  protected async load(): Promise<void> {
    this.request?.abort();
    const controller = new AbortController();
    this.request = controller;
    this.loading.set(true);
    this.error.set(false);
    this.content.set(null);
    try {
      const response = await fetch(this.url, {
        signal: controller.signal,
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error('Cannot load document');
      const data = await response.arrayBuffer();
      const { renderAsync } = await import('docx-preview');
      if (controller.signal.aborted) return;
      const container = document.createElement('div');
      await renderAsync(data, container, undefined, {
        useBase64URL: true,
        renderAltChunks: false,
        ignoreWidth: true,
        ignoreHeight: true,
      });
      if (controller.signal.aborted) return;
      // The generated document is isolated in a scriptless, opaque-origin iframe.
      const policy = "default-src 'none'; img-src data:; font-src data:; style-src 'unsafe-inline'";
      this.content.set(
        this.sanitizer.bypassSecurityTrustHtml(
          `<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="${policy}"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>${container.innerHTML}</body></html>`,
        ),
      );
    } catch {
      if (!controller.signal.aborted) this.error.set(true);
    } finally {
      if (!controller.signal.aborted) this.loading.set(false);
    }
  }
}
