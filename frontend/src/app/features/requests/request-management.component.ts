import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';

import {
  InternshipApplication,
  InternshipService,
} from '../../core/api/internship.service';

@Component({
  selector: 'app-request-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NzBadgeModule,
    NzButtonModule,
    NzCardModule,
    NzCheckboxModule,
    NzFormModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzPopconfirmModule,
    NzSelectModule,
    NzSpinModule,
    NzTableModule,
    NzTagModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="request-page feature-page-layout">
      <!-- Header -->
      <div class="page-header feature-page-header">
        <div class="header-titles">
          <h1 class="feature-page-title">Duyệt đơn đăng ký thực tập</h1>
          <p class="feature-page-subtitle">
            Xét duyệt và tiếp nhận đơn đăng ký tham gia các đợt thực tập của thực tập sinh.
          </p>
        </div>
      </div>

      <!-- Main Container -->
      <nz-card [nzBordered]="false" class="main-card">
        <!-- Toolbar Đơn đăng ký -->
        <div class="table-toolbar">
          <div class="toolbar-left">
            <div class="search-box">
              <input
                type="text"
                nz-input
                placeholder="Tìm theo tên hoặc email thực tập sinh..."
                [ngModel]="appSearchQuery()"
                (ngModelChange)="appSearchQuery.set($event)"
              />
            </div>

            <div class="filter-box">
              <span class="filter-label">Trạng thái:</span>
              <nz-select
                [ngModel]="appStatusFilter()"
                (ngModelChange)="appStatusFilter.set($event)"
                class="filter-select"
              >
                <nz-option nzValue="" nzLabel="Tất cả trạng thái"></nz-option>
                <nz-option nzValue="PENDING" nzLabel="Chờ duyệt (PENDING)"></nz-option>
                <nz-option nzValue="APPROVED" nzLabel="Đã duyệt (APPROVED)"></nz-option>
                <nz-option nzValue="REJECTED" nzLabel="Từ chối (REJECTED)"></nz-option>
              </nz-select>
            </div>

            <button
              nz-button
              nzType="default"
              (click)="loadApplications()"
              [nzLoading]="isLoadingApps()"
            >
              <span nz-icon nzType="reload"></span> Làm mới
            </button>
          </div>

          <div class="toolbar-right">
            <button
              nz-button
              nzType="primary"
              class="btn-approve-all"
              [disabled]="pendingApplicationsCount() === 0"
              nz-popconfirm
              [nzPopconfirmTitle]="
                'Bạn có chắc chắn muốn duyệt tất cả ' +
                pendingApplicationsCount() +
                ' đơn đăng ký đang chờ duyệt?'
              "
              (nzOnConfirm)="approveAllApps()"
              [nzLoading]="isBatchSubmitting()"
            >
              <span nz-icon nzType="check-all"></span> Duyệt tất cả ({{
                pendingApplicationsCount()
              }})
            </button>
          </div>
        </div>

        <!-- Batch Action Bar (Khi có đơn được chọn) -->
        @if (selectedAppIds().size > 0) {
          <div class="batch-action-bar">
            <div class="batch-info">
              <span nz-icon nzType="check-circle" class="text-blue-500"></span>
              <span>Đã chọn: <strong>{{ selectedAppIds().size }}</strong> đơn đăng ký</span>
            </div>
            <div class="batch-buttons">
              <button
                nz-button
                nzType="primary"
                class="btn-batch-approve"
                [nzLoading]="isBatchSubmitting()"
                nz-popconfirm
                [nzPopconfirmTitle]="
                  'Phê duyệt ' + selectedAppIds().size + ' đơn đăng ký đã chọn?'
                "
                (nzOnConfirm)="submitBatchAppReview('APPROVED')"
              >
                <span nz-icon nzType="check"></span> Duyệt đã chọn ({{ selectedAppIds().size }})
              </button>
              <button
                nz-button
                nzDanger
                class="btn-batch-reject"
                [nzLoading]="isBatchSubmitting()"
                (click)="openBatchRejectModal()"
              >
                <span nz-icon nzType="close"></span> Từ chối đã chọn ({{ selectedAppIds().size }})
              </button>
              <button nz-button nzType="default" (click)="clearAppSelection()">Bỏ chọn</button>
            </div>
          </div>
        }

        <!-- Desktop Table Đơn đăng ký -->
        <div class="desktop-only">
          <nz-table
            #appsTable
            [nzData]="filteredApplications()"
            [nzLoading]="isLoadingApps()"
            [nzShowPagination]="true"
            [nzPageSize]="10"
            [nzScroll]="{ x: '1000px' }"
          >
            <thead>
              <tr>
                <th
                  nzWidth="50px"
                  [nzChecked]="isAllAppsSelected()"
                  [nzIndeterminate]="isAppsIndeterminate()"
                  (nzCheckedChange)="onSelectAllApps($event)"
                ></th>
                <th nzWidth="220px">Thực tập sinh</th>
                <th nzWidth="200px">Đợt thực tập</th>
                <th>Lý do / Nguyện vọng</th>
                <th nzWidth="150px">Thời gian nộp</th>
                <th nzWidth="130px">Trạng thái</th>
                <th nzWidth="180px">Ghi chú duyệt</th>
                <th nzWidth="150px" nzAlign="center">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              @for (app of appsTable.data; track app.id) {
                <tr>
                  <td
                    [nzChecked]="selectedAppIds().has(app.id)"
                    (nzCheckedChange)="toggleAppSelection(app.id, $event)"
                  ></td>
                  <td>
                    <div class="font-medium text-slate-900">
                      {{ app.intern_name || 'Thực tập sinh' }}
                    </div>
                    <small class="text-slate-500">{{ app.intern_email }}</small>
                  </td>
                  <td>
                    <span class="font-medium text-slate-800">{{
                      app.internship_name || '—'
                    }}</span>
                  </td>
                  <td class="reason-cell">
                    {{ app.reason || '—' }}
                  </td>
                  <td>{{ app.created_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                  <td>
                    @if (app.status === 'PENDING') {
                      <nz-tag nzColor="warning">Chờ duyệt</nz-tag>
                    } @else if (app.status === 'APPROVED') {
                      <nz-tag nzColor="success">Đã phê duyệt</nz-tag>
                    } @else if (app.status === 'REJECTED') {
                      <nz-tag nzColor="error">Bị từ chối</nz-tag>
                    }
                  </td>
                  <td>
                    <small class="text-slate-600">{{ app.review_note || '—' }}</small>
                  </td>
                  <td nzAlign="center">
                    @if (app.status === 'PENDING') {
                      <div class="action-buttons-inline">
                        <button
                          nz-button
                          nzType="primary"
                          nzSize="small"
                          nz-popconfirm
                          [nzPopconfirmTitle]="
                            'Xác nhận duyệt cho ' + (app.intern_name || 'Intern') + ' vào đợt?'
                          "
                          (nzOnConfirm)="singleApproveApp(app)"
                        >
                          Duyệt
                        </button>
                        <button
                          nz-button
                          nzDanger
                          nzSize="small"
                          (click)="openSingleRejectModal(app)"
                        >
                          Từ chối
                        </button>
                      </div>
                    } @else {
                      <span class="text-slate-400 text-xs">Đã xử lý</span>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </nz-table>
        </div>

        <!-- Mobile View Đơn đăng ký -->
        <div class="mobile-only">
          @if (isLoadingApps()) {
            <div class="loading-box"><nz-spin nzSimple></nz-spin></div>
          } @else if (filteredApplications().length === 0) {
            <div class="empty-box">Không có đơn đăng ký nào.</div>
          } @else {
            <div class="mobile-card-list">
              @for (app of filteredApplications(); track app.id) {
                <div class="mobile-app-card" [class.is-selected]="selectedAppIds().has(app.id)">
                  <div class="card-header">
                    <!-- eslint-disable-next-line @angular-eslint/template/label-has-associated-control -->
                    <label
                      nz-checkbox
                      [nzChecked]="selectedAppIds().has(app.id)"
                      (nzCheckedChange)="toggleAppSelection(app.id, $event)"
                    >
                      <span class="font-semibold text-slate-800">{{
                        app.intern_name || 'Thực tập sinh'
                      }}</span>
                    </label>
                    @if (app.status === 'PENDING') {
                      <nz-tag nzColor="warning">Chờ duyệt</nz-tag>
                    } @else if (app.status === 'APPROVED') {
                      <nz-tag nzColor="success">Đã phê duyệt</nz-tag>
                    } @else if (app.status === 'REJECTED') {
                      <nz-tag nzColor="error">Bị từ chối</nz-tag>
                    }
                  </div>

                  <div class="card-body">
                    <p class="time-text">
                      <small>{{ app.intern_email }}</small>
                    </p>
                    <p>
                      <strong>Đợt:</strong> {{ app.internship_name || '—' }}
                    </p>
                    @if (app.reason) {
                      <p class="reason-text">
                        <strong>Lý do:</strong> {{ app.reason }}
                      </p>
                    }
                    <p class="time-text">
                      <small>Nộp lúc: {{ app.created_at | date: 'dd/MM/yyyy HH:mm' }}</small>
                    </p>
                    @if (app.review_note) {
                      <p class="note-text">
                        <small>Phản hồi: {{ app.review_note }}</small>
                      </p>
                    }
                  </div>

                  @if (app.status === 'PENDING') {
                    <div class="card-footer">
                      <button
                        nz-button
                        nzType="primary"
                        nzBlock
                        nz-popconfirm
                        [nzPopconfirmTitle]="
                          'Duyệt đơn của ' + (app.intern_name || 'Intern') + '?'
                        "
                        (nzOnConfirm)="singleApproveApp(app)"
                      >
                        Duyệt đơn
                      </button>
                      <button nz-button nzDanger nzBlock (click)="openSingleRejectModal(app)">
                        Từ chối
                      </button>
                    </div>
                  }
                </div>
              }
            </div>
          }
        </div>
      </nz-card>

      <!-- Modal Từ chối (Dùng cho từ chối đơn lẻ / từ chối nhiều đơn) -->
      <nz-modal
        [(nzVisible)]="isRejectModalVisible"
        [nzTitle]="rejectModalTitle"
        (nzOnCancel)="closeRejectModal()"
        (nzOnOk)="confirmRejectAction()"
        [nzOkLoading]="isBatchSubmitting()"
        nzOkText="Xác nhận từ chối"
        nzOkDanger
        nzCancelText="Hủy"
        [nzWidth]="'min(500px, calc(100vw - 24px))'"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="rejectForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Lý do từ chối</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng nhập lý do từ chối">
                <textarea
                  nz-input
                  rows="3"
                  formControlName="reason"
                  placeholder="Nhập lý do từ chối để thông báo cho ứng viên..."
                ></textarea>
              </nz-form-control>
            </nz-form-item>
          </form>
        </ng-container>
      </nz-modal>
    </div>
  `,
  styles: [
    `
      .request-page {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .page-header {
        background: #fff;
        padding: 18px 24px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }
      .feature-page-title {
        margin: 0 0 6px;
        font-size: 20px;
        font-weight: 700;
        color: #0f172a;
      }
      .feature-page-subtitle {
        color: #64748b;
        font-size: 13px;
        margin: 0;
      }
      .main-card {
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }

      /* Toolbar */
      .table-toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 16px;
        padding: 4px 0;
      }
      .toolbar-left {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        flex: 1;
      }
      .toolbar-right {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .search-box {
        width: 300px;
        max-width: 100%;
      }
      .filter-box {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .filter-label {
        font-size: 13px;
        font-weight: 500;
        color: #475569;
        white-space: nowrap;
      }
      .filter-select {
        width: 180px;
      }

      /* Batch Action Bar */
      .batch-action-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        animation: fadeIn 0.2s ease-in;
      }
      .batch-info {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: #166534;
      }
      .batch-buttons {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }
      .btn-approve-all {
        background-color: #10b981 !important;
        border-color: #10b981 !important;
        font-weight: 500;
      }
      .btn-batch-approve {
        background-color: #10b981 !important;
        border-color: #10b981 !important;
      }
      .btn-batch-reject {
        margin: 0 !important;
      }

      .reason-cell {
        word-break: break-word;
        white-space: normal;
        line-height: 1.5;
      }
      .action-buttons-inline {
        display: flex;
        gap: 6px;
        justify-content: center;
      }

      .desktop-only {
        display: block;
      }
      .mobile-only {
        display: none;
      }

      /* Responsive Mobile (<= 768px) */
      @media (max-width: 768px) {
        .desktop-only {
          display: none !important;
        }
        .mobile-only {
          display: block !important;
        }
        .table-toolbar {
          flex-direction: column;
          align-items: stretch;
        }
        .toolbar-left {
          flex-direction: column;
          align-items: stretch;
          width: 100%;
        }
        .search-box,
        .filter-box,
        .filter-select {
          width: 100% !important;
        }
        .toolbar-right {
          width: 100%;
          button {
            width: 100%;
          }
        }
        .batch-action-bar {
          flex-direction: column;
          align-items: stretch;
          .batch-buttons {
            flex-direction: column;
            button {
              width: 100%;
            }
          }
        }

        .mobile-card-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .mobile-app-card {
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          padding: 14px;
          background: #fff;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
          transition: all 0.2s;

          &.is-selected {
            border-color: #3b82f6;
            background: #f8faff;
          }

          .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 8px;
            margin-bottom: 10px;

            label {
              min-width: 0;
              word-break: break-word;
            }
          }
          .card-body {
            font-size: 13px;
            margin-bottom: 12px;
            word-break: break-word;
            overflow-wrap: anywhere;
            p {
              margin: 4px 0;
            }
            .reason-text {
              color: #1e293b;
              line-height: 1.4;
            }
            .time-text {
              color: #94a3b8;
            }
            .note-text {
              color: #64748b;
              font-style: italic;
            }
          }
          .card-footer {
            border-top: 1px dashed #e2e8f0;
            padding-top: 10px;
            display: flex;
            gap: 8px;
            button {
              flex: 1;
            }
          }
        }

        .loading-box,
        .empty-box {
          text-align: center;
          padding: 24px;
          color: #94a3b8;
          font-size: 13px;
        }
      }

      @media (max-width: 390px) {
        .page-header {
          padding: 12px 14px;
        }
        .feature-page-title {
          font-size: 18px;
        }
        .main-card ::ng-deep .ant-card-body {
          padding: 12px 8px !important;
        }
        .mobile-app-card {
          padding: 10px 12px;
        }
        .batch-action-bar {
          padding: 8px 10px;
        }
        .batch-info {
          font-size: 13px;
        }
      }

      @keyframes fadeIn {
        from {
          opacity: 0;
          transform: translateY(-4px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
    `,
  ],
})
export class RequestManagementComponent implements OnInit {
  private readonly internshipService = inject(InternshipService);
  private readonly fb = inject(FormBuilder);
  private readonly message = inject(NzMessageService);
  private readonly cdr = inject(ChangeDetectorRef);

  // --- ĐƠN ĐĂNG KÝ THỰC TẬP (APPLICATIONS) ---
  protected readonly applications = signal<InternshipApplication[]>([]);
  protected readonly isLoadingApps = signal<boolean>(false);
  protected readonly isBatchSubmitting = signal<boolean>(false);
  protected readonly appSearchQuery = signal<string>('');
  protected readonly appStatusFilter = signal<string>('');
  protected readonly selectedAppIds = signal<Set<string>>(new Set());

  protected readonly pendingApplicationsCount = computed(() => {
    return this.applications().filter((a) => a.status === 'PENDING').length;
  });

  protected readonly filteredApplications = computed(() => {
    let list = this.applications();
    const query = this.appSearchQuery().trim().toLowerCase();
    if (query) {
      list = list.filter(
        (a) =>
          (a.intern_name && a.intern_name.toLowerCase().includes(query)) ||
          (a.intern_email && a.intern_email.toLowerCase().includes(query)) ||
          (a.internship_name && a.internship_name.toLowerCase().includes(query)),
      );
    }
    const status = this.appStatusFilter();
    if (status) {
      list = list.filter((a) => a.status === status);
    }
    return list;
  });

  protected isAllAppsSelected = computed(() => {
    const currentList = this.filteredApplications();
    if (currentList.length === 0) return false;
    const selected = this.selectedAppIds();
    return currentList.every((a) => selected.has(a.id));
  });

  protected isAppsIndeterminate = computed(() => {
    const currentList = this.filteredApplications();
    if (currentList.length === 0) return false;
    const selected = this.selectedAppIds();
    const count = currentList.filter((a) => selected.has(a.id)).length;
    return count > 0 && count < currentList.length;
  });

  // --- MODAL TỪ CHỐI ---
  protected isRejectModalVisible = false;
  protected rejectModalTitle = 'Xác nhận từ chối';
  private rejectTarget: 'SINGLE_APP' | 'BATCH_APPS' = 'BATCH_APPS';
  private targetAppToReject: InternshipApplication | null = null;

  protected readonly rejectForm = this.fb.group({
    reason: ['', [Validators.required, Validators.maxLength(2000)]],
  });

  ngOnInit(): void {
    this.loadApplications();
  }

  // ================= APPLICATIONS LOGIC =================
  loadApplications(): void {
    this.isLoadingApps.set(true);
    this.internshipService.getApplications().subscribe({
      next: (apps) => {
        this.applications.set(apps);
        this.isLoadingApps.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Không thể tải danh sách đơn đăng ký.');
        this.isLoadingApps.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  toggleAppSelection(id: string, checked: boolean): void {
    const updated = new Set(this.selectedAppIds());
    if (checked) {
      updated.add(id);
    } else {
      updated.delete(id);
    }
    this.selectedAppIds.set(updated);
  }

  onSelectAllApps(checked: boolean): void {
    const updated = new Set(this.selectedAppIds());
    this.filteredApplications().forEach((a) => {
      if (checked) {
        updated.add(a.id);
      } else {
        updated.delete(a.id);
      }
    });
    this.selectedAppIds.set(updated);
  }

  clearAppSelection(): void {
    this.selectedAppIds.set(new Set());
  }

  singleApproveApp(app: InternshipApplication): void {
    this.internshipService.reviewApplication(app.id, { status: 'APPROVED' }).subscribe({
      next: () => {
        this.message.success(`Đã duyệt đơn đăng ký của ${app.intern_name || 'Intern'}!`);
        this.loadApplications();
      },
      error: (err) => {
        this.message.error(err?.error?.detail || 'Lỗi khi phê duyệt đơn.');
      },
    });
  }

  openSingleRejectModal(app: InternshipApplication): void {
    this.rejectTarget = 'SINGLE_APP';
    this.targetAppToReject = app;
    this.rejectModalTitle = `Từ chối đơn đăng ký: ${app.intern_name || 'Thực tập sinh'}`;
    this.rejectForm.reset({ reason: '' });
    this.isRejectModalVisible = true;
  }

  openBatchRejectModal(): void {
    this.rejectTarget = 'BATCH_APPS';
    const count = this.selectedAppIds().size;
    this.rejectModalTitle = `Xác nhận từ chối ${count} đơn đăng ký đã chọn`;
    this.rejectForm.reset({ reason: '' });
    this.isRejectModalVisible = true;
  }

  closeRejectModal(): void {
    this.isRejectModalVisible = false;
    this.targetAppToReject = null;
  }

  confirmRejectAction(): void {
    if (this.rejectForm.invalid) {
      this.rejectForm.markAllAsTouched();
      return;
    }

    const reason = this.rejectForm.value.reason?.trim() || null;

    if (this.rejectTarget === 'SINGLE_APP') {
      const app = this.targetAppToReject;
      if (!app) return;
      this.isBatchSubmitting.set(true);
      this.internshipService
        .reviewApplication(app.id, { status: 'REJECTED', review_note: reason })
        .subscribe({
          next: () => {
            this.message.success(`Đã từ chối đơn đăng ký của ${app.intern_name || 'Intern'}!`);
            this.isBatchSubmitting.set(false);
            this.closeRejectModal();
            this.loadApplications();
          },
          error: (err) => {
            this.message.error(err?.error?.detail || 'Lỗi khi từ chối đơn.');
            this.isBatchSubmitting.set(false);
          },
        });
    } else {
      this.submitBatchAppReview('REJECTED', reason);
      this.closeRejectModal();
    }
  }

  submitBatchAppReview(status: 'APPROVED' | 'REJECTED', note?: string | null): void {
    const ids = Array.from(this.selectedAppIds());
    if (ids.length === 0) return;

    this.isBatchSubmitting.set(true);
    this.internshipService.batchReviewApplications(ids, status, note).subscribe({
      next: (res) => {
        this.message.success(res.message);
        this.isBatchSubmitting.set(false);
        this.clearAppSelection();
        this.loadApplications();
      },
      error: (err) => {
        this.message.error(err?.error?.detail || 'Lỗi khi xử lý hàng loạt.');
        this.isBatchSubmitting.set(false);
      },
    });
  }

  approveAllApps(): void {
    this.isBatchSubmitting.set(true);
    this.internshipService.approveAllApplications().subscribe({
      next: (res) => {
        this.message.success(res.message);
        this.isBatchSubmitting.set(false);
        this.clearAppSelection();
        this.loadApplications();
      },
      error: (err) => {
        this.message.error(err?.error?.detail || 'Lỗi khi duyệt tất cả đơn.');
        this.isBatchSubmitting.set(false);
      },
    });
  }
}
