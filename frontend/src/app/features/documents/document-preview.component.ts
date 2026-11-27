import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { DocxPreviewComponent } from './docx-preview.component';

export interface PreviewDocument {
  title: string;
  url: string;
  format: string;
}

export function safeDocumentUrl(value: string): string | null {
  const url = value.trim();
  if (!url || /\s/.test(url) || url.includes('\\')) return null;
  try {
    let decoded = url;
    for (let count = 0; count < 3; count++) decoded = decodeURIComponent(decoded);
    if (
      decoded.includes('\\') ||
      Array.from(decoded).some((char) => char.charCodeAt(0) < 32) ||
      /(?:^|\/)\.{1,2}(?:\/|$)/.test(decoded)
    )
      return null;
    if (/^\/api\/v1\/uploads\/training\/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9]+)*$/.test(url)) return url;
    const parsed = new URL(url);
    return ['http:', 'https:'].includes(parsed.protocol) &&
      parsed.hostname &&
      !parsed.username &&
      !parsed.password
      ? url
      : null;
  } catch {
    return null;
  }
}

@Component({
  selector: 'app-document-preview',
  imports: [NzButtonModule, NzEmptyModule, NzModalModule, DocxPreviewComponent],
  template: `
    @if (previewDocument(); as document) {
      <nz-modal
        [nzVisible]="true"
        [nzTitle]="document.title"
        (nzOnCancel)="closed.emit()"
        [nzFooter]="previewFooter"
        nzWidth="min(1100px, calc(100vw - 24px))"
      >
        <ng-container *nzModalContent>
          @switch (previewKind()) {
            @case ('docx') {
              <app-docx-preview [url]="document.url" />
            }
            @case ('image') {
              <img class="document-preview-image" [src]="document.url" [alt]="document.title" />
            }
            @case ('video') {
              <video
                class="document-preview-media"
                [src]="document.url"
                controls
                preload="metadata"
              ></video>
            }
            @case ('audio') {
              <audio
                class="document-preview-media"
                [src]="document.url"
                controls
                preload="metadata"
              ></audio>
            }
            @case ('frame') {
              <iframe
                class="document-preview-frame"
                [src]="previewUrl()"
                [title]="document.title"
                referrerpolicy="no-referrer"
              ></iframe>
            }
            @default {
              <nz-empty
                nzNotFoundContent="Định dạng này chưa hỗ trợ xem trước. Vui lòng tải file để xem nội dung."
              />
            }
          }
        </ng-container>
        <ng-template #previewFooter>
          <a nz-button [href]="document.url" target="_blank" rel="noopener noreferrer"
            >Mở file gốc</a
          >
          <button nz-button type="button" (click)="closed.emit()">Đóng</button>
        </ng-template>
      </nz-modal>
    }
  `,
  styles: `
    .document-preview-frame {
      width: 100%;
      height: 70vh;
      border: 0;
    }
    .document-preview-image {
      display: block;
      max-width: 100%;
      max-height: 70vh;
      margin: auto;
      object-fit: contain;
    }
    .document-preview-media {
      width: 100%;
      max-height: 70vh;
    }
  `,
})
export class DocumentPreviewComponent {
  @Output() readonly closed = new EventEmitter<void>();
  private readonly sanitizer = inject(DomSanitizer);
  protected readonly previewDocument = signal<PreviewDocument | null>(null);
  protected readonly previewKind = signal('unsupported');
  protected readonly previewUrl = signal<SafeResourceUrl | null>(null);

  @Input({ required: true }) set document(document: PreviewDocument | null) {
    this.previewDocument.set(null);
    if (!document) return;
    const url = safeDocumentUrl(document.url);
    if (!url) return;
    const format = document.format.toLowerCase();
    let kind = 'unsupported';
    let frameUrl = url;
    if (format === 'docx') kind = 'docx';
    else if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(format)) kind = 'image';
    else if (['mp4', 'webm'].includes(format)) kind = 'video';
    else if (['mp3', 'wav'].includes(format)) kind = 'audio';
    else if (['pdf', 'txt', 'md', 'csv'].includes(format)) kind = 'frame';
    else if (
      ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(format) &&
      url.startsWith('https://')
    ) {
      kind = 'frame';
      frameUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(url)}`;
    }
    this.previewKind.set(kind);
    this.previewUrl.set(
      kind === 'frame' ? this.sanitizer.bypassSecurityTrustResourceUrl(frameUrl) : null,
    );
    this.previewDocument.set({ ...document, url });
  }
}
