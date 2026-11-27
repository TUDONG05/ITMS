import { DatePipe, DecimalPipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';
import {
  Subject,
  Subscription,
  concatMap,
  debounceTime,
  distinctUntilChanged,
  from,
  tap,
} from 'rxjs';

import { DocumentsService, LibraryDocument } from '../../core/api/documents.service';
import { DocumentPreviewComponent, safeDocumentUrl } from './document-preview.component';
import {
  INTERNSHIP_POSITIONS,
  InternshipPosition,
  internshipPositionLabel,
} from '../../core/api/internship.service';

const MAX_FILE_BYTES = 4 * 1024 * 1024;

function errorMessage(error: unknown, fallback: string): string {
  const body = (error as { error?: { error?: { message?: unknown }; detail?: unknown } })?.error;
  if (typeof body?.error?.message === 'string') return body.error.message;
  if (typeof body?.detail === 'string') return body.detail;
  return fallback;
}

@Component({
  selector: 'app-document-management',
  standalone: true,
  imports: [
    DocumentPreviewComponent,
    DatePipe,
    DecimalPipe,
    FormsModule,
    ReactiveFormsModule,
    NzButtonModule,
    NzCardModule,
    NzEmptyModule,
    NzFormModule,
    NzInputModule,
    NzModalModule,
    NzPopconfirmModule,
    NzSelectModule,
    NzTableModule,
    NzTagModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="feature-page-layout document-library">
      <div class="feature-page-header">
        <h1 class="feature-page-title">Quản lý tài liệu</h1>
      </div>
      <nz-card [nzBordered]="false" class="library-card">
        <div class="library-toolbar">
          <div class="search-control">
            <label for="document-search">Tên tài liệu</label>
            <input
              nz-input
              id="document-search"
              type="search"
              placeholder="Tìm theo tên tài liệu"
              [ngModel]="search"
              (ngModelChange)="onSearch($event)"
            />
          </div>
          <div class="filter-control">
            <label for="document-position">Vị trí thực tập</label>
            <nz-select
              nzId="document-position"
              nzAllowClear
              nzPlaceHolder="Tất cả vị trí"
              [ngModel]="positionFilter"
              (ngModelChange)="setPositionFilter($event)"
            >
              @for (position of positionOptions; track position.value) {
                <nz-option [nzValue]="position.value" [nzLabel]="position.label" />
              }
            </nz-select>
          </div>
          <div class="filter-control format-control">
            <label for="document-format">Định dạng</label>
            <nz-select
              nzId="document-format"
              nzAllowClear
              nzPlaceHolder="Tất cả định dạng"
              [ngModel]="formatFilter"
              (ngModelChange)="setFormatFilter($event)"
            >
              @for (format of formats(); track format) {
                <nz-option [nzValue]="format" [nzLabel]="formatLabel(format)" />
              }
            </nz-select>
          </div>
          <button
            class="add-document"
            nz-button
            nzType="primary"
            type="button"
            (click)="openCreate()"
          >
            Thêm tài liệu
          </button>
        </div>

        @if (listError()) {
          <div class="error-state" role="alert">
            <p>{{ listError() }}</p>
            <button nz-button type="button" (click)="loadDocuments()">Thử lại</button>
          </div>
        }
        <nz-table
          #documentTable
          class="document-table"
          [nzData]="documents()"
          [nzLoading]="loading()"
          [nzFrontPagination]="false"
          [nzTotal]="total()"
          [nzPageIndex]="page()"
          [nzPageSize]="pageSize"
          (nzPageIndexChange)="changePage($event)"
          nzSize="middle"
          [nzNoResult]="emptyState"
        >
          <thead>
            <tr>
              <th>Tài liệu</th>
              <th>Định dạng</th>
              <th>Vị trí thực tập</th>
              <th>Cập nhật</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            @for (document of documentTable.data; track document.id) {
              <tr>
                <td data-label="Tài liệu">
                  <strong>{{ document.title }}</strong>
                  @if (document.description) {
                    <p class="document-description">{{ document.description }}</p>
                  }
                  @if (document.original_filename) {
                    <span class="file-details"
                      >{{ document.original_filename }}
                      @if (document.size_bytes !== null) {
                        · {{ document.size_bytes / 1024 | number: '1.0-1' }} KB
                      }
                    </span>
                  }
                </td>
                <td data-label="Định dạng">
                  <nz-tag>{{ formatLabel(document.format) }}</nz-tag>
                </td>
                <td data-label="Vị trí thực tập">
                  <div class="position-tags">
                    @for (position of document.positions; track position) {
                      <nz-tag>{{ positionLabel(position) }}</nz-tag>
                    } @empty {
                      <span>Dùng chung</span>
                    }
                  </div>
                </td>
                <td data-label="Cập nhật">{{ document.updated_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                <td data-label="Thao tác">
                  <div class="row-actions">
                    @if (safeUrl(document.url); as url) {
                      <button nz-button nzType="link" type="button" (click)="openPreview(document)">
                        Xem
                      </button>
                    }
                    <button nz-button nzType="link" type="button" (click)="openEdit(document)">
                      Sửa
                    </button>
                    <button
                      nz-button
                      nzType="link"
                      nzDanger
                      type="button"
                      nz-popconfirm
                      nzPopconfirmTitle="Xóa tài liệu này?"
                      nzOkText="Xóa"
                      nzCancelText="Hủy"
                      (nzOnConfirm)="deleteDocument(document)"
                      [disabled]="document.usage_count > 0 || deletingId() !== null"
                      [nzLoading]="deletingId() === document.id"
                      [attr.title]="
                        document.usage_count > 0
                          ? 'Tài liệu đang được sử dụng trong lộ trình'
                          : null
                      "
                    >
                      Xóa
                    </button>
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </nz-table>
        <ng-template #emptyState>
          @if (!listError()) {
            <nz-empty nzNotFoundContent="Không có tài liệu phù hợp." />
          }
        </ng-template>
      </nz-card>
    </div>

    <app-document-preview [document]="previewDocument()" (closed)="closePreview()" />
    @if (editorOpen()) {
      <nz-modal
        [nzVisible]="editorOpen()"
        [nzTitle]="editingDocument() ? 'Chỉnh sửa tài liệu' : 'Thêm tài liệu'"
        (nzOnCancel)="closeEditor()"
        [nzFooter]="editorFooter"
        [nzClosable]="!saving()"
        [nzMaskClosable]="!saving()"
        nzWidth="min(600px, calc(100vw - 24px))"
      >
        <ng-container *nzModalContent>
          <form nz-form nzLayout="vertical" [formGroup]="form" class="document-form">
            <nz-form-item>
              <nz-form-label [nzRequired]="!editingDocument()" nzFor="library-document-file">{{
                editingDocument() ? 'Thay tệp tài liệu' : 'Tệp tài liệu'
              }}</nz-form-label>
              <nz-form-control>
                @if (editingDocument(); as current) {
                  <p class="current-file">
                    Tệp hiện tại:
                    @if (safeUrl(current.url); as url) {
                      <a [href]="url" target="_blank" rel="noopener noreferrer">{{
                        current.original_filename || current.title
                      }}</a>
                    } @else {
                      {{ current.original_filename || current.title }}
                    }
                  </p>
                }
                <input
                  #documentFile
                  id="library-document-file"
                  type="file"
                  [multiple]="!editingDocument()"
                  hidden
                  [disabled]="saving()"
                  (change)="selectFile($event)"
                />
                <button
                  type="button"
                  class="document-drop-zone"
                  [class.drag-over]="dragOver()"
                  [disabled]="saving()"
                  (click)="documentFile.click()"
                  (dragover)="onDragOver($event)"
                  (dragleave)="dragOver.set(false)"
                  (drop)="onDrop($event, documentFile)"
                >
                  <strong>{{
                    editingDocument() ? 'Kéo thả tệp mới vào đây' : 'Kéo thả tệp vào đây'
                  }}</strong>
                  <span>hoặc nhấp để chọn từ máy tính</span>
                </button>
                <p class="field-hint">Dung lượng tối đa 4 MB mỗi tệp.</p>
                @if (selectedFiles().length === 1) {
                  <p class="current-file">{{ selectedFile()?.name }}</p>
                }
                @if (selectedFiles().length > 1) {
                  <ul>
                    @for (file of selectedFiles(); track $index) {
                      <li>{{ file.name }}</li>
                    }
                  </ul>
                  <p class="field-hint">
                    Tên tài liệu lấy theo tên tệp. Mô tả và vị trí áp dụng cho cả lượt.
                  </p>
                }
                @if (editingDocument()) {
                  <p class="field-hint">Không chọn tệp mới nếu chỉ chỉnh sửa thông tin tài liệu.</p>
                }
                @if (selectedFile() || fileError()) {
                  <button
                    nz-button
                    nzType="link"
                    type="button"
                    [disabled]="saving()"
                    (click)="clearSelectedFile(documentFile)"
                  >
                    Bỏ tệp vừa chọn
                  </button>
                }
                @if (fileError()) {
                  <p class="field-error" role="alert">{{ fileError() }}</p>
                }
              </nz-form-control>
            </nz-form-item>
            @if (selectedFiles().length <= 1) {
              <nz-form-item>
                <nz-form-label nzRequired nzFor="library-document-title"
                  >Tên tài liệu</nz-form-label
                >
                <nz-form-control nzErrorTip="Nhập tên tài liệu (tối đa 255 ký tự).">
                  <input
                    nz-input
                    id="library-document-title"
                    formControlName="title"
                    maxlength="255"
                  />
                </nz-form-control>
              </nz-form-item>
            }

            <nz-form-item>
              <nz-form-label nzFor="library-document-description">Mô tả</nz-form-label>
              <nz-form-control nzErrorTip="Mô tả tối đa 10000 ký tự.">
                <textarea
                  nz-input
                  id="library-document-description"
                  formControlName="description"
                  rows="3"
                  maxlength="10000"
                ></textarea>
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label nzFor="library-document-positions">Vị trí thực tập</nz-form-label>
              <nz-form-control>
                <nz-select
                  nzId="library-document-positions"
                  nzMode="multiple"
                  nzPlaceHolder="Dùng chung cho mọi vị trí"
                  formControlName="positions"
                  nzAllowClear
                >
                  @for (position of positionOptions; track position.value) {
                    <nz-option [nzValue]="position.value" [nzLabel]="position.label" />
                  }
                </nz-select>
                <p class="field-hint">Không chọn vị trí nếu tài liệu dùng chung.</p>
              </nz-form-control>
            </nz-form-item>
            @if (saveError()) {
              <p class="field-error" role="alert">{{ saveError() }}</p>
            }
          </form>
        </ng-container>
        <ng-template #editorFooter>
          <button nz-button type="button" [disabled]="saving()" (click)="closeEditor()">Hủy</button>
          <button
            nz-button
            nzType="primary"
            type="button"
            [nzLoading]="saving()"
            [disabled]="
              saving() || form.invalid || (!editingDocument() && !selectedFile()) || !!fileError()
            "
            (click)="saveDocument()"
          >
            Lưu tài liệu
          </button>
        </ng-template>
      </nz-modal>
    }
  `,
  styles: [
    `
      :host {
        display: block;
        min-width: 0;
      }
      .feature-page-header {
        gap: 16px;
        flex-wrap: wrap;
      }
      .library-card {
        border-radius: 8px;
      }
      .library-toolbar {
        display: flex;
        gap: 16px;
        align-items: flex-end;
        flex-wrap: wrap;
        margin-bottom: 20px;
      }
      .search-control {
        flex: 1 1 240px;
      }
      .filter-control {
        flex: 0 1 240px;
        min-width: 180px;
      }
      .format-control {
        flex-basis: 180px;
      }
      .add-document {
        flex: 0 0 auto;
      }
      .library-toolbar label {
        display: block;
        margin-bottom: 6px;
        color: #434343;
      }
      nz-select {
        width: 100%;
      }
      button,
      input[nz-input],
      .file-input {
        border-radius: 4px;
      }
      .current-file {
        overflow-wrap: anywhere;
      }
      .document-drop-zone {
        display: grid;
        place-content: center;
        gap: 8px;
        width: 100%;
        min-height: 150px;
        padding: 20px;
        border: 1px dashed #91caff;
        border-radius: 8px;
        background: #f5faff;
        color: #0958d9;
        cursor: pointer;
      }
      .document-drop-zone:hover,
      .document-drop-zone.drag-over {
        border-color: #1677ff;
        background: #e6f4ff;
      }
      .document-drop-zone:disabled {
        opacity: 0.65;
        cursor: default;
      }
      @media (max-width: 767px) {
        .search-control,
        .filter-control {
          flex: 1 1 100%;
          min-width: 0;
        }
        input[nz-input],
        button,
        .row-actions a {
          min-height: 44px;
        }
        .row-actions a {
          display: inline-flex;
          align-items: center;
        }
        :host ::ng-deep .document-table .ant-table-thead {
          display: none;
        }
        :host ::ng-deep .document-table .ant-table-tbody > tr {
          display: block;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          margin-bottom: 16px;
          padding: 8px 12px;
        }
        :host ::ng-deep .document-table .ant-table-tbody > tr > td {
          display: grid;
          grid-template-columns: 110px minmax(0, 1fr);
          gap: 8px;
          padding: 10px 0;
          border-bottom: 0;
        }
        :host ::ng-deep .document-table td[data-label]::before {
          content: attr(data-label);
          color: #595959;
        }
        :host ::ng-deep .document-table td:first-child {
          display: block !important;
        }
        :host ::ng-deep .document-table td:first-child::before {
          display: none;
        }
        :host ::ng-deep .document-table td:not([data-label]) {
          display: block !important;
        }
      }
    `,
  ],
})
export class DocumentManagementComponent implements OnInit {
  protected readonly previewDocument = signal<LibraryDocument | null>(null);

  protected openPreview(document: LibraryDocument): void {
    if (safeDocumentUrl(document.url)) this.previewDocument.set(document);
  }

  protected closePreview(): void {
    this.previewDocument.set(null);
  }
  private readonly documentsService = inject(DocumentsService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly message = inject(NzMessageService);
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly searchChanges = new Subject<string>();
  private listRequest?: Subscription;
  protected readonly positionOptions = INTERNSHIP_POSITIONS;
  protected readonly positionLabel = internshipPositionLabel;
  protected readonly safeUrl = safeDocumentUrl;
  protected readonly documents = signal<LibraryDocument[]>([]);
  protected readonly total = signal(0);
  protected readonly formats = signal<string[]>([]);
  protected readonly loading = signal(true);
  protected readonly listError = signal<string | null>(null);
  protected readonly page = signal(1);
  protected readonly pageSize = 10;
  protected search = '';
  protected positionFilter: InternshipPosition | null = null;
  protected formatFilter: string | null = null;
  protected readonly editorOpen = signal(false);
  protected readonly editingDocument = signal<LibraryDocument | null>(null);
  protected readonly selectedFiles = signal<File[]>([]);
  protected readonly dragOver = signal(false);
  protected selectedFile(): File | null {
    return this.selectedFiles()[0] ?? null;
  }
  protected readonly fileError = signal<string | null>(null);
  protected readonly saving = signal(false);
  protected readonly saveError = signal<string | null>(null);
  protected readonly deletingId = signal<string | null>(null);
  protected readonly form = this.fb.group({
    title: ['', [Validators.required, Validators.pattern(/\S/), Validators.maxLength(255)]],
    description: ['', Validators.maxLength(10000)],
    positions: [[] as InternshipPosition[]],
  });

  constructor() {
    this.searchChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.loadDocuments(true));
  }

  ngOnInit(): void {
    this.loadDocuments();
  }

  protected loadDocuments(resetPage = false): void {
    if (resetPage) this.page.set(1);
    this.listRequest?.unsubscribe();
    this.loading.set(true);
    this.listError.set(null);
    this.listRequest = this.documentsService
      .listDocuments({
        search: this.search,
        position: this.positionFilter,
        format: this.formatFilter,
        skip: (this.page() - 1) * this.pageSize,
        limit: this.pageSize,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          const lastPage = Math.max(1, Math.ceil(response.total / this.pageSize));
          if (!response.items.length && this.page() > lastPage) {
            this.page.set(lastPage);
            this.loadDocuments();
            return;
          }
          this.documents.set(response.items);
          this.total.set(response.total);
          this.formats.set(response.formats);
          this.loading.set(false);
        },
        error: (error) => {
          this.documents.set([]);
          this.total.set(0);
          this.listError.set(
            errorMessage(error, 'Không thể tải danh sách tài liệu. Vui lòng thử lại.'),
          );
          this.loading.set(false);
        },
      });
  }

  protected onSearch(value: string): void {
    this.search = value;
    this.searchChanges.next(value);
  }
  protected setPositionFilter(value: InternshipPosition | null): void {
    this.positionFilter = value ?? null;
    this.loadDocuments(true);
  }
  protected setFormatFilter(value: string | null): void {
    this.formatFilter = value ?? null;
    this.loadDocuments(true);
  }
  protected changePage(page: number): void {
    if (page !== this.page()) {
      this.page.set(page);
      this.loadDocuments();
    }
  }
  protected formatLabel(format: string): string {
    return format.toUpperCase();
  }

  protected openCreate(): void {
    this.editingDocument.set(null);
    this.form.reset({ title: '', description: '', positions: [] });
    this.selectedFiles.set([]);
    this.fileError.set(null);
    this.saveError.set(null);
    this.editorOpen.set(true);
  }

  protected openEdit(document: LibraryDocument): void {
    this.editingDocument.set(document);
    this.form.reset({
      title: document.title,
      description: document.description ?? '',
      positions: [...document.positions],
    });
    this.selectedFiles.set([]);
    this.fileError.set(null);
    this.saveError.set(null);
    this.editorOpen.set(true);
  }

  protected selectFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.setFiles(Array.from(input.files ?? []));
    input.value = '';
  }

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
    if (!this.saving()) this.dragOver.set(true);
  }

  protected onDrop(event: DragEvent, input: HTMLInputElement): void {
    event.preventDefault();
    this.dragOver.set(false);
    const files = Array.from(event.dataTransfer?.files ?? []);
    if (this.saving() || !files.length) return;
    input.value = '';
    this.setFiles(files);
  }

  private setFiles(files: File[]): void {
    if (this.saving()) return;
    const file = files[0];
    this.selectedFiles.set([]);
    this.fileError.set(null);
    if (!file) return;
    if (this.editingDocument() && files.length > 1) {
      this.fileError.set('Chỉ chọn một tệp khi thay thế tài liệu.');
      return;
    }
    const invalid = files.find((item) => !item.size || item.size > MAX_FILE_BYTES);
    if (invalid) {
      this.fileError.set(
        !invalid.size
          ? 'Tệp tài liệu không được rỗng.'
          : 'Dung lượng tệp không được vượt quá 4 MB.',
      );
      return;
    }
    this.selectedFiles.set(files);
    if (files.length > 1 || !this.form.controls.title.value.trim()) {
      this.form.controls.title.setValue(
        (files.length > 1 ? file.name : file.name.replace(/\.[^.]+$/, '') || file.name).slice(
          0,
          255,
        ),
      );
    }
  }

  protected clearSelectedFile(input: HTMLInputElement): void {
    this.selectedFiles.set([]);
    this.fileError.set(null);
    input.value = '';
  }

  protected closeEditor(): void {
    if (!this.saving()) this.editorOpen.set(false);
  }

  protected saveDocument(): void {
    if (this.saving() || this.fileError()) return;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const editing = this.editingDocument();
    const file = this.selectedFile();
    if (!editing && !file) {
      this.fileError.set('Vui lòng chọn một tệp tài liệu.');
      return;
    }
    const value = this.form.getRawValue();
    const payload = {
      title: value.title.trim(),
      description: value.description.trim() || null,
      positions: value.positions ?? [],
    };
    const files = this.selectedFiles();
    const request = editing
      ? file
        ? this.documentsService.replaceDocumentFile(editing.id, file, payload)
        : this.documentsService.updateDocument(editing.id, payload)
      : from(files).pipe(
          concatMap((item) =>
            this.documentsService
              .uploadDocument(item, {
                ...payload,
                title: files.length > 1 ? item.name.slice(0, 255) : payload.title,
              })
              .pipe(tap(() => this.selectedFiles.update((remaining) => remaining.slice(1)))),
          ),
        );
    this.saving.set(true);
    this.saveError.set(null);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      complete: () => {
        this.saving.set(false);
        this.editorOpen.set(false);
        this.message.success(editing ? 'Đã cập nhật tài liệu.' : 'Đã thêm tài liệu.');
        this.loadDocuments(!editing);
      },
      error: (error) => {
        this.saving.set(false);
        if (files.length > 1) {
          const remaining = this.selectedFiles();
          if (remaining.length === 1)
            this.form.controls.title.setValue(remaining[0].name.slice(0, 255));
          if (remaining.length < files.length) this.loadDocuments(true);
          this.saveError.set(
            `Đã lưu ${files.length - remaining.length}/${files.length} tệp. ${remaining[0].name}: ${errorMessage(error, 'Tải lên thất bại.')}`,
          );
          return;
        }
        this.saveError.set(errorMessage(error, 'Không thể lưu tài liệu. Vui lòng thử lại.'));
      },
    });
  }

  protected deleteDocument(document: LibraryDocument): void {
    if (document.usage_count > 0 || this.deletingId() !== null) return;
    this.deletingId.set(document.id);
    this.documentsService
      .deleteDocument(document.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.deletingId.set(null);
          this.message.success('Đã xóa tài liệu.');
          this.loadDocuments();
        },
        error: (error) => {
          this.deletingId.set(null);
          this.message.error(errorMessage(error, 'Không thể xóa tài liệu. Vui lòng thử lại.'));
        },
      });
  }
}
