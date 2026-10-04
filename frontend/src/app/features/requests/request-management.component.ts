import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDatePickerModule } from 'ng-zorro-antd/date-picker';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';

import {
  InternshipRequest,
  InternshipService,
  RequestStatus,
  RequestType,
} from '../../core/api/internship.service';

@Component({
  selector: 'app-request-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NzButtonModule,
    NzCardModule,
    NzDatePickerModule,
    NzFormModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzSelectModule,
    NzTableModule,
    NzTagModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="request-page">
      <!-- Header -->
      <div class="page-header">
        <div class="header-titles">
          <h2>Quản lý Yêu cầu Thực tập</h2>
          <p>Duyệt hoặc từ chối các đề xuất gia hạn, tạm dừng hoặc kết thúc thực tập.</p>
        </div>
      </div>

      <!-- Main Content Card -->
      <nz-card [nzBordered]="false" class="main-card">
        <!-- Advanced Toolbar Filter -->
        <div class="table-toolbar">
          <div class="filter-row">
            <!-- 1. Bộ lọc Loại yêu cầu -->
            <div class="filter-item">
              <span class="filter-label">Loại yêu cầu:</span>
              <nz-select
                [ngModel]="typeFilter()"
                (ngModelChange)="onTypeFilterChange($event)"
                nzPlaceHolder="Tất cả loại"
                class="filter-select"
              >
                <nz-option nzValue="" nzLabel="Tất cả loại yêu cầu"></nz-option>
                <nz-option nzValue="EXTEND" nzLabel="Gia hạn thực tập"></nz-option>
                <nz-option nzValue="STOP" nzLabel="Dừng thực tập"></nz-option>
                <nz-option nzValue="COMPLETE" nzLabel="Kết thúc thực tập"></nz-option>
              </nz-select>
            </div>

            <!-- 2. Bộ lọc Trạng thái -->
            <div class="filter-item">
              <span class="filter-label">Trạng thái:</span>
              <nz-select
                [ngModel]="statusFilter()"
                (ngModelChange)="onStatusFilterChange($event)"
                nzPlaceHolder="Tất cả trạng thái"
                class="filter-select"
              >
                <nz-option nzValue="" nzLabel="Tất cả trạng thái"></nz-option>
                <nz-option nzValue="PENDING" nzLabel="Chờ duyệt (PENDING)"></nz-option>
                <nz-option nzValue="APPROVED" nzLabel="Đã duyệt (APPROVED)"></nz-option>
                <nz-option nzValue="REJECTED" nzLabel="Từ chối (REJECTED)"></nz-option>
              </nz-select>
            </div>

            <!-- 3. Bộ lọc Khoảng thời gian -->
            <div class="filter-item">
              <span class="filter-label">Khoảng thời gian:</span>
              <nz-range-picker
                [ngModel]="dateRange()"
                (ngModelChange)="onDateRangeChange($event)"
                nzFormat="dd/MM/yyyy"
                class="date-picker"
              ></nz-range-picker>
            </div>

            <!-- Nút Reset -->
            <div class="filter-item">
              <button nz-button nzType="default" (click)="resetFilters()">
                <span nz-icon nzType="reload"></span> Đặt lại
              </button>
            </div>
          </div>
        </div>

        <!-- Desktop Table View -->
        <div class="desktop-only">
          <nz-table
            #requestTable
            [nzData]="requests()"
            [nzLoading]="isLoading()"
            [nzShowPagination]="true"
            [nzPageSize]="10"
            [nzScroll]="{ x: '900px' }"
          >
            <thead>
              <tr>
                <th nzWidth="150px">Loại yêu cầu</th>
                <th nzWidth="300px">Lý do đề xuất</th>
                <th nzWidth="180px">Thời gian gửi / Đề xuất KT</th>
                <th nzWidth="120px">Trạng thái</th>
                <th nzWidth="200px">Ghi chú phản hồi</th>
                <th nzWidth="120px" nzAlign="center">Thao tác Admin</th>
              </tr>
            </thead>
            <tbody>
              @for (req of requestTable.data; track req.id) {
                <tr>
                  <td>
                    <nz-tag [nzColor]="getRequestTypeColor(req.type)">
                      {{ getRequestTypeLabel(req.type) }}
                    </nz-tag>
                  </td>
                  <td class="reason-cell">{{ req.reason }}</td>
                  <td>
                    <span>{{ req.created_at | date: 'dd/MM/yyyy HH:mm' }}</span>
                    @if (req.requested_end_date) {
                      <br /><small class="text-muted"
                        >Đề xuất KT: {{ req.requested_end_date }}</small
                      >
                    }
                  </td>
                  <td>
                    <nz-tag [nzColor]="getRequestStatusColor(req.status)">
                      {{ getRequestStatusLabel(req.status) }}
                    </nz-tag>
                  </td>
                  <td>{{ req.review_note || '—' }}</td>
                  <td nzAlign="center">
                    @if (req.status === 'PENDING') {
                      <button
                        nz-button
                        nzType="primary"
                        nzSize="small"
                        (click)="openReviewModal(req)"
                      >
                        <span nz-icon nzType="check-circle"></span>
                        Xử lý
                      </button>
                    } @else {
                      <span class="text-muted">Đã xử lý</span>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </nz-table>
        </div>

        <!-- Mobile Card List View -->
        <div class="mobile-only">
          @if (isLoading()) {
            <div class="loading-box">Đang tải danh sách...</div>
          } @else if (requests().length === 0) {
            <div class="empty-box">Không có dữ liệu đề xuất nào phù hợp.</div>
          } @else {
            <div class="mobile-card-list">
              @for (req of requests(); track req.id) {
                <div class="mobile-request-card">
                  <div class="card-header">
                    <nz-tag [nzColor]="getRequestTypeColor(req.type)">
                      {{ getRequestTypeLabel(req.type) }}
                    </nz-tag>
                    <nz-tag [nzColor]="getRequestStatusColor(req.status)">
                      {{ getRequestStatusLabel(req.status) }}
                    </nz-tag>
                  </div>

                  <div class="card-body">
                    <p class="reason-text"><strong>Lý do:</strong> {{ req.reason }}</p>
                    <p class="time-text">
                      <small>Gửi lúc: {{ req.created_at | date: 'dd/MM/yyyy HH:mm' }}</small>
                      @if (req.requested_end_date) {
                        <br /><small>Đề xuất kết thúc: {{ req.requested_end_date }}</small>
                      }
                    </p>
                    @if (req.review_note) {
                      <p class="note-text">
                        <small>Phản hồi: {{ req.review_note }}</small>
                      </p>
                    }
                  </div>

                  <div class="card-footer">
                    @if (req.status === 'PENDING') {
                      <button nz-button nzType="primary" nzBlock (click)="openReviewModal(req)">
                        <span nz-icon nzType="check-circle"></span> Xem & Xử lý
                      </button>
                    } @else {
                      <div class="status-done-label">Đã xử lý</div>
                    }
                  </div>
                </div>
              }
            </div>
          }
        </div>
      </nz-card>

      <!-- Modal Duyệt / Từ chối -->
      <nz-modal
        [(nzVisible)]="isReviewModalVisible"
        nzTitle="Xử lý Đề xuất Thực tập"
        (nzOnCancel)="closeReviewModal()"
        [nzFooter]="modalFooter"
        class="custom-review-modal"
      >
        <ng-container *nzModalContent>
          @if (selectedRequest(); as req) {
            <div class="info-box">
              <p><strong>Loại đề xuất:</strong> {{ getRequestTypeLabel(req.type) }}</p>
              <p><strong>Lý do gửi:</strong> {{ req.reason }}</p>
              @if (req.requested_end_date) {
                <p><strong>Ngày kết thúc đề xuất:</strong> {{ req.requested_end_date }}</p>
              }
            </div>

            <form [formGroup]="reviewForm" nz-form nzLayout="vertical">
              <nz-form-item class="mb-0">
                <nz-form-label>Ghi chú phản hồi (Admin Note)</nz-form-label>
                <nz-form-control>
                  <textarea
                    nz-input
                    rows="3"
                    formControlName="review_note"
                    placeholder="Nhập ghi chú hoặc lý do phê duyệt / từ chối..."
                  ></textarea>
                </nz-form-control>
              </nz-form-item>
            </form>
          }
        </ng-container>

        <ng-template #modalFooter>
          <div class="modal-footer-btns">
            <button
              nz-button
              nzType="primary"
              class="btn-action btn-approve"
              [nzLoading]="isSubmitting()"
              (click)="submitReview('APPROVED')"
            >
              Phê duyệt
            </button>

            <button
              nz-button
              nzType="primary"
              nzDanger
              class="btn-action"
              [nzLoading]="isSubmitting()"
              (click)="submitReview('REJECTED')"
            >
              Từ chối
            </button>

            <button
              nz-button
              nzType="default"
              class="btn-action btn-cancel"
              (click)="closeReviewModal()"
            >
              Hủy
            </button>
          </div>
        </ng-template>
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
        padding: 16px 20px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        h2 {
          margin: 0 0 4px;
          font-size: 18px;
          font-weight: 600;
          color: #1a1a1a;
        }
        p {
          margin: 0;
          font-size: 13px;
          color: #666;
        }
      }
      .main-card {
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }
      .table-toolbar {
        margin-bottom: 20px;
      }
      .filter-row {
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
      }
      .filter-item {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .filter-label {
        font-size: 13px;
        font-weight: 500;
        color: #595959;
        white-space: nowrap;
      }
      .filter-select {
        width: 180px;
      }
      .date-picker {
        width: 250px;
      }
      .reason-cell {
        word-break: break-word;
        white-space: normal;
        line-height: 1.5;
      }
      .info-box {
        background: #fafafa;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 16px;
        border-left: 3px solid #1890ff;
        p {
          margin: 4px 0;
          font-size: 13px;
          line-height: 1.5;
        }
      }
      .text-muted {
        color: #8c8c8c;
        font-size: 12px;
      }
      .mb-0 {
        margin-bottom: 0 !important;
      }
      .desktop-only {
        display: block;
      }
      .mobile-only {
        display: none;
      }
      ::ng-deep .custom-review-modal .ant-modal-footer {
        padding: 12px 24px 20px 24px !important;
        border-top: none !important;
      }
      .modal-footer-btns {
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
        .btn-action {
          width: 100% !important;
          height: 40px !important;
          border-radius: 6px !important;
          font-weight: 500;
          font-size: 14px;
          margin: 0 !important;
        }
        .btn-approve {
          background-color: #1890ff;
          border-color: #1890ff;
        }
        .btn-cancel {
          background-color: #fff;
          border: 1px solid #d9d9d9;
          color: #262626;
        }
      }
      @media (min-width: 577px) {
        .modal-footer-btns {
          flex-direction: row-reverse;
          justify-content: flex-start;
          .btn-action {
            width: auto !important;
            min-width: 100px;
            height: 36px !important;
          }
        }
      }
      @media (max-width: 768px) {
        .filter-row {
          flex-direction: column;
          align-items: stretch;
        }
        .filter-item {
          flex-direction: column;
          align-items: flex-start;
          .filter-select,
          .date-picker {
            width: 100%;
          }
        }
      }
      @media (max-width: 576px) {
        .desktop-only {
          display: none;
        }
        .mobile-only {
          display: block;
        }
        .mobile-card-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .mobile-request-card {
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          padding: 14px;
          background: #fff;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
          .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
          }
          .card-body {
            font-size: 13px;
            margin-bottom: 12px;
            .reason-text {
              margin: 0 0 6px;
              color: #262626;
              line-height: 1.4;
            }
            .time-text {
              margin: 0 0 4px;
              color: #8c8c8c;
            }
            .note-text {
              margin: 0;
              color: #595959;
              font-style: italic;
            }
          }
          .card-footer {
            border-top: 1px dashed #f0f0f0;
            padding-top: 10px;
          }
          .status-done-label {
            text-align: center;
            color: #8c8c8c;
            font-size: 12px;
          }
        }
        .loading-box,
        .empty-box {
          text-align: center;
          padding: 24px;
          color: #8c8c8c;
          font-size: 13px;
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

  protected readonly requests = signal<InternshipRequest[]>([]);
  protected readonly isLoading = signal<boolean>(false);

  protected readonly statusFilter = signal<RequestStatus | ''>('');
  protected readonly typeFilter = signal<RequestType | ''>('');
  protected readonly dateRange = signal<Date[]>([]);

  protected readonly selectedRequest = signal<InternshipRequest | null>(null);
  protected isReviewModalVisible = false;
  protected isSubmitting = signal<boolean>(false);

  protected readonly reviewForm = this.fb.group({
    review_note: [''],
  });

  ngOnInit(): void {
    this.loadRequests();
  }

  private formatDate(d: Date): string {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  loadRequests(): void {
    this.isLoading.set(true);

    let startDateStr: string | undefined;
    let endDateStr: string | undefined;

    const dates = this.dateRange();
    if (dates && dates.length === 2) {
      startDateStr = this.formatDate(dates[0]);
      endDateStr = this.formatDate(dates[1]);
    }

    this.internshipService
      .getRequests(this.statusFilter(), this.typeFilter(), startDateStr, endDateStr)
      .subscribe({
        next: (data) => {
          this.requests.set(data);
          this.isLoading.set(false);
          this.cdr.markForCheck();
        },
        error: () => {
          this.message.error('Không thể tải danh sách đề xuất thực tập.');
          this.isLoading.set(false);
          this.cdr.markForCheck();
        },
      });
  }

  onStatusFilterChange(status: RequestStatus | ''): void {
    this.statusFilter.set(status);
    this.loadRequests();
  }

  onTypeFilterChange(type: RequestType | ''): void {
    this.typeFilter.set(type);
    this.loadRequests();
  }

  onDateRangeChange(dates: Date[]): void {
    this.dateRange.set(dates);
    this.loadRequests();
  }

  resetFilters(): void {
    this.statusFilter.set('');
    this.typeFilter.set('');
    this.dateRange.set([]);
    this.loadRequests();
  }

  openReviewModal(req: InternshipRequest): void {
    this.selectedRequest.set(req);
    this.reviewForm.reset({ review_note: '' });
    this.isReviewModalVisible = true;
    this.cdr.markForCheck();
  }

  closeReviewModal(): void {
    this.isReviewModalVisible = false;
    this.selectedRequest.set(null);
    this.cdr.markForCheck();
  }

  submitReview(status: 'APPROVED' | 'REJECTED'): void {
    const req = this.selectedRequest();
    if (!req) return;

    this.isSubmitting.set(true);
    const reviewNote = this.reviewForm.value.review_note || null;

    this.internshipService.reviewRequest(req.id, { status, review_note: reviewNote }).subscribe({
      next: () => {
        this.message.success(
          `Đã ${status === 'APPROVED' ? 'phê duyệt' : 'từ chối'} đề xuất thành công!`,
        );
        this.isSubmitting.set(false);
        this.closeReviewModal();
        this.loadRequests();
      },
      error: (err) => {
        this.message.error(err?.error?.detail || 'Lỗi khi xử lý đề xuất.');
        this.isSubmitting.set(false);
      },
    });
  }

  getRequestTypeColor(type: RequestType): string {
    switch (type) {
      case 'EXTEND':
        return 'orange';
      case 'STOP':
        return 'volcano';
      case 'COMPLETE':
        return 'green';
      default:
        return 'blue';
    }
  }

  getRequestTypeLabel(type: RequestType): string {
    switch (type) {
      case 'EXTEND':
        return 'Gia hạn thực tập';
      case 'STOP':
        return 'Dừng thực tập';
      case 'COMPLETE':
        return 'Kết thúc thực tập';
      default:
        return type;
    }
  }

  getRequestStatusColor(status: RequestStatus): string {
    switch (status) {
      case 'PENDING':
        return 'processing';
      case 'APPROVED':
        return 'success';
      case 'REJECTED':
        return 'error';
      default:
        return status;
    }
  }

  getRequestStatusLabel(status: RequestStatus): string {
    switch (status) {
      case 'PENDING':
        return 'Chờ duyệt';
      case 'APPROVED':
        return 'Đã duyệt';
      case 'REJECTED':
        return 'Từ chối';
      default:
        return status;
    }
  }
}
