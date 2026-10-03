import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  HostListener,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NzAvatarModule } from 'ng-zorro-antd/avatar';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzProgressModule } from 'ng-zorro-antd/progress';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTimelineModule } from 'ng-zorro-antd/timeline';

import { InternshipService } from '../../core/api/internship.service';
import {
  MentorAssignmentHistoryItem,
  MentorInternDetail,
  MentorInternListItem,
  MentorOverviewMetrics,
  MentorService,
} from '../../core/api/mentor.service';

@Component({
  selector: 'app-mentor-intern-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    NzAvatarModule,
    NzBadgeModule,
    NzButtonModule,
    NzCardModule,
    NzDividerModule,
    NzDrawerModule,
    NzEmptyModule,
    NzFormModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzProgressModule,
    NzSelectModule,
    NzSpinModule,
    NzTableModule,
    NzTabsModule,
    NzTagModule,
    NzTimelineModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mentor-management">
      <!-- HEADER & OVERVIEW CARDS -->
      <div class="header-section">
        <div class="header-title">
          <h1>Quản lý Thực tập sinh phụ trách</h1>
          <p>
            Theo dõi tiến độ, lộ trình đào tạo, bài kiểm tra và lịch sử phân công của các Intern.
          </p>
        </div>
      </div>

      <!-- METRIC KPI CARDS -->
      <section class="metric-grid">
        <nz-card class="metric-card" [nzBordered]="false">
          <div class="metric-content">
            <span nz-icon nzType="team" class="metric-icon metric-icon--blue"></span>
            <div>
              <p>Tổng Intern phụ trách</p>
              <strong>{{ overview()?.total_interns ?? 0 }}</strong>
            </div>
          </div>
        </nz-card>
        <nz-card class="metric-card" [nzBordered]="false">
          <div class="metric-content">
            <span nz-icon nzType="check-square" class="metric-icon metric-icon--green"></span>
            <div>
              <p>Đang thực tập</p>
              <strong>{{ overview()?.active_interns ?? 0 }}</strong>
            </div>
          </div>
        </nz-card>
        <nz-card class="metric-card" [nzBordered]="false">
          <div class="metric-content">
            <span nz-icon nzType="bar-chart" class="metric-icon metric-icon--purple"></span>
            <div>
              <p>Tiến độ trung bình</p>
              <strong>{{ overview()?.avg_progress ?? 0 }}%</strong>
            </div>
          </div>
        </nz-card>
        <nz-card class="metric-card" [nzBordered]="false">
          <div class="metric-content">
            <span nz-icon nzType="form" class="metric-icon metric-icon--orange"></span>
            <div>
              <p>Quiz đã vượt qua</p>
              <strong>{{ overview()?.total_quizzes_passed ?? 0 }}</strong>
            </div>
          </div>
        </nz-card>
      </section>

      <!-- FILTER TOOLBAR -->
      <nz-card class="filter-card" [nzBordered]="false">
        <div class="filter-toolbar">
          <div class="filter-item search-box">
            <nz-input-group nzPrefixIcon="search">
              <input
                type="text"
                nz-input
                placeholder="Tìm kiếm theo tên hoặc email..."
                [(ngModel)]="searchQuery"
                (ngModelChange)="onSearchChange()"
              />
            </nz-input-group>
          </div>

          <div class="filter-item select-box">
            <nz-select
              [(ngModel)]="selectedStatus"
              (ngModelChange)="loadInterns()"
              nzPlaceHolder="Trạng thái"
              class="w-full"
            >
              <nz-option nzValue="" nzLabel="Tất cả trạng thái"></nz-option>
              <nz-option nzValue="ACTIVE" nzLabel="Đang thực tập (ACTIVE)"></nz-option>
              <nz-option nzValue="EXTENDED" nzLabel="Gia hạn (EXTENDED)"></nz-option>
              <nz-option nzValue="COMPLETED" nzLabel="Hoàn thành (COMPLETED)"></nz-option>
              <nz-option nzValue="STOPPED" nzLabel="Tạm dừng (STOPPED)"></nz-option>
            </nz-select>
          </div>

          <div class="filter-item select-box">
            <nz-select
              [(ngModel)]="selectedInternshipId"
              (ngModelChange)="loadInterns()"
              nzPlaceHolder="Đợt thực tập"
              class="w-full"
            >
              <nz-option nzValue="" nzLabel="Tất cả đợt thực tập"></nz-option>
              @for (batch of internships(); track batch.id) {
                <nz-option [nzValue]="batch.id" [nzLabel]="batch.name"></nz-option>
              }
            </nz-select>
          </div>

          <div class="filter-actions">
            <button nz-button nzType="default" (click)="resetFilters()">
              <span nz-icon nzType="reload"></span> Đặt lại
            </button>
            <button nz-button nzType="default" (click)="openAuditHistoryModal()">
              <span nz-icon nzType="audit"></span> Lịch sử phân công
            </button>
          </div>
        </div>
      </nz-card>

      <!-- MAIN CONTENT: INTERNS LIST -->
      <nz-card class="list-card" [nzBordered]="false">
        <nz-spin [nzSpinning]="loading()">
          <!-- DESKTOP TABLE (> 768px) -->
          <div class="desktop-table">
            <nz-table
              #internTable
              [nzData]="interns()"
              [nzFrontPagination]="true"
              [nzPageSize]="10"
              nzSize="middle"
            >
              <thead>
                <tr>
                  <th>Thực tập sinh</th>
                  <th>Đợt thực tập</th>
                  <th>Lộ trình & Tiến độ</th>
                  <th>Bài kiểm tra</th>
                  <th>Trạng thái</th>
                  <th nzAlign="right">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                @for (item of internTable.data; track item.id) {
                  <tr>
                    <td>
                      <div class="intern-cell">
                        <nz-avatar
                          [nzSrc]="item.intern_avatar_url ?? undefined"
                          [nzText]="getInitials(item.intern_name)"
                          class="intern-avatar"
                        ></nz-avatar>
                        <div class="intern-meta">
                          <strong class="intern-name">{{ item.intern_name }}</strong>
                          <span class="intern-email">{{ item.intern_email }}</span>
                          @if (item.intern_phone) {
                            <small class="intern-phone">{{ item.intern_phone }}</small>
                          }
                        </div>
                      </div>
                    </td>
                    <td>
                      <span class="batch-name">{{ item.internship_name }}</span>
                    </td>
                    <td>
                      <div class="progress-cell">
                        <span class="roadmap-name">{{
                          item.roadmap_name || 'Chưa gán lộ trình'
                        }}</span>
                        <div class="progress-bar-wrap">
                          <nz-progress
                            [nzPercent]="item.progress_percent"
                            nzSize="small"
                            [nzStatus]="item.progress_percent >= 100 ? 'success' : 'active'"
                          ></nz-progress>
                        </div>
                      </div>
                    </td>
                    <td>
                      <nz-tag nzColor="blue"> {{ item.quizzes_passed }} Quiz đã đạt </nz-tag>
                    </td>
                    <td>
                      <nz-tag [nzColor]="getStatusTagColor(item.status)">
                        {{ getStatusLabel(item.status) }}
                      </nz-tag>
                    </td>
                    <td nzAlign="right">
                      <div class="action-buttons">
                        <button
                          nz-button
                          nzType="link"
                          nzSize="small"
                          (click)="openDetail(item.id)"
                          title="Xem chi tiết hồ sơ & tiến độ"
                        >
                          <span nz-icon nzType="solution"></span> Chi tiết
                        </button>
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </nz-table>
          </div>

          <!-- MOBILE CARDS (<= 767px) -->
          <div class="mobile-cards">
            @if (interns().length === 0) {
              <nz-empty
                nzNotFoundImage="simple"
                nzNotFoundContent="Không tìm thấy thực tập sinh nào"
              ></nz-empty>
            }
            @for (item of interns(); track item.id) {
              <div class="intern-card-mobile">
                <div class="card-mobile-header">
                  <div class="intern-cell">
                    <nz-avatar
                      [nzSrc]="item.intern_avatar_url ?? undefined"
                      [nzText]="getInitials(item.intern_name)"
                    ></nz-avatar>
                    <div class="intern-meta">
                      <strong class="intern-name">{{ item.intern_name }}</strong>
                      <span class="intern-email">{{ item.intern_email }}</span>
                    </div>
                  </div>
                  <nz-tag [nzColor]="getStatusTagColor(item.status)">
                    {{ getStatusLabel(item.status) }}
                  </nz-tag>
                </div>

                <div class="card-mobile-body">
                  <div class="info-row">
                    <span class="label">Đợt thực tập:</span>
                    <span class="value">{{ item.internship_name }}</span>
                  </div>
                  <div class="info-row">
                    <span class="label">Lộ trình:</span>
                    <span class="value">{{ item.roadmap_name || 'Chưa gán' }}</span>
                  </div>
                  <div class="info-row">
                    <span class="label">Tiến độ:</span>
                    <div class="value progress-value">
                      <nz-progress
                        [nzPercent]="item.progress_percent"
                        nzSize="small"
                        [nzStatus]="item.progress_percent >= 100 ? 'success' : 'active'"
                      ></nz-progress>
                    </div>
                  </div>
                  <div class="info-row">
                    <span class="label">Quiz đã đạt:</span>
                    <span class="value">
                      <nz-tag nzColor="blue">{{ item.quizzes_passed }} bài</nz-tag>
                    </span>
                  </div>
                </div>

                <div class="card-mobile-footer">
                  <button nz-button nzType="primary" nzGhost nzBlock (click)="openDetail(item.id)">
                    <span nz-icon nzType="solution"></span> Chi tiết
                  </button>
                </div>
              </div>
            }
          </div>
        </nz-spin>
      </nz-card>

      <!-- DRAWER CHI TIẾT INTERN (Profile, Roadmap, Quiz, History) -->
      <nz-drawer
        [nzVisible]="isDetailDrawerOpen()"
        [nzWidth]="drawerWidth()"
        nzTitle="Chi tiết Thực tập sinh"
        (nzOnClose)="closeDetailDrawer()"
      >
        <ng-container *nzDrawerContent>
          <nz-spin [nzSpinning]="detailLoading()">
            @if (detail(); as d) {
              <div class="drawer-header-meta">
                <nz-avatar
                  [nzSize]="64"
                  [nzSrc]="d.intern.avatar_url ?? undefined"
                  [nzText]="getInitials(d.intern.full_name)"
                ></nz-avatar>
                <div class="drawer-user-info">
                  <h2>{{ d.intern.full_name }}</h2>
                  <p>{{ d.intern.email }}</p>
                  <nz-tag [nzColor]="getStatusTagColor(d.status)">
                    {{ getStatusLabel(d.status) }}
                  </nz-tag>
                </div>
              </div>

              <nz-tabs
                [nzSelectedIndex]="activeDetailTab()"
                (nzSelectedIndexChange)="activeDetailTab.set($event)"
              >
                <!-- TAB 1: HỒ SƠ INTERN -->
                <nz-tab nzTitle="Hồ sơ cá nhân">
                  <div class="tab-pane">
                    <!-- THÔNG TIN MENTOR PHỤ TRÁCH HIỆN TẠI -->
                    <nz-card nzTitle="Mentor phụ trách hiện tại" nzSize="small" class="detail-card">
                      <div class="key-value-list">
                        <div class="kv-item">
                          <span class="kv-label">Họ và tên Mentor:</span>
                          <span class="kv-value font-semibold">
                            {{ d.mentor?.full_name || 'Chưa phân công Mentor' }}
                          </span>
                        </div>
                        <div class="kv-item">
                          <span class="kv-label">Email Mentor:</span>
                          <span class="kv-value">{{ d.mentor?.email || '--' }}</span>
                        </div>
                        @if (d.mentor?.phone) {
                          <div class="kv-item">
                            <span class="kv-label">Số điện thoại:</span>
                            <span class="kv-value">{{ d.mentor?.phone }}</span>
                          </div>
                        }
                      </div>
                    </nz-card>

                    <!-- THÔNG TIN CÁ NHÂN -->
                    <nz-card nzTitle="Thông tin cá nhân Intern" nzSize="small" class="detail-card">
                      <div class="key-value-list">
                        <div class="kv-item">
                          <span class="kv-label">Họ và tên:</span>
                          <span class="kv-value">{{ d.intern.full_name }}</span>
                        </div>
                        <div class="kv-item">
                          <span class="kv-label">Email:</span>
                          <span class="kv-value">{{ d.intern.email }}</span>
                        </div>
                        <div class="kv-item">
                          <span class="kv-label">Số điện thoại:</span>
                          <span class="kv-value">{{ d.intern.phone || 'Chưa cập nhật' }}</span>
                        </div>
                        <div class="kv-item">
                          <span class="kv-label">Trạng thái tài khoản:</span>
                          <span class="kv-value">
                            <nz-tag [nzColor]="d.intern.status === 'ACTIVE' ? 'green' : 'red'">
                              {{ d.intern.status }}
                            </nz-tag>
                          </span>
                        </div>
                      </div>
                    </nz-card>

                    <!-- THÔNG TIN THỰC TẬP -->
                    <nz-card nzTitle="Thông tin thực tập" nzSize="small" class="detail-card">
                      <div class="key-value-list">
                        <div class="kv-item">
                          <span class="kv-label">Đợt thực tập:</span>
                          <span class="kv-value">{{ d.internship.name }}</span>
                        </div>
                        <div class="kv-item">
                          <span class="kv-label">Thời gian bắt đầu:</span>
                          <span class="kv-value">{{ d.start_date || 'Chưa đặt' }}</span>
                        </div>
                        <div class="kv-item">
                          <span class="kv-label">Thời gian kết thúc:</span>
                          <span class="kv-value">{{ d.end_date || 'Chưa đặt' }}</span>
                        </div>
                        <div class="kv-item">
                          <span class="kv-label">Trạng thái thực tập:</span>
                          <span class="kv-value">
                            <nz-tag [nzColor]="getStatusTagColor(d.status)">
                              {{ getStatusLabel(d.status) }}
                            </nz-tag>
                          </span>
                        </div>
                      </div>
                    </nz-card>
                  </div>
                </nz-tab>

                <!-- TAB 2: ROADMAP & TIẾN ĐỘ -->
                <nz-tab nzTitle="Lộ trình & Tiến độ">
                  <div class="tab-pane">
                    @if (d.roadmap && d.roadmap.phases && d.roadmap.phases.length > 0) {
                      <div class="roadmap-summary">
                        <h3>{{ d.roadmap.roadmap_name }}</h3>
                        @if (d.roadmap.description) {
                          <p class="roadmap-desc">{{ d.roadmap.description }}</p>
                        }
                      </div>

                      <div class="phase-list">
                        @for (phase of d.roadmap.phases; track phase.id) {
                          <nz-card [nzTitle]="phase.name" nzSize="small" class="phase-card">
                            @if (phase.description) {
                              <p class="phase-desc">{{ phase.description }}</p>
                            }
                            <div class="content-items">
                              @for (c of phase.contents; track c.id) {
                                <div class="content-row">
                                  <div class="content-main">
                                    <span class="content-title">
                                      {{ c.order_no }}. {{ c.title }}
                                    </span>
                                    <nz-tag
                                      [nzColor]="getContentTypeColor(c.type)"
                                      class="content-type-tag"
                                    >
                                      {{ c.type }}
                                    </nz-tag>
                                  </div>
                                  <div class="content-progress">
                                    <nz-progress
                                      [nzPercent]="c.progress_percent"
                                      nzSize="small"
                                      [nzStatus]="c.status === 'COMPLETED' ? 'success' : 'active'"
                                    ></nz-progress>
                                  </div>
                                  <nz-tag [nzColor]="getContentStatusColor(c.status)">
                                    {{ c.status }}
                                  </nz-tag>
                                </div>
                              }
                            </div>
                          </nz-card>
                        }
                      </div>
                    } @else {
                      <nz-empty
                        nzNotFoundContent="Intern này chưa được gán lộ trình đào tạo"
                      ></nz-empty>
                    }
                  </div>
                </nz-tab>

                <!-- TAB 3: KẾT QUẢ QUIZ -->
                <nz-tab nzTitle="Kết quả Quiz">
                  <div class="tab-pane">
                    @if (d.quiz_attempts && d.quiz_attempts.length > 0) {
                      <div class="table-responsive">
                        <nz-table
                          #quizTable
                          [nzData]="d.quiz_attempts"
                          [nzFrontPagination]="false"
                          nzSize="small"
                        >
                          <thead>
                            <tr>
                              <th>Bài kiểm tra</th>
                              <th>Lần làm</th>
                              <th>Điểm</th>
                              <th>Kết quả</th>
                              <th>Thời gian</th>
                            </tr>
                          </thead>
                          <tbody>
                            @for (q of quizTable.data; track q.id) {
                              <tr>
                                <td>
                                  <strong>{{ q.quiz_title }}</strong>
                                </td>
                                <td>Lần {{ q.attempt_no }}</td>
                                <td>
                                  <strong>{{ q.score !== null ? q.score : '--' }}</strong>
                                </td>
                                <td>
                                  <nz-tag [nzColor]="q.passed ? 'green' : 'red'">
                                    {{ q.passed ? 'ĐẠT (PASSED)' : 'CHƯA ĐẠT' }}
                                  </nz-tag>
                                </td>
                                <td>
                                  <small>{{ formatDateTime(q.started_at) }}</small>
                                </td>
                              </tr>
                            }
                          </tbody>
                        </nz-table>
                      </div>
                    } @else {
                      <nz-empty nzNotFoundContent="Chưa có lượt làm bài kiểm tra nào"></nz-empty>
                    }
                  </div>
                </nz-tab>

                <!-- TAB 4: LỊCH SỬ PHÂN CÔNG MENTOR -->
                <nz-tab nzTitle="Lịch sử phân công">
                  <div class="tab-pane">
                    @if (d.assignment_history && d.assignment_history.length > 0) {
                      <nz-timeline>
                        @for (hist of d.assignment_history; track hist.changed_at) {
                          <nz-timeline-item [nzColor]="hist.action === 'ASSIGN' ? 'green' : 'blue'">
                            <p class="history-time">{{ formatDateTime(hist.changed_at) }}</p>
                            <p class="history-title">
                              <strong>{{
                                hist.action === 'ASSIGN' ? 'Gán Mentor chính:' : 'Đổi Mentor chính:'
                              }}</strong>
                              <span class="mentor-transfer">
                                @if (hist.old_mentor_name) {
                                  <span class="old-m">{{ hist.old_mentor_name }}</span>
                                  <span nz-icon nzType="arrow-right"></span>
                                }
                                <span class="new-m">{{ hist.new_mentor_name }}</span>
                              </span>
                            </p>
                            <p class="history-actor">
                              <small>Người thực hiện: {{ hist.changed_by_name }}</small>
                            </p>
                            @if (hist.note) {
                              <p class="history-note">
                                <em>Ghi chú: {{ hist.note }}</em>
                              </p>
                            }
                          </nz-timeline-item>
                        }
                      </nz-timeline>
                    } @else {
                      <nz-empty
                        nzNotFoundContent="Chưa có lịch sử thay đổi Mentor cho Intern này"
                      ></nz-empty>
                    }
                  </div>
                </nz-tab>
              </nz-tabs>
            }
          </nz-spin>
        </ng-container>
      </nz-drawer>

      <!-- MODAL TOÀN BỘ LỊCH SỬ PHÂN CÔNG (AUDIT LOGS) -->
      <nz-modal
        [(nzVisible)]="isAuditModalVisible"
        nzTitle="Toàn bộ lịch sử phân công Mentor"
        (nzOnCancel)="closeAuditHistoryModal()"
        [nzFooter]="null"
        [nzWidth]="auditModalWidth()"
      >
        <ng-container *nzModalContent>
          <nz-spin [nzSpinning]="auditLoading()">
            @if (allAuditHistory().length > 0) {
              <div class="table-responsive">
                <nz-table
                  #auditTable
                  [nzData]="allAuditHistory()"
                  [nzFrontPagination]="true"
                  [nzPageSize]="8"
                  nzSize="small"
                >
                  <thead>
                    <tr>
                      <th>Thời điểm</th>
                      <th>Thực tập sinh</th>
                      <th>Loại</th>
                      <th>Mentor cũ &rarr; Mới</th>
                      <th>Người thực hiện</th>
                      <th>Ghi chú</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (record of auditTable.data; track record.changed_at) {
                      <tr>
                        <td>
                          <small>{{ formatDateTime(record.changed_at) }}</small>
                        </td>
                        <td>
                          <strong>{{ record.intern_name }}</strong>
                        </td>
                        <td>
                          <nz-tag [nzColor]="record.action === 'ASSIGN' ? 'green' : 'blue'">
                            {{ record.action }}
                          </nz-tag>
                        </td>
                        <td>
                          <span class="audit-transfer">
                            {{ record.old_mentor_name || 'None' }} &rarr;
                            <strong>{{ record.new_mentor_name }}</strong>
                          </span>
                        </td>
                        <td>{{ record.changed_by_name }}</td>
                        <td>
                          <small>{{ record.note || '--' }}</small>
                        </td>
                      </tr>
                    }
                  </tbody>
                </nz-table>
              </div>
            } @else {
              <nz-empty nzNotFoundContent="Chưa có lịch sử phân công nào"></nz-empty>
            }
          </nz-spin>
        </ng-container>
      </nz-modal>
    </div>
  `,
  styles: [
    `
      .mentor-management {
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .header-section {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
      }

      .header-title h1 {
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        color: #1f2937;
      }

      .header-title p {
        margin: 4px 0 0;
        font-size: 14px;
        color: #6b7280;
      }

      /* METRIC CARDS */
      .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        width: 100%;
      }

      .metric-card {
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }

      .metric-content {
        display: flex;
        align-items: center;
        gap: 16px;
      }

      .metric-icon {
        font-size: 26px;
        padding: 12px;
        border-radius: 8px;
        flex-shrink: 0;
      }

      .metric-icon--blue {
        color: #1890ff;
        background: #e6f7ff;
      }

      .metric-icon--green {
        color: #52c41a;
        background: #f6ffed;
      }

      .metric-icon--purple {
        color: #722ed1;
        background: #f9f0ff;
      }

      .metric-icon--orange {
        color: #fa8c16;
        background: #fff7e6;
      }

      .metric-content p {
        margin: 0;
        font-size: 13px;
        color: #6b7280;
      }

      .metric-content strong {
        font-size: 20px;
        color: #111827;
        font-weight: 700;
      }

      /* FILTER TOOLBAR */
      .filter-card {
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }

      .filter-toolbar {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        width: 100%;
      }

      .filter-item {
        flex: 1;
        min-width: 180px;
      }

      .filter-item.search-box {
        min-width: 240px;
        flex: 1.5;
      }

      .w-full {
        width: 100%;
      }

      .filter-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }

      /* LIST CARD */
      .list-card {
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        width: 100%;
        overflow: hidden;
      }

      .desktop-table {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
      }

      .intern-cell {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .intern-meta {
        display: flex;
        flex-direction: column;
        min-width: 0;
      }

      .intern-name {
        font-size: 14px;
        color: #111827;
        overflow-wrap: anywhere;
        word-break: break-word;
      }

      .intern-email {
        font-size: 12px;
        color: #6b7280;
        overflow-wrap: anywhere;
        word-break: break-word;
      }

      .intern-phone {
        font-size: 11px;
        color: #9ca3af;
      }

      .batch-name {
        font-weight: 500;
        color: #374151;
        overflow-wrap: anywhere;
      }

      .progress-cell {
        display: flex;
        flex-direction: column;
        gap: 4px;
        min-width: 140px;
      }

      .roadmap-name {
        font-size: 12px;
        color: #4b5563;
        font-weight: 500;
        overflow-wrap: anywhere;
      }

      .progress-bar-wrap {
        width: 100%;
      }

      .action-buttons {
        display: flex;
        gap: 4px;
        justify-content: flex-end;
      }

      /* MOBILE CARDS DISPLAY */
      .mobile-cards {
        display: none;
        flex-direction: column;
        gap: 12px;
        width: 100%;
      }

      .intern-card-mobile {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 14px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        box-sizing: border-box;
        width: 100%;
        max-width: 100%;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
      }

      .card-mobile-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 8px;
        border-bottom: 1px solid #f3f4f6;
        padding-bottom: 10px;
      }

      .card-mobile-body {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .info-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        font-size: 13px;
      }

      .info-row .label {
        color: #6b7280;
        font-size: 12px;
        flex-shrink: 0;
      }

      .info-row .value {
        color: #1f2937;
        font-weight: 500;
        text-align: right;
        min-width: 0;
        overflow-wrap: anywhere;
        word-break: break-word;
      }

      .progress-value {
        width: 55%;
      }

      .card-mobile-footer {
        display: flex;
        gap: 8px;
        padding-top: 10px;
        border-top: 1px solid #f3f4f6;
      }

      .card-mobile-footer button {
        width: 100%;
      }

      /* DRAWER & MODAL STYLES */
      .drawer-header-meta {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;
        padding-bottom: 16px;
        border-bottom: 1px solid #e5e7eb;
        flex-wrap: wrap;
      }

      .drawer-user-info {
        min-width: 0;
        flex: 1;
      }

      .drawer-user-info h2 {
        margin: 0 0 4px;
        font-size: 18px;
        font-weight: 700;
        overflow-wrap: anywhere;
      }

      .drawer-user-info p {
        margin: 0 0 6px;
        color: #6b7280;
        font-size: 13px;
        overflow-wrap: anywhere;
      }

      .tab-pane {
        padding: 12px 0;
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .detail-card {
        margin-bottom: 12px;
      }

      .key-value-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .kv-item {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        font-size: 13px;
      }

      .kv-label {
        color: #6b7280;
        flex-shrink: 0;
      }

      .kv-value {
        color: #1f2937;
        text-align: right;
        overflow-wrap: anywhere;
        word-break: break-word;
      }

      .roadmap-summary h3 {
        margin: 0 0 4px;
        font-size: 16px;
        font-weight: 600;
        overflow-wrap: anywhere;
      }

      .roadmap-desc {
        color: #6b7280;
        font-size: 13px;
        margin-bottom: 12px;
        overflow-wrap: anywhere;
      }

      .phase-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .phase-card {
        background: #fafafa;
      }

      .phase-desc {
        color: #6b7280;
        font-size: 12px;
        margin-bottom: 8px;
        overflow-wrap: anywhere;
      }

      .content-items {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .content-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        background: #ffffff;
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid #f0f0f0;
      }

      .content-main {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
        min-width: 0;
      }

      .content-title {
        font-size: 13px;
        font-weight: 500;
        color: #374151;
        overflow-wrap: anywhere;
      }

      .content-progress {
        width: 120px;
        flex-shrink: 0;
      }

      .table-responsive {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
      }

      .history-time {
        font-size: 12px;
        color: #9ca3af;
        margin: 0 0 2px;
      }

      .history-title {
        font-size: 13px;
        margin: 0 0 4px;
        color: #1f2937;
        overflow-wrap: anywhere;
      }

      .mentor-transfer {
        margin-left: 6px;
        overflow-wrap: anywhere;
      }

      .old-m {
        color: #ef4444;
        text-decoration: line-through;
        margin-right: 4px;
      }

      .new-m {
        color: #10b981;
        font-weight: 600;
        margin-left: 4px;
      }

      .history-actor,
      .history-note {
        margin: 2px 0 0;
        font-size: 12px;
        color: #6b7280;
        overflow-wrap: anywhere;
      }

      .audit-transfer {
        font-size: 12px;
        overflow-wrap: anywhere;
      }

      /* ==========================================================================
         TABLET BREAKPOINT (768px – 1023px)
         ========================================================================== */
      @media screen and (min-width: 768px) and (max-width: 1023px) {
        .metric-grid {
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
        }

        .filter-toolbar {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .filter-item.search-box {
          grid-column: 1 / -1;
        }

        .filter-actions {
          grid-column: 1 / -1;
          justify-content: flex-end;
        }

        .desktop-table {
          overflow-x: auto;
        }
      }

      /* ==========================================================================
         MOBILE BREAKPOINT (<= 767px)
         ========================================================================== */
      @media screen and (max-width: 767px) {
        .desktop-table {
          display: none;
        }

        .mobile-cards {
          display: flex;
        }

        /* KPI mobile: 2x2 grid */
        .metric-grid {
          grid-template-columns: repeat(2, 1fr);
          gap: 8px;
        }

        .metric-card {
          border-radius: 6px;
        }

        .metric-content {
          gap: 8px;
          padding: 4px;
        }

        .metric-icon {
          font-size: 20px;
          padding: 8px;
        }

        .metric-content p {
          font-size: 11px;
          line-height: 1.2;
        }

        .metric-content strong {
          font-size: 16px;
        }

        /* Filter mobile: vertical layout */
        .filter-toolbar {
          display: flex;
          flex-direction: column;
          gap: 10px;
          width: 100%;
        }

        .filter-item {
          width: 100%;
          min-width: 100%;
        }

        .filter-actions {
          display: flex;
          gap: 8px;
          width: 100%;
        }

        .filter-actions button {
          flex: 1;
          justify-content: center;
          padding: 0 4px;
          font-size: 13px;
        }

        .content-row {
          flex-direction: column;
          align-items: flex-start;
          gap: 6px;
        }

        .content-progress {
          width: 100%;
        }

        .drawer-header-meta {
          flex-direction: column;
          align-items: center;
          text-align: center;
        }

        .drawer-user-info {
          text-align: center;
        }

        .kv-item {
          flex-direction: column;
          gap: 2px;
        }

        .kv-value {
          text-align: left;
        }
      }
    `,
  ],
})
export class MentorInternManagementComponent implements OnInit {
  private readonly mentorService = inject(MentorService);
  private readonly internshipService = inject(InternshipService);
  private readonly message = inject(NzMessageService);
  private readonly cdr = inject(ChangeDetectorRef);

  loading = signal<boolean>(false);
  overview = signal<MentorOverviewMetrics | null>(null);
  interns = signal<MentorInternListItem[]>([]);
  internships = signal<{ id: string; name: string }[]>([]);

  searchQuery = '';
  selectedStatus = '';
  selectedInternshipId = '';

  // Drawer detail state
  isDetailDrawerOpen = signal<boolean>(false);
  detailLoading = signal<boolean>(false);
  detail = signal<MentorInternDetail | null>(null);
  activeDetailTab = signal<number>(0);

  // Audit history modal state
  isAuditModalVisible = false;
  auditLoading = signal<boolean>(false);
  allAuditHistory = signal<MentorAssignmentHistoryItem[]>([]);

  // Reactive window width for responsive drawer and modal
  windowWidth = signal<number>(typeof window !== 'undefined' ? window.innerWidth : 1200);

  @HostListener('window:resize')
  onResize(): void {
    if (typeof window !== 'undefined') {
      this.windowWidth.set(window.innerWidth);
    }
  }

  drawerWidth = computed(() => {
    return this.windowWidth() <= 767 ? '100%' : '680px';
  });

  auditModalWidth = computed(() => {
    return this.windowWidth() <= 767 ? '95vw' : '760px';
  });

  ngOnInit(): void {
    this.loadOverview();
    this.loadInterns();
    this.loadAuxiliaryData();
  }

  loadOverview(): void {
    this.mentorService.getOverview().subscribe({
      next: (data) => {
        this.overview.set(data);
        this.cdr.markForCheck();
      },
      error: () => undefined,
    });
  }

  loadInterns(): void {
    this.loading.set(true);
    this.mentorService
      .getInterns(this.searchQuery, this.selectedStatus, this.selectedInternshipId)
      .subscribe({
        next: (data) => {
          this.interns.set(data);
          this.loading.set(false);
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.loading.set(false);
          this.message.error(err?.error?.message || 'Không thể tải danh sách Intern');
          this.cdr.markForCheck();
        },
      });
  }

  loadAuxiliaryData(): void {
    // Load internships for filter
    this.internshipService.getInternships(0, 100).subscribe({
      next: (batches) => {
        this.internships.set(batches.map((b) => ({ id: b.id, name: b.name })));
        this.cdr.markForCheck();
      },
      error: () => undefined,
    });
  }

  onSearchChange(): void {
    this.loadInterns();
  }

  resetFilters(): void {
    this.searchQuery = '';
    this.selectedStatus = '';
    this.selectedInternshipId = '';
    this.loadInterns();
  }

  openDetail(memberId: string): void {
    this.isDetailDrawerOpen.set(true);
    this.detailLoading.set(true);
    this.activeDetailTab.set(0);

    this.mentorService.getInternDetail(memberId).subscribe({
      next: (res) => {
        this.detail.set(res);
        this.detailLoading.set(false);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.detailLoading.set(false);
        this.message.error(err?.error?.message || 'Không thể tải chi tiết Intern');
        this.cdr.markForCheck();
      },
    });
  }

  closeDetailDrawer(): void {
    this.isDetailDrawerOpen.set(false);
    this.detail.set(null);
  }

  openAuditHistoryModal(): void {
    this.isAuditModalVisible = true;
    this.auditLoading.set(true);
    this.mentorService.getAssignmentHistory().subscribe({
      next: (logs) => {
        this.allAuditHistory.set(logs);
        this.auditLoading.set(false);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.auditLoading.set(false);
        this.message.error(err?.error?.message || 'Không thể tải lịch sử phân công');
        this.cdr.markForCheck();
      },
    });
  }

  closeAuditHistoryModal(): void {
    this.isAuditModalVisible = false;
  }

  getStatusTagColor(status: string): string {
    switch (status) {
      case 'ACTIVE':
        return 'green';
      case 'EXTENDED':
        return 'gold';
      case 'COMPLETED':
        return 'blue';
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
        return 'Gia hạn';
      case 'COMPLETED':
        return 'Hoàn thành';
      case 'STOPPED':
        return 'Tạm dừng';
      default:
        return status;
    }
  }

  getContentTypeColor(type: string): string {
    switch (type) {
      case 'LESSON':
        return 'blue';
      case 'ASSIGNMENT':
        return 'orange';
      case 'QUIZ':
        return 'purple';
      case 'PROJECT':
        return 'cyan';
      default:
        return 'geekblue';
    }
  }

  getContentStatusColor(status: string): string {
    switch (status) {
      case 'COMPLETED':
        return 'green';
      case 'IN_PROGRESS':
        return 'blue';
      default:
        return 'default';
    }
  }

  getInitials(name: string): string {
    if (!name) return 'IN';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  formatDateTime(isoStr?: string | null): string {
    if (!isoStr) return '--';
    try {
      const d = new Date(isoStr);
      return (
        d.toLocaleDateString('vi-VN', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
        }) +
        ' ' +
        d.toLocaleTimeString('vi-VN', {
          hour: '2-digit',
          minute: '2-digit',
        })
      );
    } catch {
      return isoStr;
    }
  }
}
