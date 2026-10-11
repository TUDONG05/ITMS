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
import { FormsModule } from '@angular/forms';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzAvatarModule } from 'ng-zorro-antd/avatar';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDatePickerModule } from 'ng-zorro-antd/date-picker';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTimelineModule } from 'ng-zorro-antd/timeline';

import {
  InternshipProposalCreatePayload,
  InternshipProposalItem,
  InternshipStatusHistoryItem,
  MentorInternListItem,
  MentorService,
} from '../../core/api/mentor.service';

@Component({
  selector: 'app-mentor-internship-status',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    NzAlertModule,
    NzAvatarModule,
    NzBadgeModule,
    NzButtonModule,
    NzCardModule,
    NzDatePickerModule,
    NzDividerModule,
    NzDrawerModule,
    NzEmptyModule,
    NzFormModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzSelectModule,
    NzSpinModule,
    NzTableModule,
    NzTabsModule,
    NzTagModule,
    NzTimelineModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="internship-status-container">
      <!-- HEADER -->
      <div class="header-section">
        <div class="header-title">
          <h1>Quản lý Trạng thái Thực tập</h1>
          <p>
            Theo dõi trạng thái, xem lịch sử và đề xuất gia hạn, dừng hoặc kết thúc quá trình thực
            tập của Intern phụ trách.
          </p>
        </div>
        <div class="header-actions">
          <button nz-button nzType="default" (click)="loadAllData()" [nzLoading]="isLoading()">
            <span nz-icon nzType="reload"></span> Làm mới
          </button>
        </div>
      </div>

      <!-- METRIC CARDS -->
      <div class="metrics-grid">
        <nz-card class="metric-card" [nzBordered]="false">
          <div class="metric-card-body">
            <div class="metric-icon metric-icon--blue">
              <span nz-icon nzType="team"></span>
            </div>
            <div class="metric-info">
              <span class="metric-label">Tổng Intern phụ trách</span>
              <strong class="metric-value">{{ interns().length }}</strong>
            </div>
          </div>
        </nz-card>

        <nz-card class="metric-card" [nzBordered]="false">
          <div class="metric-card-body">
            <div class="metric-icon metric-icon--green">
              <span nz-icon nzType="check-circle"></span>
            </div>
            <div class="metric-info">
              <span class="metric-label">Đang thực tập</span>
              <strong class="metric-value">{{ activeInternsCount() }}</strong>
            </div>
          </div>
        </nz-card>

        <nz-card class="metric-card" [nzBordered]="false">
          <div class="metric-card-body">
            <div class="metric-icon metric-icon--orange">
              <span nz-icon nzType="clock-circle"></span>
            </div>
            <div class="metric-info">
              <span class="metric-label">Đề xuất chờ duyệt</span>
              <strong class="metric-value">{{ pendingProposalsCount() }}</strong>
            </div>
          </div>
        </nz-card>

        <nz-card class="metric-card" [nzBordered]="false">
          <div class="metric-card-body">
            <div class="metric-icon metric-icon--purple">
              <span nz-icon nzType="flag"></span>
            </div>
            <div class="metric-info">
              <span class="metric-label">Đã hoàn thành</span>
              <strong class="metric-value">{{ completedInternsCount() }}</strong>
            </div>
          </div>
        </nz-card>
      </div>

      <!-- MAIN TABS -->
      <nz-card [nzBordered]="false" class="main-card">
        <nz-tabs [(nzSelectedIndex)]="selectedTabIndex">
          <!-- TAB 1: DANH SÁCH INTERN PHỤ TRÁCH -->
          <nz-tab nzTitle="Thực tập sinh phụ trách">
            <!-- FILTER BAR -->
            <div class="filter-bar">
              <div class="filter-inputs">
                <nz-input-group nzPrefixIcon="search" class="search-input">
                  <input
                    type="text"
                    nz-input
                    placeholder="Tìm theo tên hoặc email thực tập sinh..."
                    [(ngModel)]="searchQuery"
                    (ngModelChange)="onFilterChange()"
                  />
                </nz-input-group>

                <nz-select
                  class="status-select"
                  [(ngModel)]="statusFilter"
                  (ngModelChange)="onFilterChange()"
                  nzPlaceHolder="Trạng thái thực tập"
                  nzAllowClear
                >
                  <nz-option nzValue="ACTIVE" nzLabel="Đang thực tập (ACTIVE)"></nz-option>
                  <nz-option nzValue="EXTENDED" nzLabel="Đã gia hạn (EXTENDED)"></nz-option>
                  <nz-option nzValue="STOPPED" nzLabel="Đã dừng (STOPPED)"></nz-option>
                  <nz-option nzValue="COMPLETED" nzLabel="Đã hoàn thành (COMPLETED)"></nz-option>
                </nz-select>
              </div>
            </div>

            <!-- INTERN TABLE -->
            <nz-table
              #internTable
              [nzData]="filteredInterns()"
              [nzLoading]="isLoading()"
              [nzPageSize]="10"
              nzSize="middle"
              class="intern-table"
            >
              <thead>
                <tr>
                  <th>Thực tập sinh</th>
                  <th>Đợt thực tập</th>
                  <th>Thời gian</th>
                  <th>Trạng thái thực tập</th>
                  <th>Đề xuất hiện tại</th>
                  <th nzAlign="center" style="width: 220px;">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                @for (intern of internTable.data; track intern.id) {
                  <tr>
                    <td>
                      <div class="user-cell">
                        <nz-avatar
                          [nzSrc]="intern.intern_avatar_url || undefined"
                          [nzText]="getInitials(intern.intern_name)"
                          class="user-avatar"
                        ></nz-avatar>
                        <div class="user-meta">
                          <strong class="user-name">{{ intern.intern_name }}</strong>
                          <span class="user-email">{{ intern.intern_email }}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span class="batch-badge">{{ intern.internship_name || 'N/A' }}</span>
                    </td>
                    <td>
                      <div class="date-cell">
                        <span>{{
                          intern.start_date ? (intern.start_date | date: 'dd/MM/yyyy') : '—'
                        }}</span>
                        <span class="date-separator">→</span>
                        <span>{{
                          intern.end_date ? (intern.end_date | date: 'dd/MM/yyyy') : '—'
                        }}</span>
                      </div>
                    </td>
                    <td>
                      <nz-tag [nzColor]="getStatusTagColor(intern.status)">
                        {{ getStatusLabel(intern.status) }}
                      </nz-tag>
                    </td>
                    <td>
                      @if (getPendingProposalForIntern(intern.id); as pending) {
                        <nz-tag nzColor="processing" class="pending-tag">
                          <span nz-icon nzType="sync" nzSpin></span>
                          Chờ duyệt {{ getProposalTypeLabel(pending.type) }}
                        </nz-tag>
                      } @else {
                        <span class="text-muted">Không có đề xuất chờ</span>
                      }
                    </td>
                    <td nzAlign="center">
                      <div class="action-buttons">
                        <button
                          nz-button
                          nzType="primary"
                          nzSize="small"
                          (click)="openProposalModal(intern)"
                          [disabled]="isProposalDisabled(intern)"
                          [title]="getProposalDisabledTooltip(intern)"
                        >
                          <span nz-icon nzType="form"></span> Đề xuất
                        </button>
                        <button
                          nz-button
                          nzType="default"
                          nzSize="small"
                          (click)="openHistoryDrawer(intern)"
                        >
                          <span nz-icon nzType="history"></span> Lịch sử
                        </button>
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </nz-table>
          </nz-tab>

          <!-- TAB 2: ĐỀ XUẤT ĐÃ GỬI -->
          <nz-tab nzTitle="Đề xuất đã gửi ({{ proposals().length }})">
            <div class="filter-bar">
              <nz-select
                class="status-select"
                [(ngModel)]="proposalStatusFilter"
                (ngModelChange)="onProposalFilterChange()"
                nzPlaceHolder="Lọc trạng thái đề xuất"
                nzAllowClear
              >
                <nz-option nzValue="PENDING" nzLabel="Chờ duyệt (PENDING)"></nz-option>
                <nz-option nzValue="APPROVED" nzLabel="Đã duyệt (APPROVED)"></nz-option>
                <nz-option nzValue="REJECTED" nzLabel="Đã từ chối (REJECTED)"></nz-option>
              </nz-select>
            </div>

            <nz-table
              #proposalTable
              [nzData]="filteredProposals()"
              [nzLoading]="isLoadingProposals()"
              [nzPageSize]="10"
              nzSize="middle"
            >
              <thead>
                <tr>
                  <th>Thực tập sinh</th>
                  <th>Loại đề xuất</th>
                  <th>Ngày kết thúc mới</th>
                  <th>Lý do đề xuất</th>
                  <th>Trạng thái</th>
                  <th>Ngày tạo</th>
                  <th>Phản hồi quản trị</th>
                </tr>
              </thead>
              <tbody>
                @for (item of proposalTable.data; track item.id) {
                  <tr>
                    <td>
                      <strong>{{ item.intern_name || 'Intern' }}</strong>
                      <div class="text-muted small">{{ item.intern_email || '' }}</div>
                    </td>
                    <td>
                      <nz-tag [nzColor]="getProposalTypeColor(item.type)">
                        {{ getProposalTypeLabel(item.type) }}
                      </nz-tag>
                    </td>
                    <td>
                      @if (item.type === 'EXTEND' && item.requested_end_date) {
                        <span>{{ item.requested_end_date | date: 'dd/MM/yyyy' }}</span>
                      } @else {
                        <span>—</span>
                      }
                    </td>
                    <td>
                      <span class="reason-text" [title]="item.reason">{{ item.reason }}</span>
                    </td>
                    <td>
                      <nz-tag [nzColor]="getReviewStatusColor(item.status)">
                        {{ getReviewStatusLabel(item.status) }}
                      </nz-tag>
                    </td>
                    <td>
                      {{ item.created_at | date: 'dd/MM/yyyy HH:mm' }}
                    </td>
                    <td>
                      @if (item.review_note) {
                        <span class="note-text" [title]="item.review_note">{{
                          item.review_note
                        }}</span>
                      } @else {
                        <span class="text-muted">—</span>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </nz-table>
          </nz-tab>
        </nz-tabs>
      </nz-card>

      <!-- PROPOSAL MODAL -->
      <nz-modal
        [(nzVisible)]="isModalVisible"
        nzTitle="Tạo đề xuất thay đổi trạng thái thực tập"
        (nzOnCancel)="closeProposalModal()"
        (nzOnOk)="submitProposal()"
        [nzOkLoading]="isSubmitting()"
        [nzOkDisabled]="isSubmitDisabled()"
        nzOkText="Gửi đề xuất"
        nzCancelText="Hủy"
        [nzWidth]="540"
      >
        <ng-container *nzModalContent>
          @if (selectedIntern(); as intern) {
            <div class="modal-intern-card">
              <div class="modal-intern-header">
                <nz-avatar [nzText]="getInitials(intern.intern_name)"></nz-avatar>
                <div>
                  <strong>{{ intern.intern_name }}</strong>
                  <div class="text-muted">{{ intern.intern_email }}</div>
                </div>
              </div>
              <nz-divider style="margin: 12px 0;"></nz-divider>
              <div class="modal-intern-details">
                <div>
                  <span>Đợt:</span> <b>{{ intern.internship_name }}</b>
                </div>
                <div>
                  <span>Trạng thái hiện tại:</span>
                  <nz-tag [nzColor]="getStatusTagColor(intern.status)">{{
                    getStatusLabel(intern.status)
                  }}</nz-tag>
                </div>
                <div>
                  <span>Hạn kết thúc hiện tại:</span>
                  <b>{{ intern.end_date ? (intern.end_date | date: 'dd/MM/yyyy') : '—' }}</b>
                </div>
              </div>
            </div>

            <!-- BR-10 WARNING ALERT -->
            @if (hasPendingExtendProposal(intern.id)) {
              <nz-alert
                nzType="warning"
                nzShowIcon
                nzMessage="Đang có đề xuất gia hạn chờ duyệt (BR-10)"
                nzDescription="Thực tập sinh này đã có một đề xuất gia hạn đang trong trạng thái chờ xử lý. Tùy chọn Gia hạn sẽ bị khóa cho đến khi đề xuất trước đó được phê duyệt hoặc từ chối."
                style="margin-bottom: 16px;"
              ></nz-alert>
            }

            <form nz-form nzLayout="vertical" style="margin-top: 16px;">
              <nz-form-item>
                <nz-form-label nzRequired>Loại đề xuất</nz-form-label>
                <nz-form-control>
                  <nz-select
                    [(ngModel)]="proposalType"
                    name="proposalType"
                    (ngModelChange)="onTypeChange()"
                    style="width: 100%;"
                  >
                    <nz-option
                      nzValue="EXTEND"
                      nzLabel="Gia hạn thực tập"
                      [nzDisabled]="hasPendingExtendProposal(intern.id)"
                    ></nz-option>
                    <nz-option nzValue="STOP" nzLabel="Dừng thực tập (Hủy / Thôi việc)"></nz-option>
                    <nz-option
                      nzValue="COMPLETE"
                      nzLabel="Kết thúc thực tập (Hoàn thành)"
                    ></nz-option>
                  </nz-select>
                </nz-form-control>
              </nz-form-item>

              <!-- REQUESTED END DATE (IF EXTEND) -->
              @if (proposalType === 'EXTEND') {
                <nz-form-item>
                  <nz-form-label nzRequired>Ngày kết thúc mới đề xuất</nz-form-label>
                  <nz-form-control nzExtra="Ngày kết thúc đề xuất phải sau ngày kết thúc hiện tại">
                    <nz-date-picker
                      [(ngModel)]="proposalEndDate"
                      name="proposalEndDate"
                      nzFormat="dd/MM/yyyy"
                      style="width: 100%;"
                      [nzDisabledDate]="disabledEndDate"
                      nzPlaceHolder="Chọn ngày kết thúc mới"
                    ></nz-date-picker>
                  </nz-form-control>
                </nz-form-item>
              }

              <!-- REASON -->
              <nz-form-item>
                <nz-form-label nzRequired>Lý do đề xuất</nz-form-label>
                <nz-form-control
                  nzExtra="Tối đa 1000 ký tự. Vui lòng nêu rõ lý do để Quản lý phê duyệt."
                >
                  <textarea
                    nz-input
                    [(ngModel)]="proposalReason"
                    name="proposalReason"
                    [rows]="4"
                    maxlength="1000"
                    placeholder="Nhập chi tiết lý do (ví dụ: Thực tập sinh cần thêm thời gian hoàn thành đồ án, hoặc vi phạm quy chế,...)"
                  ></textarea>
                </nz-form-control>
              </nz-form-item>
            </form>
          }
        </ng-container>
      </nz-modal>

      <!-- STATUS HISTORY DRAWER -->
      <nz-drawer
        [nzVisible]="isDrawerVisible"
        nzPlacement="right"
        [nzWidth]="500"
        [nzTitle]="drawerTitle"
        (nzOnClose)="closeHistoryDrawer()"
      >
        <ng-container *nzDrawerContent>
          @if (isLoadingHistory()) {
            <div class="drawer-loading">
              <nz-spin nzSimple nzSize="large"></nz-spin>
            </div>
          } @else if (historyItems().length === 0) {
            <nz-empty nzNotFoundContent="Không có lịch sử trạng thái"></nz-empty>
          } @else {
            <div class="history-timeline-container">
              <nz-timeline>
                @for (item of historyItems(); track item.id) {
                  <nz-timeline-item [nzColor]="getTimelineItemColor(item)">
                    <div class="timeline-entry">
                      <div class="timeline-header">
                        <nz-tag [nzColor]="getHistoryActionColor(item.action)">
                          {{ getHistoryActionLabel(item.action) }}
                        </nz-tag>
                        @if (item.proposal_status) {
                          <nz-tag [nzColor]="getReviewStatusColor(item.proposal_status)">
                            {{ getReviewStatusLabel(item.proposal_status) }}
                          </nz-tag>
                        }
                      </div>

                      <div class="timeline-body">
                        <div class="status-transition">
                          <span class="status-box">{{ item.from_status || 'Khởi tạo' }}</span>
                          <span class="status-arrow">→</span>
                          <span class="status-box status-box--to">{{ item.to_status }}</span>
                        </div>

                        @if (item.requested_end_date) {
                          <div class="timeline-field">
                            <span class="field-label">Ngày kết thúc đề xuất:</span>
                            <span>{{ item.requested_end_date | date: 'dd/MM/yyyy' }}</span>
                          </div>
                        }

                        @if (item.reason) {
                          <div class="timeline-field">
                            <span class="field-label">Lý do:</span>
                            <span class="field-value">{{ item.reason }}</span>
                          </div>
                        }

                        @if (item.review_note) {
                          <div class="timeline-field timeline-field--note">
                            <span class="field-label">Ghi chú duyệt:</span>
                            <span class="field-value">{{ item.review_note }}</span>
                          </div>
                        }

                        <div class="timeline-meta">
                          @if (item.requested_by_name) {
                            <span
                              >Đề xuất: <b>{{ item.requested_by_name }}</b></span
                            >
                          }
                          @if (item.reviewed_by_name) {
                            <span>
                              • Duyệt: <b>{{ item.reviewed_by_name }}</b></span
                            >
                          }
                          <div class="timestamp">
                            {{ item.changed_at | date: 'dd/MM/yyyy HH:mm' }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </nz-timeline-item>
                }
              </nz-timeline>
            </div>
          }
        </ng-container>
      </nz-drawer>
    </div>
  `,
  styles: [
    `
      .internship-status-container {
        display: flex;
        flex-direction: column;
        gap: 20px;
        padding-bottom: 24px;
      }

      .header-section {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 16px;
      }

      .header-title h1 {
        font-size: 24px;
        font-weight: 700;
        margin: 0 0 6px 0;
        color: #1f2937;
      }

      .header-title p {
        margin: 0;
        color: #6b7280;
        font-size: 14px;
      }

      .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
      }

      .metric-card {
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }

      .metric-card-body {
        display: flex;
        align-items: center;
        gap: 16px;
      }

      .metric-icon {
        width: 48px;
        height: 48px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
      }

      .metric-icon--blue {
        background: #e6f7ff;
        color: #1890ff;
      }

      .metric-icon--green {
        background: #f6ffed;
        color: #52c41a;
      }

      .metric-icon--orange {
        background: #fff7e6;
        color: #fa8c16;
      }

      .metric-icon--purple {
        background: #f9f0ff;
        color: #722ed1;
      }

      .metric-info {
        display: flex;
        flex-direction: column;
      }

      .metric-label {
        font-size: 13px;
        color: #6b7280;
      }

      .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #111827;
      }

      .main-card {
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }

      .filter-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        gap: 12px;
        flex-wrap: wrap;
      }

      .filter-inputs {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        flex: 1;
      }

      .search-input {
        max-width: 340px;
        width: 100%;
      }

      .status-select {
        min-width: 220px;
      }

      .user-cell {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .user-avatar {
        background-color: #1890ff;
        flex-shrink: 0;
      }

      .user-meta {
        display: flex;
        flex-direction: column;
      }

      .user-name {
        color: #111827;
        font-size: 14px;
      }

      .user-email {
        font-size: 12px;
        color: #6b7280;
      }

      .batch-badge {
        font-weight: 500;
        color: #374151;
      }

      .date-cell {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: #4b5563;
      }

      .date-separator {
        color: #9ca3af;
      }

      .pending-tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }

      .action-buttons {
        display: flex;
        justify-content: center;
        gap: 8px;
      }

      .modal-intern-card {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 16px;
      }

      .modal-intern-header {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .modal-intern-details {
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 13px;
        color: #374151;
      }

      .text-muted {
        color: #9ca3af;
      }

      .small {
        font-size: 12px;
      }

      .reason-text,
      .note-text {
        display: inline-block;
        max-width: 240px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .drawer-loading {
        display: flex;
        justify-content: center;
        padding: 40px 0;
      }

      .history-timeline-container {
        padding: 8px 0;
      }

      .timeline-entry {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 8px;
      }

      .timeline-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }

      .status-transition {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        font-size: 13px;
        margin-bottom: 8px;
      }

      .status-box {
        padding: 2px 8px;
        background: #e5e7eb;
        border-radius: 4px;
        color: #374151;
      }

      .status-box--to {
        background: #dbeafe;
        color: #1e40af;
      }

      .status-arrow {
        color: #9ca3af;
      }

      .timeline-field {
        font-size: 13px;
        margin-bottom: 4px;
        display: flex;
        flex-direction: column;
      }

      .timeline-field--note {
        background: #fffbe6;
        border-left: 3px solid #faad14;
        padding: 4px 8px;
        border-radius: 0 4px 4px 0;
      }

      .field-label {
        font-weight: 500;
        color: #6b7280;
      }

      .field-value {
        color: #1f2937;
      }

      .timeline-meta {
        margin-top: 8px;
        font-size: 12px;
        color: #6b7280;
        border-top: 1px dashed #e5e7eb;
        padding-top: 6px;
      }

      .timestamp {
        color: #9ca3af;
        margin-top: 2px;
      }

      @media (max-width: 768px) {
        .header-section {
          flex-direction: column;
        }

        .filter-inputs {
          flex-direction: column;
        }

        .search-input,
        .status-select {
          max-width: 100%;
          width: 100%;
        }
      }
    `,
  ],
})
export class MentorInternshipStatusComponent implements OnInit {
  private readonly mentorService = inject(MentorService);
  private readonly message = inject(NzMessageService);
  private readonly cdr = inject(ChangeDetectorRef);

  // Signals
  readonly interns = signal<MentorInternListItem[]>([]);
  readonly proposals = signal<InternshipProposalItem[]>([]);
  readonly isLoading = signal(false);
  readonly isLoadingProposals = signal(false);
  readonly isLoadingHistory = signal(false);
  readonly isSubmitting = signal(false);

  // Tab & Filters
  selectedTabIndex = 0;
  searchQuery = '';
  statusFilter: string | null = null;
  proposalStatusFilter: string | null = null;

  // Selected intern & Modal state
  readonly selectedIntern = signal<MentorInternListItem | null>(null);
  isModalVisible = false;
  proposalType: 'EXTEND' | 'STOP' | 'COMPLETE' = 'EXTEND';
  proposalEndDate: Date | null = null;
  proposalReason = '';

  // History Drawer state
  isDrawerVisible = false;
  drawerTitle = 'Lịch sử trạng thái';
  readonly historyItems = signal<InternshipStatusHistoryItem[]>([]);

  // Computed metrics
  readonly activeInternsCount = computed(() => {
    return this.interns().filter((i) => i.status === 'ACTIVE' || i.status === 'EXTENDED').length;
  });

  readonly pendingProposalsCount = computed(() => {
    return this.proposals().filter((p) => p.status === 'PENDING').length;
  });

  readonly completedInternsCount = computed(() => {
    return this.interns().filter((i) => i.status === 'COMPLETED').length;
  });

  // Filtered interns list
  readonly filteredInterns = computed(() => {
    let list = this.interns();
    const query = this.searchQuery.trim().toLowerCase();
    if (query) {
      list = list.filter(
        (i) =>
          i.intern_name.toLowerCase().includes(query) ||
          i.intern_email.toLowerCase().includes(query),
      );
    }
    if (this.statusFilter) {
      list = list.filter((i) => i.status === this.statusFilter);
    }
    return list;
  });

  // Filtered proposals list
  readonly filteredProposals = computed(() => {
    let list = this.proposals();
    if (this.proposalStatusFilter) {
      list = list.filter((p) => p.status === this.proposalStatusFilter);
    }
    return list;
  });

  ngOnInit(): void {
    this.loadAllData();
  }

  loadAllData(): void {
    this.loadInterns();
    this.loadProposals();
  }

  loadInterns(): void {
    this.isLoading.set(true);
    this.mentorService.getInterns().subscribe({
      next: (data) => {
        this.interns.set(data);
        this.isLoading.set(false);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.message.error(
          'Không thể tải danh sách thực tập sinh: ' + (err.error?.detail || err.message),
        );
        this.isLoading.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  loadProposals(): void {
    this.isLoadingProposals.set(true);
    this.mentorService.getMentorProposals().subscribe({
      next: (data) => {
        this.proposals.set(data);
        this.isLoadingProposals.set(false);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.message.error(
          'Không thể tải danh sách đề xuất: ' + (err.error?.detail || err.message),
        );
        this.isLoadingProposals.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  onFilterChange(): void {
    this.cdr.markForCheck();
  }

  onProposalFilterChange(): void {
    this.cdr.markForCheck();
  }

  getPendingProposalForIntern(internId: string): InternshipProposalItem | undefined {
    return this.proposals().find(
      (p) =>
        (p.internship_member_id === internId || p.intern_id === internId) && p.status === 'PENDING',
    );
  }

  hasPendingExtendProposal(internId: string): boolean {
    return this.proposals().some(
      (p) =>
        (p.internship_member_id === internId || p.intern_id === internId) &&
        p.type === 'EXTEND' &&
        p.status === 'PENDING',
    );
  }

  isProposalDisabled(intern: MentorInternListItem): boolean {
    // Disabled if already completed or stopped
    return intern.status === 'COMPLETED' || intern.status === 'STOPPED';
  }

  getProposalDisabledTooltip(intern: MentorInternListItem): string {
    if (intern.status === 'COMPLETED') {
      return 'Thực tập sinh đã hoàn thành kỳ thực tập';
    }
    if (intern.status === 'STOPPED') {
      return 'Thực tập sinh đã dừng thực tập';
    }
    return '';
  }

  openProposalModal(intern: MentorInternListItem): void {
    this.selectedIntern.set(intern);
    this.proposalReason = '';
    this.proposalEndDate = null;

    // If intern has pending extend proposal, default to STOP or COMPLETE
    if (this.hasPendingExtendProposal(intern.id)) {
      this.proposalType = 'COMPLETE';
    } else {
      this.proposalType = 'EXTEND';
      // Default end date + 30 days
      if (intern.end_date) {
        const d = new Date(intern.end_date);
        d.setDate(d.getDate() + 30);
        this.proposalEndDate = d;
      }
    }
    this.isModalVisible = true;
    this.cdr.markForCheck();
  }

  closeProposalModal(): void {
    this.isModalVisible = false;
    this.selectedIntern.set(null);
    this.cdr.markForCheck();
  }

  onTypeChange(): void {
    this.cdr.markForCheck();
  }

  disabledEndDate = (current: Date): boolean => {
    const intern = this.selectedIntern();
    if (!intern || !current) return false;
    const baseDate = intern.end_date ? new Date(intern.end_date) : new Date();
    return current.getTime() <= baseDate.getTime();
  };

  isSubmitDisabled(): boolean {
    if (!this.proposalReason || !this.proposalReason.trim()) {
      return true;
    }
    if (this.proposalType === 'EXTEND' && !this.proposalEndDate) {
      return true;
    }
    return false;
  }

  submitProposal(): void {
    const intern = this.selectedIntern();
    if (!intern) return;

    if (!this.proposalReason || !this.proposalReason.trim()) {
      this.message.warning('Vui lòng nhập lý do đề xuất');
      return;
    }

    if (this.proposalType === 'EXTEND') {
      if (!this.proposalEndDate) {
        this.message.warning('Vui lòng chọn ngày kết thúc mới cho đề xuất gia hạn');
        return;
      }
      if (this.hasPendingExtendProposal(intern.id)) {
        this.message.error('Đã có yêu cầu gia hạn đang chờ xử lý (BR-10)');
        return;
      }
    }

    const payload: InternshipProposalCreatePayload = {
      member_id: intern.id,
      type: this.proposalType,
      reason: this.proposalReason.trim(),
      requested_end_date:
        this.proposalType === 'EXTEND' && this.proposalEndDate
          ? this.formatDateISO(this.proposalEndDate)
          : null,
    };

    this.isSubmitting.set(true);
    this.mentorService.createProposal(payload).subscribe({
      next: () => {
        this.message.success('Đã gửi đề xuất thành công! Quản lý sẽ sớm phê duyệt.');
        this.isSubmitting.set(false);
        this.closeProposalModal();
        this.loadAllData();
      },
      error: (err) => {
        const detail = err.error?.detail || err.message || 'Lỗi gửi đề xuất';
        this.message.error(detail);
        this.isSubmitting.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  openHistoryDrawer(intern: MentorInternListItem): void {
    this.drawerTitle = `Lịch sử trạng thái: ${intern.intern_name}`;
    this.isDrawerVisible = true;
    this.isLoadingHistory.set(true);
    this.historyItems.set([]);

    this.mentorService.getInternStatusHistory(intern.id).subscribe({
      next: (items) => {
        this.historyItems.set(items);
        this.isLoadingHistory.set(false);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.message.error(
          'Không thể tải lịch sử trạng thái: ' + (err.error?.detail || err.message),
        );
        this.isLoadingHistory.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  closeHistoryDrawer(): void {
    this.isDrawerVisible = false;
    this.cdr.markForCheck();
  }

  private formatDateISO(d: Date): string {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  getInitials(name: string): string {
    if (!name) return 'IN';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  getStatusTagColor(status: string): string {
    switch (status) {
      case 'ACTIVE':
        return 'blue';
      case 'EXTENDED':
        return 'cyan';
      case 'COMPLETED':
        return 'green';
      case 'STOPPED':
        return 'red';
      default:
        return 'default';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'ACTIVE':
        return 'Đang thực tập';
      case 'EXTENDED':
        return 'Đã gia hạn';
      case 'COMPLETED':
        return 'Đã hoàn thành';
      case 'STOPPED':
        return 'Đã dừng';
      default:
        return status;
    }
  }

  getProposalTypeColor(type: string): string {
    switch (type) {
      case 'EXTEND':
        return 'cyan';
      case 'COMPLETE':
        return 'green';
      case 'STOP':
      case 'TERMINATE':
        return 'red';
      default:
        return 'blue';
    }
  }

  getProposalTypeLabel(type: string): string {
    switch (type) {
      case 'EXTEND':
        return 'Gia hạn';
      case 'COMPLETE':
        return 'Kết thúc';
      case 'STOP':
      case 'TERMINATE':
        return 'Dừng thực tập';
      default:
        return type;
    }
  }

  getReviewStatusColor(status: string): string {
    switch (status) {
      case 'APPROVED':
        return 'success';
      case 'REJECTED':
        return 'error';
      case 'PENDING':
      default:
        return 'warning';
    }
  }

  getReviewStatusLabel(status: string): string {
    switch (status) {
      case 'APPROVED':
        return 'Đã duyệt';
      case 'REJECTED':
        return 'Từ chối';
      case 'PENDING':
      default:
        return 'Chờ duyệt';
    }
  }

  getTimelineItemColor(item: InternshipStatusHistoryItem): string {
    if (item.action === 'INITIAL') return 'gray';
    if (item.proposal_status === 'APPROVED') return 'green';
    if (item.proposal_status === 'REJECTED') return 'red';
    return 'blue';
  }

  getHistoryActionColor(action: string): string {
    switch (action) {
      case 'INITIAL':
        return 'default';
      case 'EXTEND':
        return 'cyan';
      case 'COMPLETE':
        return 'green';
      case 'STOP':
        return 'red';
      default:
        return 'blue';
    }
  }

  getHistoryActionLabel(action: string): string {
    switch (action) {
      case 'INITIAL':
        return 'Bắt đầu';
      case 'EXTEND':
        return 'Đề xuất gia hạn';
      case 'COMPLETE':
        return 'Đề xuất hoàn thành';
      case 'STOP':
        return 'Đề xuất dừng';
      default:
        return action;
    }
  }
}
