import { DatePipe } from '@angular/common';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzResultModule } from 'ng-zorro-antd/result';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzSelectModule } from 'ng-zorro-antd/select';
// 👉 Thêm Import NzDatePickerModule
import { NzDatePickerModule } from 'ng-zorro-antd/date-picker';
import { FormsModule } from '@angular/forms';
import { Internship, InternshipService } from '../../core/api/internship.service';
import { DashboardService, DashboardResponse } from '../../core/api/dashboard.service';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  computed,
  inject,
  OnDestroy,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NzAvatarModule } from 'ng-zorro-antd/avatar';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDropdownModule } from 'ng-zorro-antd/dropdown';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzLayoutModule } from 'ng-zorro-antd/layout';
import { NzMenuModule } from 'ng-zorro-antd/menu';
import { NzPopoverModule } from 'ng-zorro-antd/popover';
import { NzProgressModule } from 'ng-zorro-antd/progress';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTooltipModule } from 'ng-zorro-antd/tooltip';
import { AuthService } from '../../core/api/auth.service';
import { EvaluationsComponent } from '../evaluations/evaluations.component';
import { InternshipManagementComponent } from '../internships/internship-management.component';
import { LearningComponent } from '../learning/learning.component';
import { MentorInternManagementComponent } from '../mentor/mentor-intern-management.component';
import { MentorInternshipStatusComponent } from '../mentor/mentor-internship-status.component';
import { ProfileComponent } from '../profile/profile.component';
import { TaskManagementComponent } from '../tasks/task-management.component';
import { TrainingManagementComponent } from '../training/training-management.component';
import { UserManagementComponent } from '../users/user-management.component';
import { RequestManagementComponent } from '../requests/request-management.component';
import { NotificationManagementComponent } from '../notifications/notification-management.component';
import { Notification, NotificationService } from '../../core/api/notification.service';
import { AsyncPipe, SlicePipe } from '@angular/common';
import { Subscription, interval } from 'rxjs';
import { AssistantChatComponent } from '../assistant/assistant-chat.component';
import { ChangePasswordComponent } from '../auth/change-password.component';

enum Role {
  Intern = 'INTERN',
  Mentor = 'MENTOR',
  Admin = 'ADMIN',
}

interface Item {
  id: string;
  label: string;
  icon: string;
}

interface Dashboard {
  roleLabel: string;
  name: string;
  initials: string;
  greeting: string;
  description: string;
  nav: Item[];
  metrics: { label: string; value: string; note: string; tone: string; icon: string }[];
}

const common: Item[] = [{ id: 'notifications', label: 'Thông báo', icon: 'bell' }];

const dashboards: Record<Role, Dashboard> = {
  [Role.Intern]: {
    roleLabel: 'Thực tập sinh',
    name: 'Nguyễn Văn An',
    initials: 'NA',
    greeting: 'Chào buổi sáng, Nguyễn Văn An!',
    description: 'Theo dõi lộ trình, task và kết quả thực tập của bạn.',
    nav: [
      { id: 'roadmap', label: 'Lộ trình học tập', icon: 'read' },
      { id: 'documents', label: 'Tài liệu học tập', icon: 'file-text' },
      { id: 'quizzes', label: 'Bài kiểm tra', icon: 'form' },
      { id: 'tasks', label: 'Task của tôi', icon: 'check-square' },
      { id: 'evaluations', label: 'Đánh giá', icon: 'star' },
      ...common,
    ],
    metrics: [
      {
        label: 'Tiến độ học tập',
        value: '75%',
        note: '9/12 nội dung hoàn thành',
        tone: 'green',
        icon: 'read',
      },
      { label: 'Bài kiểm tra', value: '4/6', note: 'Đã hoàn thành', tone: 'purple', icon: 'form' },
      {
        label: 'Task được giao',
        value: '7',
        note: '5 đang thực hiện',
        tone: 'orange',
        icon: 'check-square',
      },
      {
        label: 'Đánh giá hiện tại',
        value: '8.5/10',
        note: 'Điểm trung bình',
        tone: 'pink',
        icon: 'star',
      },
    ],
  },
  [Role.Mentor]: {
    roleLabel: 'Mentor',
    name: 'Lê Minh Hoàng',
    initials: 'LH',
    greeting: 'Xin chào, Lê Minh Hoàng!',
    description: 'Đồng hành và phát triển các thực tập sinh phụ trách.',
    nav: [
      { id: 'interns', label: 'Quản lý Intern', icon: 'team' },
      { id: 'tasks', label: 'Quản lý Task', icon: 'check-square' },
      { id: 'evaluations', label: 'Đánh giá', icon: 'star' },
      { id: 'internship-status', label: 'Trạng thái thực tập', icon: 'calendar' },
      ...common,
    ],
    metrics: [
      {
        label: 'Intern phụ trách',
        value: '8',
        note: '6 đang thực tập',
        tone: 'blue',
        icon: 'team',
      },
      {
        label: 'Task đang thực hiện',
        value: '24',
        note: '3 task mới tuần này',
        tone: 'green',
        icon: 'check-square',
      },
      {
        label: 'Bài nộp chờ review',
        value: '7',
        note: 'Cần phản hồi',
        tone: 'pink',
        icon: 'file-text',
      },
      {
        label: 'Đánh giá sắp hạn',
        value: '5',
        note: 'Trong 7 ngày tới',
        tone: 'orange',
        icon: 'star',
      },
    ],
  },
  [Role.Admin]: {
    roleLabel: 'Quản trị viên',
    name: 'Administrator',
    initials: 'AD',
    greeting: 'Xin chào, Administrator!',
    description: 'Tổng quan vận hành hệ thống quản lý thực tập sinh.',
    nav: [
      { id: 'users', label: 'Quản lý người dùng', icon: 'team' },
      { id: 'internships', label: 'Quản lý thực tập', icon: 'solution' },
      { id: 'training', label: 'Quản lý đào tạo (LMS)', icon: 'book' },
      { id: 'evaluations', label: 'Quản lý đánh giá', icon: 'star' },
      { id: 'requests', label: 'Quản lý yêu cầu', icon: 'audit' },
      ...common,
    ],
    metrics: [
      {
        label: 'Tổng người dùng',
        value: '156',
        note: 'Tăng 12% so với tháng trước',
        tone: 'blue',
        icon: 'team',
      },
      {
        label: 'Tổng thực tập sinh',
        value: '48',
        note: 'Đang hoạt động',
        tone: 'green',
        icon: 'user',
      },
      {
        label: 'Tổng Mentor',
        value: '12',
        note: 'Đang phụ trách Intern',
        tone: 'orange',
        icon: 'solution',
      },
      {
        label: 'Yêu cầu chờ duyệt',
        value: '5',
        note: 'Gia hạn, dừng, kết thúc',
        tone: 'pink',
        icon: 'audit',
      },
    ],
  },
};

@Component({
  selector: 'app-dashboard-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    DatePipe,
    AsyncPipe,
    SlicePipe,
    NzSpinModule,
    NzResultModule,
    NzEmptyModule,
    NzSelectModule,
    NzDatePickerModule,
    FormsModule,
    NzAvatarModule,
    NzBadgeModule,
    NzButtonModule,
    NzCardModule,
    NzDropdownModule,
    NzIconModule,
    NzLayoutModule,
    NzMenuModule,
    NzPopoverModule,
    NzProgressModule,
    NzTagModule,
    NzTooltipModule,
    EvaluationsComponent,
    InternshipManagementComponent,
    LearningComponent,
    MentorInternManagementComponent,
    MentorInternshipStatusComponent,
    ProfileComponent,
    TaskManagementComponent,
    TrainingManagementComponent,
    UserManagementComponent,
    RequestManagementComponent,
    NotificationManagementComponent,
    AssistantChatComponent,
    ChangePasswordComponent,
  ],

  styles: [
    `
      :host ::ng-deep {
        nz-sider.sidebar,
        .sidebar {
          position: fixed !important;
          top: 64px !important;
          left: 0 !important;
          bottom: 0 !important;
          height: calc(100dvh - 64px) !important;
          width: 250px !important;
          min-width: 250px !important;
          max-width: 250px !important;
          z-index: 100 !important;
          overflow-y: auto !important;
          overflow-x: hidden !important;
          background: #fff !important;
          border-right: 0 !important;
          box-sizing: border-box !important;

          .ant-layout-sider-children {
            display: flex !important;
            flex-direction: column !important;
            height: 100% !important;
            min-height: 100% !important;
            width: 100% !important;
          }
        }

        .dashboard-main,
        nz-layout.dashboard-main {
          margin-left: 250px !important;
          min-height: 100dvh !important;
          width: calc(100% - 250px) !important;
          padding-top: 64px !important;
          box-sizing: border-box !important;
          display: flex !important;
          flex-direction: column !important;
          background: #f4f7fc !important;
        }

        .dashboard-shell--sidebar-collapsed {
          nz-sider.sidebar,
          .sidebar {
            width: 72px !important;
            min-width: 72px !important;
            max-width: 72px !important;
          }

          .dashboard-main,
          nz-layout.dashboard-main {
            margin-left: 72px !important;
            width: calc(100% - 72px) !important;
          }
        }

        .topbar {
          position: fixed !important;
          top: 0 !important;
          right: 0 !important;
          left: 0 !important;
          z-index: 120 !important;
          width: 100% !important;
          height: 64px !important;
          box-sizing: border-box !important;
        }

        .metric-card,
        .metric-card .ant-card-body {
          display: flex !important;
          flex-direction: column !important;
          align-items: center !important;
          justify-content: center !important;
          text-align: center !important;
          padding: 18px 12px !important;
        }

        .metric-card__content {
          display: flex !important;
          flex-direction: column !important;
          align-items: center !important;
          justify-content: center !important;
          text-align: center !important;
          width: 100% !important;
        }

        .metric-card .metric-icon {
          margin: 0 auto 10px auto !important;
        }

        .metric-card__label,
        .metric-card p {
          margin: 2px 0 6px 0 !important;
          font-weight: 650 !important;
          text-align: center !important;
          width: 100% !important;
        }

        .metric-card__value,
        .metric-card strong {
          display: block !important;
          font-size: 28px !important;
          text-align: center !important;
          width: 100% !important;
          line-height: 1.2 !important;
        }

        @media (max-width: 768px) {
          .topbar {
            height: 56px !important;
          }
          nz-sider.sidebar,
          .sidebar {
            top: 56px !important;
            right: auto !important;
            bottom: 0 !important;
            width: 72px !important;
            min-width: 72px !important;
            max-width: 72px !important;
            height: calc(100dvh - 56px) !important;
            padding: 12px 8px !important;
            overflow-x: hidden !important;
            overflow-y: auto !important;
            border-right: 0 !important;
            border-bottom: 0 !important;
            transform: none !important;
          }
          .dashboard-main,
          nz-layout.dashboard-main {
            margin-left: 72px !important;
            width: calc(100% - 72px) !important;
            max-width: calc(100% - 72px) !important;
            min-width: 0 !important;
            padding-top: 56px !important;
            overflow-x: hidden !important;
          }
          .breadcrumb {
            word-break: break-word !important;
            overflow-wrap: break-word !important;
          }
        }
      }
    `,
  ],
  template: `
    <div class="dashboard-shell" [class.dashboard-shell--sidebar-collapsed]="isSidebarCollapsed()">
      <nz-layout>
        <nz-sider class="sidebar" [nzWidth]="250" nzTheme="light">
          <ul nz-menu nzMode="inline" class="sidebar__nav" aria-label="Chức năng">
            <li
              nz-menu-item
              role="button"
              tabindex="0"
              [nzSelected]="section() === 'overview'"
              (click)="choose('overview')"
              (keydown.enter)="choose('overview')"
              title="Tổng quan"
            >
              <span nz-icon nzType="home"></span>
              <span class="sidebar__label">Tổng quan</span>
            </li>
            @for (item of dashboard().nav; track item.id) {
              <li
                nz-menu-item
                role="button"
                tabindex="0"
                [nzSelected]="section() === item.id"
                (click)="openSection(item.id)"
                (keydown.enter)="openSection(item.id)"
                [attr.title]="item.label"
              >
                <span nz-icon [nzType]="item.icon"></span>
                <span class="sidebar__label">{{ item.label }}</span>
              </li>
            }
          </ul>
        </nz-sider>
        <nz-layout class="dashboard-main">
          <nz-header class="topbar">
            <div class="topbar__left">
              <div class="topbar__brand">
                <img src="/itms-logo.png" alt="ITMS — Hệ thống quản lý thực tập sinh" />
              </div>
              <button
                nz-button
                nzType="text"
                type="button"
                class="sidebar-collapse-toggle"
                [attr.aria-label]="
                  isSidebarCollapsed() ? 'Mở rộng thanh điều hướng' : 'Thu gọn thanh điều hướng'
                "
                [attr.aria-expanded]="!isSidebarCollapsed()"
                [title]="
                  isSidebarCollapsed() ? 'Mở rộng thanh điều hướng' : 'Thu gọn thanh điều hướng'
                "
                (click)="toggleSidebar()"
              >
                <span nz-icon [nzType]="isSidebarCollapsed() ? 'right' : 'left'"></span>
              </button>
            </div>
            <div class="topbar__right">
              @if (role() === 'ADMIN') {
                <nz-badge [nzCount]="(unreadCount$ | async) ?? 0" [nzOverflowCount]="99">
                  <button
                    nz-button
                    nzType="text"
                    class="notification"
                    (click)="choose('notifications')"
                    title="Quản lý thông báo"
                  >
                    <span nz-icon nzType="bell"></span>
                  </button>
                </nz-badge>
              } @else {
                <nz-badge [nzCount]="(unreadCount$ | async) ?? 0" [nzOverflowCount]="99">
                  <button
                    nz-button
                    nzType="text"
                    class="notification"
                    nz-popover
                    [nzPopoverContent]="notifPopoverTemplate"
                    nzPopoverTrigger="click"
                    nzPopoverPlacement="bottomRight"
                    nzPopoverOverlayClassName="notif-popover-overlay"
                    [(nzPopoverVisible)]="isNotifPopoverVisible"
                    (nzPopoverVisibleChange)="onNotifPopoverVisibleChange($event)"
                    title="Thông báo"
                  >
                    <span nz-icon nzType="bell"></span>
                  </button>
                </nz-badge>
              }
              <button
                nz-button
                nzType="text"
                type="button"
                class="account-trigger"
                nz-dropdown
                [nzDropdownMenu]="accountMenu"
                nzTrigger="click"
                nzPlacement="bottomRight"
                aria-label="Mở menu tài khoản"
              >
                <nz-avatar
                  class="avatar"
                  [nzSrc]="userAvatar() ?? undefined"
                  [nzText]="userInitials()"
                ></nz-avatar>
                <span class="user-summary">
                  <strong>{{ userName() }}</strong>
                  <small>{{ dashboard().roleLabel }}</small>
                </span>
                <span nz-icon nzType="down" class="account-trigger__arrow"></span>
              </button>
              <nz-dropdown-menu #accountMenu="nzDropdownMenu">
                <ul nz-menu class="user-account-menu">
                  <li nz-menu-item (click)="choose('profile')">
                    <span nz-icon nzType="user"></span>
                    <span>Hồ sơ cá nhân</span>
                  </li>
                  <li nz-menu-item (click)="openSection('change-password')">
                    <span nz-icon nzType="key"></span>
                    <span>Đổi mật khẩu</span>
                  </li>
                  <li nz-menu-divider></li>
                  <li nz-menu-item (click)="logout()">
                    <span nz-icon nzType="logout"></span>
                    <span>Đăng xuất</span>
                  </li>
                </ul>
              </nz-dropdown-menu>
            </div>
          </nz-header>
          <nz-content class="content">
            <div class="breadcrumb">
              <span nz-icon nzType="home"></span> <span>/</span> {{ activeLabel() }}
            </div>

            @if (section() === 'overview') {
              @if (role() === 'ADMIN') {
                <div
                  style="margin-bottom: 20px; display: flex; align-items: center; justify-content: flex-end; gap: 10px;"
                >
                  <span>Lọc theo đợt thực tập:</span>
                  <nz-select
                    style="width: 250px"
                    [(ngModel)]="selectedInternshipId"
                    (ngModelChange)="onInternshipChange($event)"
                    nzAllowClear
                    nzPlaceHolder="Tất cả"
                  >
                    @for (internship of internships(); track internship.id) {
                      <nz-option [nzValue]="internship.id" [nzLabel]="internship.name"></nz-option>
                    }
                  </nz-select>
                </div>
              }
              @if (isLoading()) {
                <div style="text-align: center; padding: 50px;">
                  <nz-spin nzSimple nzSize="large"></nz-spin>
                </div>
              } @else if (hasError()) {
                <nz-result
                  nzStatus="error"
                  nzTitle="Lỗi tải dữ liệu"
                  [nzSubTitle]="dashboardError()"
                >
                  <div nz-result-extra>
                    <button nz-button nzType="primary" (click)="loadDashboard()">Thử lại</button>
                  </div>
                </nz-result>
              } @else {
                <section class="metric-grid">
                  @for (metric of dashboardData()?.metrics; track metric.label) {
                    <nz-card class="metric-card" [nzBordered]="false" style="text-align: center;">
                      <div
                        class="metric-card__content"
                        style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; width: 100%;"
                      >
                        <i
                          class="metric-icon metric-icon--{{
                            metricStyles[metric.key]?.tone || 'blue'
                          }}"
                          nz-icon
                          [nzType]="metricStyles[metric.key]?.icon || 'appstore'"
                          style="margin: 0 auto 10px auto;"
                        ></i>
                        <p
                          class="metric-card__label"
                          style="text-align: center; margin: 2px 0 6px 0; width: 100%;"
                        >
                          {{ metric.label }}
                        </p>
                        <strong
                          class="metric-card__value"
                          style="display: block; text-align: center; width: 100%; font-size: 28px; line-height: 1.2;"
                          >{{ metric.value }}</strong
                        >
                      </div>
                    </nz-card>
                  }
                </section>
                <section class="dashboard-grid">
                  <nz-card class="panel panel--wide" [nzBordered]="false">
                    <div class="panel__title">
                      <h2>
                        {{
                          dashboard().roleLabel === 'Mentor'
                            ? 'Danh sách Intern của tôi'
                            : dashboard().roleLabel === 'Quản trị viên'
                              ? 'Đợt thực tập gần đây'
                              : 'Task gần đây'
                        }}
                      </h2>
                      <button
                        nz-button
                        nzType="link"
                        (click)="
                          dashboard().roleLabel === 'Mentor' ? choose('interns') : choose('tasks')
                        "
                      >
                        Xem tất cả
                      </button>
                    </div>
                    @if (dashboardData()?.recent_items?.length) {
                      <div class="table-head">
                        <span>Tên / thông tin</span><span>Trạng thái</span><span>Hạn</span>
                      </div>
                      @for (row of dashboardData()?.recent_items; track row.title) {
                        <div class="table-row">
                          <span
                            ><b>{{ row.title }}</b
                            ><small>{{ row.subtitle }}</small></span
                          >
                          <nz-tag [nzColor]="statusColor(row.status || '')" class="tag">{{
                            statusLabel(row.status || '')
                          }}</nz-tag>
                          <span>{{ row.due_at ? (row.due_at | date: 'dd/MM/yyyy') : '-' }}</span>
                        </div>
                      }
                    } @else {
                      <nz-empty nzNotFoundContent="Không có dữ liệu"></nz-empty>
                    }
                  </nz-card>

                  @if (dashboardData()?.progress) {
                    <nz-card class="panel" [nzBordered]="false">
                      <div class="panel__title">
                        <h2>Lộ trình & tiến độ</h2>
                        <button nz-button nzType="link" (click)="choose(detailsTarget())">
                          Xem chi tiết
                        </button>
                      </div>
                      <div style="padding: 20px 0; text-align: center;">
                        <nz-progress
                          nz-tooltip
                          [nzTooltipTitle]="progressTooltip(dashboardData()?.progress)"
                          nzTooltipPlacement="top"
                          [nzPercent]="formatPercentNumber(dashboardData()?.progress?.percent)"
                          [nzFormat]="formatProgress"
                          nzType="circle"
                        ></nz-progress>
                        <p style="margin-top: 10px;">
                          Hoàn thành {{ dashboardData()?.progress?.completed }}/{{
                            dashboardData()?.progress?.total
                          }}
                        </p>
                      </div>
                    </nz-card>
                  }
                </section>
              }
            } @else if (section() === 'profile') {
              <!-- UC-5: Hồ sơ cá nhân -->
              <app-profile />
            } @else if (section() === 'change-password') {
              <app-change-password [embedded]="true" />
            } @else if (
              section() === 'internships' && (role() === 'ADMIN' || role() === 'MENTOR')
            ) {
              <app-internship-management />
            } @else if (section() === 'users' && (role() === 'ADMIN' || role() === 'MENTOR')) {
              <!-- UC-14: Quản lý người dùng -->
              <app-user-management />
            } @else if (section() === 'requests') {
              <!-- UC-17: Quản lý yêu cầu thực tập -->
              <app-request-management />
            } @else if (section() === 'interns' && (role() === 'MENTOR' || role() === 'ADMIN')) {
              <!-- UC-11: Mentor quản lý Intern -->
              <app-mentor-intern-management />
            } @else if (
              section() === 'internship-status' && (role() === 'MENTOR' || role() === 'ADMIN')
            ) {
              <!-- UC-13: Quản lý trạng thái thực tập (Mentor đề xuất gia hạn, dừng, kết thúc) -->
              <app-mentor-internship-status />
            } @else if (section() === 'training' && (role() === 'ADMIN' || role() === 'MENTOR')) {
              <!-- UC-16: Quản lý đào tạo (LMS) -->
              <app-training-management />
            } @else if (section() === 'tasks' && (role() === 'MENTOR' || role() === 'INTERN')) {
              <!-- UC-7: Quản lý Task — Mentor giao/review, Intern nộp (Sprint 2) -->
              <app-task-management />
            } @else if (section() === 'evaluations') {
              <!-- UC-12: Quản lý đánh giá — Admin (tiêu chí), Mentor (lập/công bố), Intern (xem) -->
              <app-evaluations />
            } @else if (section() === 'notifications') {
              <!-- UC-9: Quản lý thông báo -->
              <app-notification-management />
            } @else if (
              role() === 'INTERN' &&
              (section() === 'roadmap' || section() === 'documents' || section() === 'quizzes')
            ) {
              <!-- UC-6: Học tập và đào tạo — Intern xem lộ trình, tài liệu, làm Quiz -->
              <app-learning [view]="section()" />
            } @else {
              <section class="feature-placeholder">
                <span nz-icon [nzType]="activeIcon()"></span>
                <h1>{{ activeLabel() }}</h1>
                <p>
                  Đây là vị trí dành cho chức năng <b>{{ activeLabel() }}</b
                  >. Giao diện chi tiết và Backend sẽ được phát triển ở use case tương ứng.
                </p>
                <button (click)="choose('overview')">← Quay về tổng quan</button>
              </section>
            }
          </nz-content>
        </nz-layout>
      </nz-layout>
      <app-assistant-chat [role]="role()" />

      <!-- Notification Popover Template for Mentor/Intern -->
      <ng-template #notifPopoverTemplate>
        <div class="notif-popover">
          <div class="notif-popover__header">
            <h4>Thông báo</h4>
            @if (popoverUnreadCount() > 0) {
              <button
                nz-button
                nzType="link"
                nzSize="small"
                (click)="popoverMarkAllAsRead()"
                [nzLoading]="isMarkingAllRead()"
              >
                Đánh dấu tất cả đã đọc
              </button>
            }
          </div>
          <nz-spin [nzSpinning]="isLoadingPopoverNotifs()">
            <div class="notif-popover__body">
              @if (popoverNotifs().length === 0 && !isLoadingPopoverNotifs()) {
                <nz-empty nzNotFoundContent="Không có thông báo nào"></nz-empty>
              } @else {
                <div class="notif-popover__list">
                  @for (n of popoverNotifs(); track n.id) {
                    <div
                      class="notif-popover__item"
                      [class.notif-popover__item--unread]="!n.is_read"
                      role="button"
                      tabindex="0"
                      (click)="onPopoverItemClick(n)"
                      (keydown.enter)="onPopoverItemClick(n)"
                    >
                      <div class="notif-popover__item-title">
                        @if (!n.is_read) {
                          <span class="unread-dot"></span>
                        }
                        <b>{{ n.title }}</b>
                      </div>
                      <div class="notif-popover__item-desc">
                        {{ n.content | slice: 0 : 80 }}{{ n.content.length > 80 ? '...' : '' }}
                      </div>
                      <div class="notif-popover__item-meta">
                        {{ n.created_at | date: 'dd/MM/yyyy HH:mm' }}
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          </nz-spin>
          <div class="notif-popover__footer">
            <button nz-button nzType="link" nzBlock (click)="viewAllNotifications()">
              Xem tất cả thông báo →
            </button>
          </div>
        </div>
      </ng-template>
    </div>
  `,
})
export class DashboardShellComponent implements OnInit, OnDestroy {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly dashboardService = inject(DashboardService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly notifService = inject(NotificationService);
  protected readonly unreadCount$ = this.notifService.unreadCount$;
  private notifChangedSub?: Subscription;
  private popoverIntervalSub?: Subscription;

  protected isNotifPopoverVisible = false;
  protected readonly popoverNotifs = signal<Notification[]>([]);
  protected readonly isLoadingPopoverNotifs = signal(false);
  protected readonly isMarkingAllRead = signal(false);
  protected readonly popoverUnreadCount = computed(
    () => this.popoverNotifs().filter((n) => !n.is_read).length,
  );

  protected readonly dashboardData = signal<DashboardResponse | null>(null);
  protected readonly isLoading = signal(true);
  protected readonly hasError = signal(false);
  protected readonly dashboardError = signal('Vui lòng thử lại sau.');
  private readonly internshipService = inject(InternshipService);
  protected readonly internships = signal<Internship[]>([]);
  protected selectedInternshipId: string | null = null;

  protected onInternshipChange(id: string | null): void {
    this.selectedInternshipId = id;
    this.loadDashboard();
  }

  protected readonly metricStyles: Record<string, { tone: string; icon: string }> = {
    active_interns: { tone: 'green', icon: 'user' },
    active_mentors: { tone: 'orange', icon: 'solution' },
    ongoing_internships: { tone: 'blue', icon: 'team' },
    pending_requests: { tone: 'pink', icon: 'audit' },
    total_tasks: { tone: 'blue', icon: 'check-square' },
    published_evaluations: { tone: 'orange', icon: 'star' },
    assigned_interns: { tone: 'blue', icon: 'team' },
    cohort_tasks: { tone: 'green', icon: 'check-square' },
    assigned_tasks: { tone: 'orange', icon: 'check-square' },
    active_memberships: { tone: 'blue', icon: 'calendar' },
    unsubmitted_tasks: { tone: 'green', icon: 'check-square' },
    tasks_needing_action: { tone: 'pink', icon: 'warning' },
    completed_quizzes: { tone: 'purple', icon: 'form' },
    latest_evaluation_score: { tone: 'orange', icon: 'star' },
    pending_reviews: { tone: 'pink', icon: 'file-text' },
    draft_evaluations: { tone: 'orange', icon: 'star' },
  };
  protected readonly role = signal<Role>(Role.Admin);
  protected readonly section = signal('overview');
  protected readonly isSidebarCollapsed = signal(false);
  protected readonly dashboard = computed(() => dashboards[this.role()]);

  protected readonly currentUser = this.authService.currentUser;

  protected readonly userName = computed(() => {
    return this.currentUser()?.full_name || this.dashboard().name;
  });

  protected readonly userAvatar = computed(() => {
    return this.currentUser()?.avatar_url || null;
  });

  protected readonly userInitials = computed(() => {
    const name = this.userName();
    return (
      name
        .split(' ')
        .filter(Boolean)
        .map((w) => w[0])
        .slice(-2)
        .join('')
        .toUpperCase() || this.dashboard().initials
    );
  });

  ngOnInit(): void {
    this.authService.getProfile().subscribe({ error: () => undefined });
    this.loadDashboard();
    this.notifService.startPolling(3000);
    this.loadPopoverNotifs(false);

    this.notifChangedSub = this.notifService.notificationsChanged$.subscribe(() => {
      this.loadPopoverNotifs(false);
    });

    this.popoverIntervalSub = interval(3000).subscribe(() => {
      if (this.isNotifPopoverVisible) {
        this.loadPopoverNotifs(false);
      }
    });
  }

  ngOnDestroy(): void {
    this.notifService.stopPolling();
    this.notifChangedSub?.unsubscribe();
    this.popoverIntervalSub?.unsubscribe();
  }

  protected loadDashboard(): void {
    this.isLoading.set(true);
    this.hasError.set(false);
    this.dashboardService.getDashboard(this.selectedInternshipId || undefined).subscribe({
      next: (res) => {
        this.dashboardData.set(res);
        if (Object.values(Role).includes(res.role as Role)) {
          const role = res.role as Role;
          this.role.set(role);
          this.section.set(this.normalizeSection(role, this.section()));
          if (res.role === Role.Admin) {
            this.internshipService.getInternships().subscribe({
              next: (internships) => this.internships.set(internships),
              error: () => undefined,
            });
          }
        }
        this.isLoading.set(false);
        this.cdr.markForCheck();
      },
      error: (err: { status?: number }) => {
        this.dashboardError.set(mapDashboardError(err.status));
        this.hasError.set(true);
        this.isLoading.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  protected readonly activeLabel = computed(() =>
    this.section() === 'overview'
      ? 'Tổng quan'
      : this.section() === 'profile'
        ? 'Hồ sơ cá nhân'
        : this.section() === 'change-password'
          ? 'Đổi mật khẩu'
          : this.section() === 'logout'
            ? 'Đăng xuất'
            : (this.dashboard().nav.find((item) => item.id === this.section())?.label ??
              'Chức năng'),
  );
  protected readonly activeIcon = computed(() =>
    this.section() === 'profile'
      ? 'user'
      : this.section() === 'change-password'
        ? 'key'
        : (this.dashboard().nav.find((item) => item.id === this.section())?.icon ?? 'setting'),
  );

  constructor() {
    this.activatedRoute.paramMap.subscribe((params) => {
      const requestedRole = params.get('role')?.toUpperCase();
      if (Object.values(Role).includes(requestedRole as Role)) {
        const role = requestedRole as Role;
        this.role.set(role);
        this.section.set(this.normalizeSection(role, this.section()));
        this.notifService.refreshUnreadCount();
      }
    });
    this.activatedRoute.queryParamMap.subscribe((queryParams) => {
      const sec = queryParams.get('section') || queryParams.get('tab');
      if (sec) {
        this.section.set(this.normalizeSection(this.role(), sec));
        this.notifService.refreshUnreadCount();
      }
    });
  }

  protected choose(section: string): void {
    this.section.set(section);
    this.notifService.refreshUnreadCount();
    this.cdr.markForCheck();
  }

  protected openSection(section: string): void {
    this.choose(section);
  }

  protected toggleSidebar(): void {
    this.isSidebarCollapsed.update((collapsed) => !collapsed);
  }

  protected logout(): void {
    this.authService.logout().subscribe({
      next: () => this.finishLogout(),
      error: () => this.finishLogout(),
    });
  }

  private finishLogout(): void {
    this.notifService.clear();
    this.authService.clearSession();
    void this.router.navigate(['/login']);
  }

  protected detailsTarget(): string {
    return this.role() === Role.Intern
      ? 'roadmap'
      : this.role() === Role.Mentor
        ? 'interns'
        : 'training';
  }

  private normalizeSection(role: Role, section: string): string {
    if (section === 'settings') return 'overview';

    const removedSection =
      role === Role.Mentor ? 'learning' : role === Role.Intern ? 'internship' : 'reports';
    return section === removedSection ? 'overview' : section;
  }

  protected statusColor(status: string): string {
    if (status === 'COMPLETED') return 'success';
    if (status === 'SUBMITTED') return 'warning';
    if (status === 'REVISION_REQUIRED') return 'error';
    return 'default';
  }

  protected statusLabel(status: string): string {
    const labels: Record<string, string> = {
      TODO: 'Chưa nộp',
      SUBMITTED: 'Chờ review',
      REVISION_REQUIRED: 'Yêu cầu làm lại',
      COMPLETED: 'Hoàn thành',
      CANCELLED: 'Đã hủy',
    };
    return labels[status] ?? status;
  }

  protected readonly formatProgress = (percent: number): string => {
    return `${+(percent || 0).toFixed(2)}%`;
  };

  protected formatPercentNumber(val?: number | null): number {
    if (val == null) return 0;
    return Math.round(val * 100) / 100;
  }

  protected progressTooltip(progress: DashboardResponse['progress'] | undefined): string {
    if (!progress) return '';
    return `Đã hoàn thành ${progress.completed}/${progress.total} (${this.formatPercentNumber(progress.percent)}%)`;
  }

  protected onNotifPopoverVisibleChange(visible: boolean): void {
    this.isNotifPopoverVisible = visible;
    if (visible) {
      this.loadPopoverNotifs(true);
      this.notifService.refreshUnreadCount();
    }
  }

  protected loadPopoverNotifs(showSpinner = true): void {
    if (showSpinner && this.popoverNotifs().length === 0) {
      this.isLoadingPopoverNotifs.set(true);
    }
    this.notifService.getNotifications().subscribe({
      next: (list) => {
        this.popoverNotifs.set(list.slice(0, 8));
        const unread = list.filter((n) => !n.is_read).length;
        this.notifService.setUnreadCount(unread);
        this.isLoadingPopoverNotifs.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoadingPopoverNotifs.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  protected popoverMarkAllAsRead(): void {
    this.isMarkingAllRead.set(true);
    this.notifService.markAllAsRead().subscribe({
      next: () => {
        this.popoverNotifs.update((list) => list.map((n) => ({ ...n, is_read: true })));
        this.notifService.setUnreadCount(0);
        this.isMarkingAllRead.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isMarkingAllRead.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  protected onPopoverItemClick(n: Notification): void {
    if (!n.is_read) {
      this.notifService.markAsRead(n.id).subscribe({
        next: () => {
          this.popoverNotifs.update((list) =>
            list.map((item) => (item.id === n.id ? { ...item, is_read: true } : item)),
          );
          this.notifService.refreshUnreadCount();
          this.cdr.markForCheck();
        },
        error: () => undefined,
      });
    }
    this.isNotifPopoverVisible = false;
    this.choose('notifications');
  }

  protected viewAllNotifications(): void {
    this.isNotifPopoverVisible = false;
    this.choose('notifications');
  }
}

function mapDashboardError(status?: number): string {
  if (status === 401) return 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.';
  if (status === 403) return 'Tài khoản không có quyền xem dữ liệu này.';
  if (status !== undefined && status >= 500) return 'Máy chủ đang gặp sự cố. Vui lòng thử lại sau.';
  return 'Vui lòng thử lại sau.';
}
