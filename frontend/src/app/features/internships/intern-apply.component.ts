import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzTagModule } from 'ng-zorro-antd/tag';

import {
  Internship,
  InternshipApplication,
  InternshipService,
} from '../../core/api/internship.service';

@Component({
  selector: 'app-intern-apply',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NzBadgeModule,
    NzButtonModule,
    NzCardModule,
    NzEmptyModule,
    NzFormModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzSpinModule,
    NzTableModule,
    NzTabsModule,
    NzTagModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="intern-apply-page feature-page-layout">
      <div class="page-header feature-page-header">
        <div class="header-titles">
          <h1 class="feature-page-title">Đăng ký Thực tập</h1>
          <p class="feature-page-subtitle">
            Khám phá các đợt thực tập đang mở và theo dõi tiến độ phê duyệt đơn đăng ký của bạn.
          </p>
        </div>
      </div>

      <nz-card [nzBordered]="false" class="main-card">
        <nz-tabs [(nzSelectedIndex)]="selectedTabIndex">
          <!-- TAB 1: CÁC ĐỢT THỰC TẬP ĐANG MỞ -->
          <nz-tab nzTitle="Đợt thực tập đang mở">
            <nz-spin [nzSpinning]="isLoadingOpen()">
              @if (openInternships().length > 0) {
                <div class="batches-grid">
                  @for (batch of openInternships(); track batch.id) {
                    <div class="batch-card">
                      <div class="batch-card__header">
                        <span class="batch-card__badge">Đang mở đăng ký</span>
                        <h2 class="batch-card__title">{{ batch.name }}</h2>
                      </div>
                      <p class="batch-card__desc">
                        {{ batch.description || 'Chưa có mô tả chi tiết cho đợt thực tập này.' }}
                      </p>
                      <div class="batch-card__meta">
                        <div class="meta-item">
                          <span nz-icon nzType="calendar" class="meta-icon"></span>
                          <span>Bắt đầu: {{ batch.start_date }}</span>
                        </div>
                        <div class="meta-item">
                          <span nz-icon nzType="clock-circle" class="meta-icon"></span>
                          <span>Kết thúc: {{ batch.end_date }}</span>
                        </div>
                      </div>
                      <div class="batch-card__actions">
                        @if (isApplied(batch.id)) {
                          <button nz-button nzType="default" disabled class="btn-applied">
                            <span nz-icon nzType="check"></span> Đã nộp đơn
                          </button>
                        } @else {
                          <button
                            nz-button
                            nzType="primary"
                            (click)="openApplyModal(batch)"
                            class="btn-apply"
                          >
                            <span nz-icon nzType="form"></span> Đăng ký tham gia
                          </button>
                        }
                      </div>
                    </div>
                  }
                </div>
              } @else {
                <nz-empty
                  nzNotFoundContent="Hiện tại không có đợt thực tập nào đang mở đăng ký."
                ></nz-empty>
              }
            </nz-spin>
          </nz-tab>

          <!-- TAB 2: ĐƠN ĐĂNG KÝ CỦA TÔI -->
          <nz-tab nzTitle="Đơn đăng ký của tôi">
            <nz-spin [nzSpinning]="isLoadingMyApps()">
              <!-- Desktop Table View -->
              <div class="desktop-only">
                <nz-table
                  #appsTable
                  [nzData]="myApplications()"
                  [nzBordered]="true"
                  nzSize="middle"
                  [nzScroll]="{ x: '750px' }"
                  class="itms-table"
                >
                  <thead>
                    <tr>
                      <th>Đợt thực tập</th>
                      <th>Lý do / Nguyện vọng</th>
                      <th>Ngày nộp</th>
                      <th>Trạng thái</th>
                      <th>Ghi chú từ Quản trị viên</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (app of appsTable.data; track app.id) {
                      <tr>
                        <td class="font-medium text-slate-800">
                          {{ app.internship_name || 'Đợt thực tập' }}
                        </td>
                        <td class="max-w-xs text-slate-600">{{ app.reason || '—' }}</td>
                        <td>{{ app.created_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                        <td>
                          @if (app.status === 'PENDING') {
                            <nz-tag nzColor="warning">Chờ phê duyệt</nz-tag>
                          } @else if (app.status === 'APPROVED') {
                            <nz-tag nzColor="success">Đã phê duyệt</nz-tag>
                          } @else if (app.status === 'REJECTED') {
                            <nz-tag nzColor="error">Bị từ chối</nz-tag>
                          }
                        </td>
                        <td>
                          @if (app.status === 'APPROVED') {
                            <span class="text-emerald-600 font-medium">
                              <span nz-icon nzType="check-circle"></span> Đã được tiếp nhận vào đợt.
                            </span>
                          } @else if (app.status === 'REJECTED') {
                            <span class="text-rose-600">
                              {{ app.review_note || 'Chưa đạt yêu cầu' }}
                            </span>
                          } @else {
                            <span class="text-slate-400">Đang chờ Admin xem xét</span>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </nz-table>
              </div>

              <!-- Mobile Card List View -->
              <div class="mobile-only">
                @if (myApplications().length === 0) {
                  <nz-empty nzNotFoundContent="Bạn chưa nộp đơn đăng ký nào."></nz-empty>
                } @else {
                  <div class="mobile-apps-list">
                    @for (app of myApplications(); track app.id) {
                      <div class="mobile-app-card">
                        <div class="mobile-app-header">
                          <strong class="mobile-app-title">{{
                            app.internship_name || 'Đợt thực tập'
                          }}</strong>
                          @if (app.status === 'PENDING') {
                            <nz-tag nzColor="warning">Chờ duyệt</nz-tag>
                          } @else if (app.status === 'APPROVED') {
                            <nz-tag nzColor="success">Đã duyệt</nz-tag>
                          } @else if (app.status === 'REJECTED') {
                            <nz-tag nzColor="error">Bị từ chối</nz-tag>
                          }
                        </div>
                        <div class="mobile-app-body">
                          <div class="mobile-app-row">
                            <span class="row-label">Ngày nộp:</span>
                            <span class="row-val">{{
                              app.created_at | date: 'dd/MM/yyyy HH:mm'
                            }}</span>
                          </div>
                          @if (app.reason) {
                            <div class="mobile-app-row">
                              <span class="row-label">Nguyện vọng:</span>
                              <span class="row-val">{{ app.reason }}</span>
                            </div>
                          }
                          <div class="mobile-app-row">
                            <span class="row-label">Phản hồi:</span>
                            <span class="row-val">
                              @if (app.status === 'APPROVED') {
                                <span class="text-emerald-600 font-medium">
                                  <span nz-icon nzType="check-circle"></span> Đã tiếp nhận vào đợt
                                </span>
                              } @else if (app.status === 'REJECTED') {
                                <span class="text-rose-600">{{
                                  app.review_note || 'Chưa đạt yêu cầu'
                                }}</span>
                              } @else {
                                <span class="text-slate-400">Đang chờ Admin xem xét</span>
                              }
                            </span>
                          </div>
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>
            </nz-spin>
          </nz-tab>
        </nz-tabs>
      </nz-card>

      <!-- MODAL NỘP ĐƠN ĐĂNG KÝ -->
      <nz-modal
        [(nzVisible)]="isModalVisible"
        [nzTitle]="'Đăng ký tham gia ' + (selectedBatch()?.name || '')"
        (nzOnCancel)="closeApplyModal()"
        (nzOnOk)="submitApplication()"
        [nzOkLoading]="isSubmitting()"
        nzOkText="Gửi đơn đăng ký"
        nzCancelText="Hủy"
        [nzWidth]="'min(540px, calc(100vw - 24px))'"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="applyForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label>Lý do & Nguyện vọng tham gia (Không bắt buộc)</nz-form-label>
              <nz-form-control>
                <textarea
                  nz-input
                  formControlName="reason"
                  rows="4"
                  placeholder="Giới thiệu ngắn gọn bản thân, kỹ năng hoặc lý do bạn muốn tham gia đợt thực tập này (tùy chọn)..."
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
      .intern-apply-page {
        padding: 0 0 24px 0;
      }
      .page-header {
        margin-bottom: 24px;
      }
      .feature-page-title {
        font-size: 22px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 6px;
      }
      .feature-page-subtitle {
        color: #64748b;
        font-size: 14px;
        margin: 0;
      }
      .main-card {
        border-radius: 16px;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
      }
      .batches-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
        gap: 20px;
        padding-top: 12px;
      }
      .batch-card {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        background: #fff;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition:
          box-shadow 0.2s,
          transform 0.2s;
      }
      .batch-card:hover {
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08);
        transform: translateY(-2px);
      }
      .batch-card__badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 9999px;
        background: #dcfce7;
        color: #15803d;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 10px;
      }
      .batch-card__title {
        font-size: 17px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 10px;
      }
      .batch-card__desc {
        font-size: 13.5px;
        color: #64748b;
        line-height: 1.5;
        margin-bottom: 16px;
        flex-grow: 1;
      }
      .batch-card__meta {
        background: #f8fafc;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 16px;
        font-size: 13px;
        color: #475569;
      }
      .meta-item {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
      }
      .meta-item:last-child {
        margin-bottom: 0;
      }
      .meta-icon {
        color: #64748b;
      }
      .batch-card__actions {
        display: flex;
        justify-content: flex-end;
      }
      .btn-apply {
        background: #e11d48;
        border-color: #e11d48;
        font-weight: 600;
        border-radius: 8px;
      }
      .btn-apply:hover {
        background: #be123c !important;
        border-color: #be123c !important;
      }
      .btn-applied {
        border-radius: 8px;
        color: #15803d;
        border-color: #86efac;
        background: #f0fdf4;
      }
      .itms-table th {
        font-weight: 600;
        background: #f8fafc;
        color: #334155;
      }
      .desktop-only {
        display: block;
      }
      .mobile-only {
        display: none;
      }

      .mobile-apps-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding-top: 8px;
      }
      .mobile-app-card {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      }
      .mobile-app-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 8px;
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 1px solid #f1f5f9;
      }
      .mobile-app-title {
        font-size: 15px;
        color: #1e293b;
        word-break: break-word;
      }
      .mobile-app-body {
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 13px;
      }
      .mobile-app-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 8px;
      }
      .row-label {
        color: #64748b;
        font-size: 12px;
        flex-shrink: 0;
      }
      .row-val {
        color: #1e293b;
        text-align: right;
        word-break: break-word;
      }

      @media (max-width: 768px) {
        .desktop-only {
          display: none !important;
        }
        .mobile-only {
          display: block !important;
        }
      }

      @media (max-width: 640px) {
        .batches-grid {
          grid-template-columns: 1fr;
          gap: 12px;
        }
        .batch-card {
          padding: 14px;
        }
        .feature-page-title {
          font-size: 18px;
        }
      }
    `,
  ],
})
export class InternApplyComponent implements OnInit {
  private readonly internshipService = inject(InternshipService);
  private readonly message = inject(NzMessageService);
  private readonly fb = inject(FormBuilder);
  private readonly cdr = inject(ChangeDetectorRef);

  protected selectedTabIndex = 0;
  protected openInternships = signal<Internship[]>([]);
  protected myApplications = signal<InternshipApplication[]>([]);
  protected isLoadingOpen = signal<boolean>(false);
  protected isLoadingMyApps = signal<boolean>(false);
  protected isSubmitting = signal<boolean>(false);
  protected isModalVisible = false;
  protected selectedBatch = signal<Internship | null>(null);

  protected applyForm = this.fb.group({
    reason: ['', [Validators.maxLength(2000)]],
  });

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loadOpenBatches();
    this.loadMyApps();
  }

  loadOpenBatches(): void {
    this.isLoadingOpen.set(true);
    this.internshipService.getOpenInternships().subscribe({
      next: (batches) => {
        this.openInternships.set(batches);
        this.isLoadingOpen.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoadingOpen.set(false);
        this.message.error('Không thể tải danh sách đợt thực tập đang mở.');
        this.cdr.markForCheck();
      },
    });
  }

  loadMyApps(): void {
    this.isLoadingMyApps.set(true);
    this.internshipService.getMyApplications().subscribe({
      next: (apps) => {
        this.myApplications.set(apps);
        this.isLoadingMyApps.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoadingMyApps.set(false);
        this.message.error('Không thể tải danh sách đơn đăng ký của bạn.');
        this.cdr.markForCheck();
      },
    });
  }

  isApplied(batchId: string): boolean {
    return this.myApplications().some(
      (a) => a.internship_id === batchId && (a.status === 'PENDING' || a.status === 'APPROVED'),
    );
  }

  openApplyModal(batch: Internship): void {
    this.selectedBatch.set(batch);
    this.applyForm.reset();
    this.isModalVisible = true;
  }

  closeApplyModal(): void {
    this.isModalVisible = false;
    this.selectedBatch.set(null);
  }

  submitApplication(): void {
    if (this.applyForm.invalid) {
      this.applyForm.markAllAsTouched();
      return;
    }

    const batch = this.selectedBatch();
    if (!batch) return;

    const reason = this.applyForm.value.reason?.trim() || null;
    this.isSubmitting.set(true);

    this.internshipService.applyInternship(batch.id, { reason }).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.message.success('Đã gửi đơn đăng ký thành công! Vui lòng chờ Admin phê duyệt.');
        this.closeApplyModal();
        this.loadMyApps();
        this.selectedTabIndex = 1; // Chuyển sang tab đơn đăng ký của tôi
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isSubmitting.set(false);
        const detail =
          err.error?.detail || err.error?.error?.message || 'Gửi đơn đăng ký thất bại.';
        this.message.error(detail);
        this.cdr.markForCheck();
      },
    });
  }
}
