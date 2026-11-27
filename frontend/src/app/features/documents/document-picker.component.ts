import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  EventEmitter,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { DocumentsService, LibraryDocument } from '../../core/api/documents.service';
import {
  INTERNSHIP_POSITIONS,
  InternshipPosition,
  internshipPositionLabel,
} from '../../core/api/internship.service';

export type DocumentSelection = Pick<
  LibraryDocument,
  'id' | 'title' | 'url' | 'format' | 'positions'
> &
  Partial<Pick<LibraryDocument, 'original_filename'>>;

@Component({
  selector: 'app-document-picker',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    NzButtonModule,
    NzInputModule,
    NzModalModule,
    NzSelectModule,
    NzTableModule,
    NzTagModule,
  ],
  template: `
    <nz-modal
      [nzVisible]="visible"
      nzTitle="Chọn tài liệu từ kho"
      [nzWidth]="'min(900px, 96vw)'"
      [nzFooter]="footer"
      [nzClosable]="!saving"
      [nzMaskClosable]="!saving"
      (nzOnCancel)="cancelled.emit()"
    >
      <ng-container *nzModalContent>
        <div class="filters">
          <input
            nz-input
            aria-label="Tìm tên tài liệu"
            placeholder="Tìm theo tên tài liệu"
            [ngModel]="search"
            (ngModelChange)="setSearch($event)"
          />
          <nz-select
            nzAllowClear
            nzPlaceHolder="Vị trí thực tập"
            aria-label="Vị trí thực tập"
            [ngModel]="position"
            (ngModelChange)="position = $event; resetPage()"
          >
            @for (option of positions; track option.value) {
              <nz-option [nzValue]="option.value" [nzLabel]="option.label" />
            }
          </nz-select>
          <nz-select
            nzAllowClear
            nzPlaceHolder="Định dạng"
            aria-label="Định dạng"
            [ngModel]="format"
            (ngModelChange)="format = $event; resetPage()"
          >
            @for (item of formats(); track item) {
              <nz-option [nzValue]="item" [nzLabel]="item.toUpperCase()" />
            }
          </nz-select>
        </div>
        @if (error()) {
          <div role="alert" class="load-error">
            Không thể tải kho tài liệu.
            <button nz-button type="button" (click)="load()">Thử lại</button>
          </div>
        }
        <nz-table
          #table
          class="responsive-card-table"
          [nzData]="items()"
          [nzLoading]="loading()"
          [nzFrontPagination]="false"
          [nzTotal]="total()"
          [nzPageIndex]="page"
          [nzPageSize]="10"
          (nzPageIndexChange)="page = $event; load()"
          nzSize="small"
          nzNoResult="Không có tài liệu phù hợp"
        >
          <thead>
            <tr>
              <th nzWidth="48px">Chọn</th>
              <th>Tên tài liệu</th>
              <th>Định dạng</th>
              <th>Phạm vi</th>
            </tr>
          </thead>
          <tbody>
            @for (document of table.data; track document.id) {
              <tr>
                <td data-label="Chọn">
                  <input
                    type="checkbox"
                    [checked]="draft().has(document.id)"
                    [attr.aria-label]="'Chọn ' + document.title"
                    (change)="toggle(document)"
                  />
                </td>
                <td data-label="Tên tài liệu">{{ document.title }}</td>
                <td data-label="Định dạng">
                  <nz-tag>{{ document.format.toUpperCase() }}</nz-tag>
                </td>
                <td data-label="Phạm vi">{{ positionLabels(document.positions) }}</td>
              </tr>
            }
          </tbody>
        </nz-table>
        <p class="selected-count">
          Đã chọn {{ draft().size }} tài liệu. Lựa chọn được giữ khi chuyển trang hoặc lọc.
        </p>
      </ng-container>
      <ng-template #footer>
        <button nz-button type="button" [disabled]="saving" (click)="cancelled.emit()">Hủy</button>
        <button
          nz-button
          nzType="primary"
          type="button"
          [nzLoading]="saving"
          [disabled]="saving || !draft().size"
          (click)="confirm()"
        >
          Dùng {{ draft().size }} tài liệu
        </button>
      </ng-template>
    </nz-modal>
  `,
  styles: [
    `
      .filters {
        display: grid;
        grid-template-columns: minmax(180px, 1fr) 190px 140px;
        gap: 12px;
        margin-bottom: 16px;
      }
      .selected-count {
        margin: 12px 0 0;
        color: #595959;
      }
      .load-error {
        display: flex;
        gap: 12px;
        align-items: center;
        margin-bottom: 12px;
      }
      @media (max-width: 640px) {
        .filters {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class DocumentPickerComponent implements OnChanges, OnDestroy {
  @Input() visible = false;
  @Input() single = false;
  @Input() saving = false;
  @Input() selectedDocuments: readonly DocumentSelection[] = [];
  @Output() readonly cancelled = new EventEmitter<void>();
  @Output() readonly confirmed = new EventEmitter<DocumentSelection[]>();
  private readonly service = inject(DocumentsService);
  private readonly destroyRef = inject(DestroyRef);
  private request?: Subscription;
  private timer?: ReturnType<typeof setTimeout>;
  protected readonly positions = INTERNSHIP_POSITIONS;
  protected readonly items = signal<LibraryDocument[]>([]);
  protected readonly total = signal(0);
  protected readonly formats = signal<string[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal(false);
  protected readonly draft = signal(new Map<string, DocumentSelection>());
  protected search = '';
  protected position: InternshipPosition | null = null;
  protected format: string | null = null;
  protected page = 1;

  ngOnChanges(): void {
    this.request?.unsubscribe();
    clearTimeout(this.timer);
    if (!this.visible) return;
    this.draft.set(new Map(this.selectedDocuments.map((document) => [document.id, document])));
    this.page = 1;
    this.load();
  }

  ngOnDestroy(): void {
    clearTimeout(this.timer);
    this.request?.unsubscribe();
  }

  protected setSearch(value: string): void {
    this.search = value;
    this.request?.unsubscribe();
    clearTimeout(this.timer);
    this.loading.set(true);
    this.timer = setTimeout(() => this.resetPage(), 250);
  }

  protected resetPage(): void {
    this.page = 1;
    this.load();
  }

  protected load(): void {
    clearTimeout(this.timer);
    this.request?.unsubscribe();
    this.loading.set(true);
    this.error.set(false);
    this.request = this.service
      .listDocuments({
        search: this.search,
        position: this.position,
        format: this.format,
        skip: (this.page - 1) * 10,
        limit: 10,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.items.set(result.items);
          this.total.set(result.total);
          this.formats.set(result.formats);
          this.loading.set(false);
        },
        error: () => {
          this.items.set([]);
          this.total.set(0);
          this.error.set(true);
          this.loading.set(false);
        },
      });
  }

  protected toggle(document: DocumentSelection): void {
    if (this.saving) return;
    const next = new Map(this.draft());
    if (next.has(document.id)) next.delete(document.id);
    else {
      if (this.single) next.clear();
      next.set(document.id, document);
    }
    this.draft.set(next);
  }

  protected confirm(): void {
    if (this.saving || !this.draft().size) return;
    this.confirmed.emit([...this.draft().values()]);
  }

  protected positionLabels(positions: InternshipPosition[]): string {
    return positions.length ? positions.map(internshipPositionLabel).join(', ') : 'Dùng chung';
  }
}
