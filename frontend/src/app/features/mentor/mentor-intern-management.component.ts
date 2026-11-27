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
import { ActivatedRoute, Router } from '@angular/router';
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
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzProgressModule } from 'ng-zorro-antd/progress';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTimelineModule } from 'ng-zorro-antd/timeline';

import { InternshipService, internshipPositionLabel } from '../../core/api/internship.service';
import {
  InternshipProposalCreatePayload,
  InternshipProposalItem,
  InternshipStatusHistoryItem,
  MentorAssignmentHistoryItem,
  MentorInternDetail,
  MentorInternListItem,
  MentorService,
  PendingQuizGradingItem,
  QuizAttemptGradingDetail,
} from '../../core/api/mentor.service';

@Component({
  selector: 'app-mentor-intern-management',
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
    NzInputNumberModule,
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
    <div class="mentor-management feature-page-layout">
      <!-- HEADER -->
      <div class="header-section feature-page-header">
        <div class="header-title">
          <h1 class="feature-page-title">Quản lý thực tập</h1>
        </div>
      </div>

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
            <button nz-button nzType="default" (click)="openProposalHistoryModal()">
              <span nz-icon nzType="form"></span> Đề xuất đã gửi ({{ proposals().length }})
            </button>
            <button nz-button nzType="default" (click)="openAuditHistoryModal()">
              <span nz-icon nzType="audit"></span> Lịch sử phân công
            </button>
            <button
              nz-button
              [nzType]="totalPendingQuizGradings() > 0 ? 'primary' : 'default'"
              (click)="openPendingGradingsModal()"
              title="Xem danh sách bài kiểm tra tự luận chờ chấm"
            >
              <span nz-icon nzType="edit"></span> Bài chờ chấm ({{ totalPendingQuizGradings() }})
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
                  <th>Đề xuất hiện tại</th>
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
                      <div class="position-caption">{{ positionLabel(item.position) }}</div>
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
                      @if ((item.pending_quiz_gradings ?? 0) > 0) {
                        <nz-tag
                          nzColor="warning"
                          style="cursor: pointer"
                          (click)="openPendingGradingsModal(item.id)"
                          title="Nhấn để xem bài làm chờ chấm"
                        >
                          Chờ chấm: {{ item.pending_quiz_gradings }}
                        </nz-tag>
                      }
                    </td>
                    <td>
                      <nz-tag [nzColor]="getStatusTagColor(item.status)">
                        {{ getStatusLabel(item.status) }}
                      </nz-tag>
                    </td>
                    <td>
                      @if (getPendingProposalForIntern(item.id); as pending) {
                        <nz-tag nzColor="processing" class="pending-tag">
                          <span nz-icon nzType="sync" nzSpin></span>
                          Chờ duyệt {{ getProposalTypeLabel(pending.type) }}
                        </nz-tag>
                      } @else {
                        <span class="text-muted">Không có đề xuất chờ</span>
                      }
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
                        <button
                          nz-button
                          nzType="primary"
                          nzSize="small"
                          (click)="openProposalModal(item)"
                          [disabled]="isProposalDisabled(item)"
                          [title]="getProposalDisabledTooltip(item)"
                        >
                          <span nz-icon nzType="form"></span> Đề xuất
                        </button>
                        <button
                          nz-button
                          nzType="default"
                          nzSize="small"
                          (click)="openStatusHistoryDrawer(item)"
                        >
                          <span nz-icon nzType="history"></span> Lịch sử
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
                    <span class="label">Vị trí thực tập:</span>
                    <span class="value">{{ positionLabel(item.position) }}</span>
                  </div>
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
                      @if ((item.pending_quiz_gradings ?? 0) > 0) {
                        <nz-tag
                          nzColor="warning"
                          style="cursor: pointer"
                          (click)="openPendingGradingsModal(item.id)"
                          title="Nhấn để xem bài làm chờ chấm"
                        >
                          Chờ chấm: {{ item.pending_quiz_gradings }}
                        </nz-tag>
                      }
                    </span>
                  </div>
                  <div class="info-row">
                    <span class="label">Đề xuất hiện tại:</span>
                    <span class="value">
                      @if (getPendingProposalForIntern(item.id); as pending) {
                        <nz-tag nzColor="processing">
                          Chờ duyệt {{ getProposalTypeLabel(pending.type) }}
                        </nz-tag>
                      } @else {
                        <span class="text-muted">Không có đề xuất chờ</span>
                      }
                    </span>
                  </div>
                </div>

                <div class="card-mobile-footer">
                  <button
                    nz-button
                    nzType="primary"
                    nzGhost
                    class="detail-action"
                    (click)="openDetail(item.id)"
                  >
                    <span nz-icon nzType="solution"></span> Chi tiết
                  </button>
                  <button
                    nz-button
                    nzType="primary"
                    (click)="openProposalModal(item)"
                    [disabled]="isProposalDisabled(item)"
                  >
                    <span nz-icon nzType="form"></span> Đề xuất
                  </button>
                  <button nz-button nzType="default" (click)="openStatusHistoryDrawer(item)">
                    <span nz-icon nzType="history"></span> Lịch sử
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
                          <span class="kv-label">Vị trí thực tập:</span>
                          <span class="kv-value">{{ positionLabel(d.position) }}</span>
                        </div>
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
                          class="responsive-card-table responsive-card-table--compact"
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
                              <th>Thao tác</th>
                            </tr>
                          </thead>
                          <tbody>
                            @for (q of quizTable.data; track q.id) {
                              <tr>
                                <td data-label="Bài kiểm tra">
                                  <strong>{{ q.quiz_title }}</strong>
                                </td>
                                <td data-label="Lần làm">Lần {{ q.attempt_no }}</td>
                                <td data-label="Điểm">
                                  <strong>{{
                                    q.score !== null && q.score !== undefined ? q.score : '--'
                                  }}</strong>
                                </td>
                                <td data-label="Kết quả">
                                  @if (!q.submitted_at) {
                                    <nz-tag nzColor="processing">Đang làm</nz-tag>
                                  } @else if (q.grading_status === 'PENDING_GRADING') {
                                    <nz-tag nzColor="orange">Chờ chấm</nz-tag>
                                  } @else {
                                    <nz-tag [nzColor]="q.passed ? 'green' : 'red'">
                                      {{ q.passed ? 'ĐẠT (PASSED)' : 'CHƯA ĐẠT' }}
                                    </nz-tag>
                                  }
                                </td>
                                <td data-label="Thời gian">
                                  <small>{{ formatDateTime(q.started_at) }}</small>
                                </td>
                                <td data-label="Thao tác">
                                  @if (q.submitted_at) {
                                    <button
                                      nz-button
                                      nzType="link"
                                      nzSize="small"
                                      (click)="openQuizGradingModal(q.id)"
                                    >
                                      {{
                                        q.grading_status === 'PENDING_GRADING'
                                          ? 'Chấm bài'
                                          : 'Xem / Sửa điểm'
                                      }}
                                    </button>
                                  }
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

      <!-- MODAL GỬI ĐỀ XUẤT THAY ĐỔI TRẠNG THÁI -->
      <nz-modal
        [(nzVisible)]="isProposalModalVisible"
        nzTitle="Tạo đề xuất thay đổi trạng thái thực tập"
        (nzOnCancel)="closeProposalModal()"
        (nzOnOk)="submitProposal()"
        [nzOkLoading]="proposalSubmitting()"
        [nzOkDisabled]="isSubmitProposalDisabled()"
        nzOkText="Gửi đề xuất"
        nzCancelText="Hủy"
        [nzWidth]="proposalModalWidth()"
      >
        <ng-container *nzModalContent>
          @if (selectedProposalIntern(); as intern) {
            <div class="proposal-intern-card">
              <div class="proposal-intern-header">
                <nz-avatar
                  [nzSrc]="intern.intern_avatar_url ?? undefined"
                  [nzText]="getInitials(intern.intern_name)"
                ></nz-avatar>
                <div>
                  <strong>{{ intern.intern_name }}</strong>
                  <div class="text-muted">{{ intern.intern_email }}</div>
                </div>
              </div>
              <nz-divider style="margin: 12px 0;"></nz-divider>
              <div class="proposal-intern-details">
                <div>
                  <span>Đợt:</span> <b>{{ intern.internship_name }}</b>
                </div>
                <div>
                  <span>Trạng thái hiện tại:</span>
                  <nz-tag [nzColor]="getStatusTagColor(intern.status)">
                    {{ getStatusLabel(intern.status) }}
                  </nz-tag>
                </div>
                <div>
                  <span>Hạn kết thúc hiện tại:</span>
                  <b>{{ intern.end_date ? (intern.end_date | date: 'dd/MM/yyyy') : '—' }}</b>
                </div>
              </div>
            </div>

            @if (hasPendingExtendProposal(intern.id)) {
              <nz-alert
                nzType="warning"
                nzShowIcon
                nzMessage="Đang có đề xuất gia hạn chờ duyệt"
                nzDescription="Tùy chọn Gia hạn được khóa cho đến khi đề xuất trước đó được xử lý."
              ></nz-alert>
            }

            <form nz-form nzLayout="vertical" class="proposal-form">
              <nz-form-item>
                <nz-form-label nzRequired>Loại đề xuất</nz-form-label>
                <nz-form-control>
                  <nz-select [(ngModel)]="proposalType" name="proposalType" style="width: 100%;">
                    <nz-option
                      nzValue="EXTEND"
                      nzLabel="Gia hạn thực tập"
                      [nzDisabled]="hasPendingExtendProposal(intern.id)"
                    ></nz-option>
                    <nz-option nzValue="STOP" nzLabel="Dừng thực tập"></nz-option>
                    <nz-option nzValue="COMPLETE" nzLabel="Hoàn thành thực tập"></nz-option>
                  </nz-select>
                </nz-form-control>
              </nz-form-item>

              @if (proposalType === 'EXTEND') {
                <nz-form-item>
                  <nz-form-label nzRequired>Ngày kết thúc mới đề xuất</nz-form-label>
                  <nz-form-control nzExtra="Ngày mới phải sau ngày kết thúc hiện tại">
                    <nz-date-picker
                      [(ngModel)]="proposalEndDate"
                      name="proposalEndDate"
                      nzFormat="dd/MM/yyyy"
                      style="width: 100%;"
                      [nzDisabledDate]="disabledProposalEndDate"
                      nzPlaceHolder="Chọn ngày kết thúc mới"
                    ></nz-date-picker>
                  </nz-form-control>
                </nz-form-item>
              }

              <nz-form-item>
                <nz-form-label nzRequired>Lý do đề xuất</nz-form-label>
                <nz-form-control nzExtra="Tối đa 1000 ký tự">
                  <textarea
                    nz-input
                    [(ngModel)]="proposalReason"
                    name="proposalReason"
                    [rows]="4"
                    maxlength="1000"
                    placeholder="Nhập lý do đề xuất..."
                  ></textarea>
                </nz-form-control>
              </nz-form-item>
            </form>
          }
        </ng-container>
      </nz-modal>

      <!-- DRAWER LỊCH SỬ TRẠNG THÁI -->
      <nz-drawer
        [nzVisible]="isStatusHistoryDrawerVisible"
        nzPlacement="right"
        [nzWidth]="statusHistoryDrawerWidth()"
        [nzTitle]="statusHistoryDrawerTitle"
        (nzOnClose)="closeStatusHistoryDrawer()"
      >
        <ng-container *nzDrawerContent>
          @if (statusHistoryLoading()) {
            <div class="drawer-loading"><nz-spin nzSimple nzSize="large"></nz-spin></div>
          } @else if (statusHistoryItems().length === 0) {
            <nz-empty nzNotFoundContent="Không có lịch sử trạng thái"></nz-empty>
          } @else {
            <nz-timeline class="status-history-timeline">
              @for (item of statusHistoryItems(); track item.id) {
                <nz-timeline-item [nzColor]="getTimelineItemColor(item)">
                  <div class="status-history-entry">
                    <div class="status-history-header">
                      <nz-tag [nzColor]="getHistoryActionColor(item.action)">
                        {{ getHistoryActionLabel(item.action) }}
                      </nz-tag>
                      @if (item.proposal_status) {
                        <nz-tag [nzColor]="getReviewStatusColor(item.proposal_status)">
                          {{ getReviewStatusLabel(item.proposal_status) }}
                        </nz-tag>
                      }
                    </div>
                    <div class="status-transition">
                      <span>{{ getStatusLabel(item.from_status || 'INITIAL') }}</span>
                      <span>→</span>
                      <strong>{{ getStatusLabel(item.to_status) }}</strong>
                    </div>
                    @if (item.requested_end_date) {
                      <p>
                        <b>Ngày kết thúc đề xuất:</b>
                        {{ item.requested_end_date | date: 'dd/MM/yyyy' }}
                      </p>
                    }
                    @if (item.reason) {
                      <p><b>Lý do:</b> {{ item.reason }}</p>
                    }
                    @if (item.review_note) {
                      <p><b>Phản hồi:</b> {{ item.review_note }}</p>
                    }
                    <small>{{ item.changed_at | date: 'dd/MM/yyyy HH:mm' }}</small>
                  </div>
                </nz-timeline-item>
              }
            </nz-timeline>
          }
        </ng-container>
      </nz-drawer>

      <!-- MODAL CHẤM BÀI TỰ LUẬN QUIZ -->
      <nz-modal
        [(nzVisible)]="isQuizGradingModalVisible"
        [nzTitle]="
          quizGradingDetail()
            ? quizGradingDetail()!.quiz_title + ' — Lần ' + quizGradingDetail()!.attempt_no
            : 'Chi tiết bài làm Quiz'
        "
        [nzWidth]="auditModalWidth()"
        [nzFooter]="quizGradingFooter"
        (nzOnCancel)="closeQuizGradingModal()"
      >
        <ng-container *nzModalContent>
          @if (quizGradingLoading()) {
            <div class="drawer-loading"><nz-spin nzSimple nzSize="large"></nz-spin></div>
          } @else if (quizGradingDetail(); as gd) {
            <div
              style="margin-bottom: 14px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;"
            >
              <span><strong>Intern:</strong> {{ gd.intern_name }}</span>
              <span>| <strong>Điểm đạt:</strong> từ {{ gd.pass_score }}</span>
              <span
                >| <strong>Tổng điểm:</strong>
                {{ gd.score !== null && gd.score !== undefined ? gd.score : 'Chờ chấm' }}</span
              >
              @if (gd.grading_status === 'PENDING_GRADING') {
                <nz-tag nzColor="orange">Chờ chấm tự luận</nz-tag>
              } @else {
                <nz-tag [nzColor]="gd.passed ? 'green' : 'red'">
                  {{ gd.passed ? 'ĐẠT' : 'CHƯA ĐẠT' }}
                </nz-tag>
              }
            </div>

            @for (q of gd.questions; track q.question_id; let idx = $index) {
              <div
                style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 12px;"
              >
                <div
                  style="display: flex; justify-content: space-between; gap: 8px; margin-bottom: 6px;"
                >
                  <strong
                    >Câu {{ idx + 1 }} ({{
                      q.type === 'TEXT' ? 'Tự luận' : 'Trắc nghiệm'
                    }}):</strong
                  >
                  <span>Tối đa {{ q.max_score }} điểm</span>
                </div>
                <p style="margin-bottom: 8px;">{{ q.content }}</p>

                @if (q.type === 'TEXT') {
                  <div
                    style="background: #f8fafc; padding: 8px 10px; border-radius: 6px; margin-bottom: 8px;"
                  >
                    <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">
                      Câu trả lời của Intern:
                    </div>
                    <div style="white-space: pre-wrap;">
                      {{ q.text || '(Không có câu trả lời)' }}
                    </div>
                  </div>
                  @if (formatCorrectAnswerRef(q.correct_answer)) {
                    <div style="font-size: 12px; color: #475569; margin-bottom: 8px;">
                      <strong>Gợi ý đáp án:</strong> {{ formatCorrectAnswerRef(q.correct_answer) }}
                    </div>
                  }
                  <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start;">
                    <div>
                      <div style="font-size: 12px; margin-bottom: 4px;">
                        Điểm chấm (0 - {{ q.max_score }})
                      </div>
                      <nz-input-number
                        [(ngModel)]="gradingInputs[q.question_id].earned_score"
                        [nzMin]="0"
                        [nzMax]="q.max_score"
                        [nzStep]="0.5"
                      ></nz-input-number>
                    </div>
                    <div style="flex: 1; min-width: 220px;">
                      <div style="font-size: 12px; margin-bottom: 4px;">Nhận xét</div>
                      <textarea
                        nz-input
                        rows="2"
                        maxlength="1000"
                        placeholder="Nhập nhận xét cho câu trả lời..."
                        [(ngModel)]="gradingInputs[q.question_id].feedback"
                      ></textarea>
                    </div>
                  </div>
                } @else {
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <nz-tag [nzColor]="q.is_correct ? 'green' : 'red'">
                      {{ q.is_correct ? 'Đúng' : 'Sai' }} ({{ q.earned_score ?? 0 }}/{{
                        q.max_score
                      }})
                    </nz-tag>
                    <small style="color: #64748b;"
                      >Đã chọn: {{ q.selected_keys.join(', ') || 'Không chọn' }}</small
                    >
                  </div>
                }
              </div>
            }
          }
        </ng-container>
        <ng-template #quizGradingFooter>
          <button nz-button (click)="closeQuizGradingModal()">Đóng</button>
          @if (hasManualQuestions()) {
            <button
              nz-button
              nzType="primary"
              [nzLoading]="quizGradingSaving()"
              (click)="saveQuizGrades()"
            >
              Lưu điểm tự luận
            </button>
          }
        </ng-template>
      </nz-modal>

      <!-- MODAL DANH SÁCH ĐỀ XUẤT ĐÃ GỬI -->
      <nz-modal
        [(nzVisible)]="isProposalHistoryModalVisible"
        nzTitle="Đề xuất trạng thái đã gửi"
        (nzOnCancel)="closeProposalHistoryModal()"
        [nzFooter]="null"
        [nzWidth]="proposalHistoryModalWidth()"
      >
        <ng-container *nzModalContent>
          <nz-spin [nzSpinning]="proposalsLoading()">
            <nz-table
              #proposalTable
              class="responsive-card-table responsive-card-table--compact"
              [nzData]="proposals()"
              [nzPageSize]="8"
              nzSize="small"
            >
              <thead>
                <tr>
                  <th>Thực tập sinh</th>
                  <th>Loại đề xuất</th>
                  <th>Lý do</th>
                  <th>Trạng thái</th>
                  <th>Ngày tạo</th>
                </tr>
              </thead>
              <tbody>
                @for (item of proposalTable.data; track item.id) {
                  <tr>
                    <td data-label="Thực tập sinh">{{ item.intern_name || 'Thực tập sinh' }}</td>
                    <td data-label="Loại đề xuất">
                      <nz-tag [nzColor]="getProposalTypeColor(item.type)">
                        {{ getProposalTypeLabel(item.type) }}
                      </nz-tag>
                    </td>
                    <td data-label="Lý do">{{ item.reason }}</td>
                    <td data-label="Trạng thái">
                      <nz-tag [nzColor]="getReviewStatusColor(item.status)">
                        {{ getReviewStatusLabel(item.status) }}
                      </nz-tag>
                    </td>
                    <td data-label="Ngày tạo">{{ item.created_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                  </tr>
                }
              </tbody>
            </nz-table>
          </nz-spin>
        </ng-container>
      </nz-modal>

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
                  class="responsive-card-table responsive-card-table--compact"
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
                        <td data-label="Thời điểm">
                          <small>{{ formatDateTime(record.changed_at) }}</small>
                        </td>
                        <td data-label="Thực tập sinh">
                          <strong>{{ record.intern_name }}</strong>
                        </td>
                        <td data-label="Loại">
                          <nz-tag [nzColor]="record.action === 'ASSIGN' ? 'green' : 'blue'">
                            {{ record.action }}
                          </nz-tag>
                        </td>
                        <td data-label="Mentor cũ → Mới">
                          <span class="audit-transfer">
                            {{ record.old_mentor_name || 'None' }} &rarr;
                            <strong>{{ record.new_mentor_name }}</strong>
                          </span>
                        </td>
                        <td data-label="Người thực hiện">{{ record.changed_by_name }}</td>
                        <td data-label="Ghi chú">
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

      <!-- MODAL: DANH SÁCH BÀI KIỂM TRA CHỜ CHẤM TỰ LUẬN -->
      <nz-modal
        [(nzVisible)]="isPendingGradingsModalVisible"
        nzTitle="Danh sách bài kiểm tra tự luận chờ chấm"
        [nzFooter]="null"
        [nzWidth]="auditModalWidth()"
        (nzOnCancel)="closePendingGradingsModal()"
      >
        <ng-container *nzModalContent>
          <nz-spin [nzSpinning]="pendingGradingsLoading()">
            @if (pendingGradingsMemberFilter()) {
              <div style="margin-bottom: 12px; display: flex; justify-content: flex-end">
                <button nz-button nzType="link" nzSize="small" (click)="openPendingGradingsModal()">
                  Xem tất cả thực tập sinh
                </button>
              </div>
            }
            @if (pendingGradingsList().length > 0) {
              <nz-table
                #pendingGradingsTable
                [nzData]="pendingGradingsList()"
                [nzFrontPagination]="true"
                [nzPageSize]="8"
                nzSize="small"
              >
                <thead>
                  <tr>
                    <th>Thực tập sinh</th>
                    <th>Bài kiểm tra</th>
                    <th>Chờ chấm</th>
                    <th>Thời gian nộp</th>
                    <th nzAlign="right">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  @for (row of pendingGradingsTable.data; track row.attempt_id) {
                    <tr>
                      <td>
                        <div>
                          <strong>{{ row.intern_name }}</strong>
                        </div>
                        <small style="color: #6b7280">{{ row.intern_email }}</small>
                      </td>
                      <td>
                        <div>{{ row.quiz_title }}</div>
                        <small style="color: #6b7280">Lần {{ row.attempt_no }}</small>
                      </td>
                      <td>
                        <nz-tag nzColor="warning">{{ row.ungraded_questions }} câu tự luận</nz-tag>
                      </td>
                      <td>{{ row.submitted_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                      <td nzAlign="right">
                        <button
                          nz-button
                          nzType="primary"
                          nzSize="small"
                          (click)="openQuizGradingModal(row.attempt_id)"
                        >
                          Chấm bài
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </nz-table>
            } @else {
              <nz-empty
                nzNotFoundContent="Không có bài kiểm tra tự luận nào đang chờ chấm"
              ></nz-empty>
            }
          </nz-spin>
        </ng-container>
      </nz-modal>
    </div>
  `,
  styles: [
    `
      .position-caption {
        color: #595959;
        margin-top: 4px;
        font-size: 13px;
      }
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
        flex-wrap: wrap;
        gap: 4px;
        justify-content: flex-end;
      }

      .pending-tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }

      .text-muted {
        color: #9ca3af;
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
        flex-wrap: wrap;
        gap: 8px;
        padding-top: 10px;
        border-top: 1px solid #f3f4f6;
      }

      .card-mobile-footer button {
        flex: 1 1 calc(50% - 4px);
        min-height: 44px;
      }

      .card-mobile-footer .detail-action {
        flex-basis: 100%;
      }

      .proposal-intern-card,
      .status-history-entry {
        padding: 12px 16px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #f9fafb;
      }

      .proposal-intern-card {
        margin-bottom: 16px;
      }

      .proposal-intern-header,
      .status-history-header,
      .status-transition {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      .proposal-intern-header > div {
        min-width: 0;
        overflow-wrap: anywhere;
      }

      .proposal-intern-details {
        display: flex;
        flex-direction: column;
        gap: 6px;
        color: #374151;
        font-size: 13px;
      }

      .proposal-form {
        margin-top: 16px;
      }

      .drawer-loading {
        display: flex;
        justify-content: center;
        padding: 40px 0;
      }

      .status-history-timeline {
        display: block;
        padding-top: 8px;
      }

      .status-history-entry {
        margin-bottom: 8px;
        overflow-wrap: anywhere;
      }

      .status-history-header {
        justify-content: space-between;
        margin-bottom: 10px;
      }

      .status-transition {
        margin-bottom: 8px;
      }

      .status-history-entry p {
        margin: 6px 0;
      }

      .status-history-entry small {
        color: #9ca3af;
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
         TABLET BREAKPOINT (769px – 1023px)
         ========================================================================== */
      @media screen and (min-width: 769px) and (max-width: 1023px) {
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
         MOBILE BREAKPOINT (<= 768px)
         ========================================================================== */
      @media screen and (max-width: 768px) {
        .table-responsive {
          overflow-x: visible;
        }

        .desktop-table {
          display: none;
        }

        .mobile-cards {
          display: flex;
        }

        /* Filter mobile: vertical layout */
        .filter-toolbar {
          display: flex;
          flex-direction: column;
          gap: 10px;
          width: 100%;
        }

        .filter-item,
        .filter-item.search-box {
          width: 100%;
          min-width: 0;
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

        .proposal-form input[nz-input],
        .proposal-form textarea[nz-input],
        .proposal-form nz-select,
        .proposal-form nz-date-picker {
          font-size: 16px;
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

      @media screen and (max-width: 480px) {
        .status-history-header,
        .status-transition {
          flex-wrap: wrap;
        }
      }
    `,
  ],
})
export class MentorInternManagementComponent implements OnInit {
  protected readonly positionLabel = internshipPositionLabel;
  private readonly mentorService = inject(MentorService);
  private readonly internshipService = inject(InternshipService);
  private readonly message = inject(NzMessageService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  totalPendingQuizGradings = computed(() =>
    this.interns().reduce((sum, item) => sum + (item.pending_quiz_gradings ?? 0), 0),
  );

  loading = signal<boolean>(false);
  interns = signal<MentorInternListItem[]>([]);
  internships = signal<{ id: string; name: string }[]>([]);
  proposals = signal<InternshipProposalItem[]>([]);
  proposalsLoading = signal<boolean>(false);

  searchQuery = '';
  selectedStatus = '';
  selectedInternshipId = '';

  // Drawer detail state
  isDetailDrawerOpen = signal<boolean>(false);
  detailLoading = signal<boolean>(false);
  detail = signal<MentorInternDetail | null>(null);
  activeDetailTab = signal<number>(0);

  // Proposal and internship status state
  selectedProposalIntern = signal<MentorInternListItem | null>(null);
  proposalSubmitting = signal<boolean>(false);
  statusHistoryLoading = signal<boolean>(false);
  statusHistoryItems = signal<InternshipStatusHistoryItem[]>([]);
  isProposalModalVisible = false;
  isProposalHistoryModalVisible = false;
  isStatusHistoryDrawerVisible = false;
  statusHistoryDrawerTitle = 'Lịch sử trạng thái';
  proposalType: 'EXTEND' | 'STOP' | 'COMPLETE' = 'EXTEND';
  proposalEndDate: Date | null = null;
  proposalReason = '';

  // Audit history modal state
  isAuditModalVisible = false;
  auditLoading = signal<boolean>(false);
  allAuditHistory = signal<MentorAssignmentHistoryItem[]>([]);

  // Quiz essay grading modal state
  isQuizGradingModalVisible = false;
  quizGradingLoading = signal<boolean>(false);
  quizGradingSaving = signal<boolean>(false);
  quizGradingDetail = signal<QuizAttemptGradingDetail | null>(null);
  gradingInputs: Record<string, { earned_score: number; feedback: string }> = {};

  // Pending quiz gradings list modal state
  isPendingGradingsModalVisible = signal<boolean>(false);
  pendingGradingsLoading = signal<boolean>(false);
  pendingGradingsList = signal<PendingQuizGradingItem[]>([]);
  pendingGradingsMemberFilter = signal<string | null>(null);

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

  proposalModalWidth = computed(() => (this.windowWidth() <= 767 ? 'calc(100vw - 16px)' : '540px'));
  proposalHistoryModalWidth = computed(() =>
    this.windowWidth() <= 767 ? 'calc(100vw - 16px)' : '900px',
  );
  statusHistoryDrawerWidth = computed(() => (this.windowWidth() <= 767 ? '100%' : '500px'));

  ngOnInit(): void {
    this.loadInterns();
    this.loadProposals();
    this.loadAuxiliaryData();
    this.route.queryParams.subscribe((params) => {
      if (params['openPendingGradings'] === '1') {
        this.openPendingGradingsModal();
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { openPendingGradings: null },
          queryParamsHandling: 'merge',
          replaceUrl: true,
        });
      }
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

  loadProposals(): void {
    this.proposalsLoading.set(true);
    this.mentorService.getMentorProposals().subscribe({
      next: (data) => {
        this.proposals.set(data);
        this.proposalsLoading.set(false);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.proposalsLoading.set(false);
        this.message.error(err?.error?.detail || 'Không thể tải danh sách đề xuất');
        this.cdr.markForCheck();
      },
    });
  }

  getPendingProposalForIntern(internId: string): InternshipProposalItem | undefined {
    return this.proposals().find(
      (proposal) =>
        (proposal.internship_member_id === internId || proposal.intern_id === internId) &&
        proposal.status === 'PENDING',
    );
  }

  hasPendingExtendProposal(internId: string): boolean {
    return this.proposals().some(
      (proposal) =>
        (proposal.internship_member_id === internId || proposal.intern_id === internId) &&
        proposal.type === 'EXTEND' &&
        proposal.status === 'PENDING',
    );
  }

  isProposalDisabled(intern: MentorInternListItem): boolean {
    return intern.status === 'COMPLETED' || intern.status === 'STOPPED';
  }

  getProposalDisabledTooltip(intern: MentorInternListItem): string {
    if (intern.status === 'COMPLETED') return 'Thực tập sinh đã hoàn thành kỳ thực tập';
    if (intern.status === 'STOPPED') return 'Thực tập sinh đã dừng thực tập';
    return '';
  }

  openProposalModal(intern: MentorInternListItem): void {
    this.selectedProposalIntern.set(intern);
    this.proposalReason = '';
    this.proposalEndDate = null;
    if (this.hasPendingExtendProposal(intern.id)) {
      this.proposalType = 'COMPLETE';
    } else {
      this.proposalType = 'EXTEND';
      if (intern.end_date) {
        const proposedDate = new Date(intern.end_date);
        proposedDate.setDate(proposedDate.getDate() + 30);
        this.proposalEndDate = proposedDate;
      }
    }
    this.isProposalModalVisible = true;
    this.cdr.markForCheck();
  }

  closeProposalModal(): void {
    this.isProposalModalVisible = false;
    this.selectedProposalIntern.set(null);
  }

  disabledProposalEndDate = (current: Date): boolean => {
    const intern = this.selectedProposalIntern();
    if (!intern || !current) return false;
    const currentEndDate = intern.end_date ? new Date(intern.end_date) : new Date();
    return current.getTime() <= currentEndDate.getTime();
  };

  isSubmitProposalDisabled(): boolean {
    return !this.proposalReason.trim() || (this.proposalType === 'EXTEND' && !this.proposalEndDate);
  }

  submitProposal(): void {
    const intern = this.selectedProposalIntern();
    if (!intern || this.isSubmitProposalDisabled()) return;
    if (this.proposalType === 'EXTEND' && this.hasPendingExtendProposal(intern.id)) {
      this.message.error('Đã có đề xuất gia hạn đang chờ xử lý');
      return;
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

    this.proposalSubmitting.set(true);
    this.mentorService.createProposal(payload).subscribe({
      next: () => {
        this.proposalSubmitting.set(false);
        this.closeProposalModal();
        this.message.success('Đã gửi đề xuất thành công');
        this.loadProposals();
        this.loadInterns();
      },
      error: (err) => {
        this.proposalSubmitting.set(false);
        this.message.error(err?.error?.detail || err?.message || 'Không thể gửi đề xuất');
        this.cdr.markForCheck();
      },
    });
  }

  openStatusHistoryDrawer(intern: MentorInternListItem): void {
    this.statusHistoryDrawerTitle = `Lịch sử trạng thái: ${intern.intern_name}`;
    this.isStatusHistoryDrawerVisible = true;
    this.statusHistoryLoading.set(true);
    this.statusHistoryItems.set([]);
    this.mentorService.getInternStatusHistory(intern.id).subscribe({
      next: (items) => {
        this.statusHistoryItems.set(items);
        this.statusHistoryLoading.set(false);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.statusHistoryLoading.set(false);
        this.message.error(err?.error?.detail || 'Không thể tải lịch sử trạng thái');
        this.cdr.markForCheck();
      },
    });
  }

  closeStatusHistoryDrawer(): void {
    this.isStatusHistoryDrawerVisible = false;
  }

  openProposalHistoryModal(): void {
    this.isProposalHistoryModalVisible = true;
    this.loadProposals();
  }

  closeProposalHistoryModal(): void {
    this.isProposalHistoryModalVisible = false;
  }

  openDetail(memberId: string): void {
    this.detail.set(null);
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

  getProposalTypeColor(type: string): string {
    if (type === 'EXTEND') return 'cyan';
    if (type === 'COMPLETE') return 'green';
    if (type === 'STOP' || type === 'TERMINATE') return 'red';
    return 'blue';
  }

  getProposalTypeLabel(type: string): string {
    if (type === 'EXTEND') return 'Gia hạn';
    if (type === 'COMPLETE') return 'Hoàn thành';
    if (type === 'STOP' || type === 'TERMINATE') return 'Dừng thực tập';
    return type;
  }

  getReviewStatusColor(status: string): string {
    if (status === 'APPROVED') return 'success';
    if (status === 'REJECTED') return 'error';
    return 'warning';
  }

  getReviewStatusLabel(status: string): string {
    if (status === 'APPROVED') return 'Đã duyệt';
    if (status === 'REJECTED') return 'Từ chối';
    return 'Chờ duyệt';
  }

  getTimelineItemColor(item: InternshipStatusHistoryItem): string {
    if (item.action === 'INITIAL') return 'gray';
    if (item.proposal_status === 'APPROVED') return 'green';
    if (item.proposal_status === 'REJECTED') return 'red';
    return 'blue';
  }

  getHistoryActionColor(action: string): string {
    if (action === 'INITIAL') return 'default';
    return this.getProposalTypeColor(action);
  }

  getHistoryActionLabel(action: string): string {
    if (action === 'INITIAL') return 'Bắt đầu';
    return `Đề xuất ${this.getProposalTypeLabel(action).toLowerCase()}`;
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

  private formatDateISO(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  hasManualQuestions(): boolean {
    const gd = this.quizGradingDetail();
    return !!gd?.questions.some((q) => q.needs_manual_grading);
  }

  openQuizGradingModal(attemptId: string): void {
    this.isQuizGradingModalVisible = true;
    this.quizGradingLoading.set(true);
    this.quizGradingDetail.set(null);
    this.gradingInputs = {};
    this.mentorService.getQuizAttemptDetail(attemptId).subscribe({
      next: (res) => {
        for (const q of res.questions) {
          if (q.needs_manual_grading) {
            this.gradingInputs[q.question_id] = {
              earned_score: q.earned_score ?? 0,
              feedback: q.feedback ?? '',
            };
          }
        }
        this.quizGradingDetail.set(res);
        this.quizGradingLoading.set(false);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.message.error(err?.error?.detail || 'Không thể tải chi tiết bài làm');
        this.quizGradingLoading.set(false);
        this.isQuizGradingModalVisible = false;
        this.cdr.markForCheck();
      },
    });
  }

  closeQuizGradingModal(): void {
    this.isQuizGradingModalVisible = false;
    this.quizGradingDetail.set(null);
  }

  saveQuizGrades(): void {
    const gd = this.quizGradingDetail();
    if (!gd) return;
    const grades = gd.questions
      .filter((q) => q.needs_manual_grading)
      .map((q) => {
        const input = this.gradingInputs[q.question_id];
        return {
          question_id: q.question_id,
          earned_score: Number(input?.earned_score ?? 0),
          feedback: input?.feedback?.trim() || null,
        };
      });
    if (grades.length === 0) return;

    this.quizGradingSaving.set(true);
    this.mentorService.gradeQuizAttempt(gd.attempt_id, { grades }).subscribe({
      next: (updated) => {
        this.quizGradingDetail.set(updated);
        this.quizGradingSaving.set(false);
        this.message.success('Đã lưu điểm tự luận và cập nhật kết quả bài kiểm tra');
        this.loadInterns();
        if (this.isPendingGradingsModalVisible()) {
          this.loadPendingGradings(this.pendingGradingsMemberFilter());
        }
        const currentDetail = this.detail();
        if (currentDetail) {
          this.mentorService.getInternDetail(currentDetail.id).subscribe({
            next: (detail) => {
              this.detail.set(detail);
              this.cdr.markForCheck();
            },
          });
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.message.error(err?.error?.detail || 'Lưu điểm thất bại');
        this.quizGradingSaving.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  formatCorrectAnswerRef(raw: unknown): string {
    if (raw === null || raw === undefined) return '';
    if (Array.isArray(raw)) {
      return raw
        .map((v) => String(v ?? '').trim())
        .filter((v) => v.length > 0)
        .join(', ');
    }
    return String(raw).trim();
  }

  openPendingGradingsModal(memberId?: string): void {
    const filterId = memberId ?? null;
    this.pendingGradingsMemberFilter.set(filterId);
    this.isPendingGradingsModalVisible.set(true);
    this.loadPendingGradings(filterId);
  }

  closePendingGradingsModal(): void {
    this.isPendingGradingsModalVisible.set(false);
    this.pendingGradingsMemberFilter.set(null);
  }

  private loadPendingGradings(memberId: string | null): void {
    this.pendingGradingsLoading.set(true);
    this.mentorService.getPendingQuizAttempts(memberId).subscribe({
      next: (list) => {
        this.pendingGradingsList.set(list);
        this.pendingGradingsLoading.set(false);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.message.error(err?.error?.detail || 'Không tải được danh sách bài chờ chấm');
        this.pendingGradingsLoading.set(false);
        this.cdr.markForCheck();
      },
    });
  }
}
