import { DatePipe } from '@angular/common';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzResultModule } from 'ng-zorro-antd/result';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { FormsModule } from '@angular/forms';
import { Internship, InternshipService } from '../../core/api/internship.service';
import { DashboardService, DashboardResponse } from '../../core/api/dashboard.service';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NzAvatarModule } from 'ng-zorro-antd/avatar';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzLayoutModule } from 'ng-zorro-antd/layout';
import { NzMenuModule } from 'ng-zorro-antd/menu';
import { NzProgressModule } from 'ng-zorro-antd/progress';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { AuthService } from '../../core/api/auth.service';
import { InternshipManagementComponent } from '../internships/internship-management.component';
import { ProfileComponent } from '../profile/profile.component';
import { UserManagementComponent } from '../users/user-management.component';

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

const common: Item[] = [
  { id: 'notifications', label: 'Thông báo', icon: 'bell' },
  { id: 'change-password', label: 'Đổi mật khẩu', icon: 'key' },
];

const dashboards: Record<Role, Dashboard> = {
  [Role.Intern]: {
    roleLabel: 'Thực tập sinh',
    name: 'Nguyễn Văn An',
    initials: 'NA',
    greeting: 'Chào buổi sáng, Nguyễn Văn An!',
    description: 'Theo dõi lộ trình, task và kết quả thực tập của bạn.',
    nav: [
      { id: 'profile', label: 'Hồ sơ cá nhân', icon: 'user' },
      { id: 'roadmap', label: 'Lộ trình học tập', icon: 'read' },
      { id: 'documents', label: 'Tài liệu học tập', icon: 'file-text' },
      { id: 'quizzes', label: 'Bài kiểm tra', icon: 'form' },
      { id: 'tasks', label: 'Task của tôi', icon: 'check-square' },
      { id: 'internship', label: 'Theo dõi thực tập', icon: 'calendar' },
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
      { id: 'profile', label: 'Hồ sơ cá nhân', icon: 'user' },
      { id: 'interns', label: 'Quản lý Intern', icon: 'team' },
      { id: 'tasks', label: 'Quản lý Task', icon: 'check-square' },
      { id: 'learning', label: 'Theo dõi đào tạo', icon: 'book' },
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
      { id: 'profile', label: 'Hồ sơ cá nhân', icon: 'user' },
      { id: 'users', label: 'Quản lý người dùng', icon: 'team' },
      { id: 'internships', label: 'Quản lý thực tập', icon: 'solution' },
      { id: 'training', label: 'Quản lý đào tạo (LMS)', icon: 'book' },
      { id: 'tasks', label: 'Quản lý Task', icon: 'check-square' },
      { id: 'evaluations', label: 'Quản lý đánh giá', icon: 'star' },
      { id: 'requests', label: 'Quản lý yêu cầu', icon: 'audit' },
      { id: 'reports', label: 'Báo cáo & thống kê', icon: 'bar-chart' },
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
    NzSpinModule,
    NzResultModule,
    NzEmptyModule,
    NzSelectModule,
    FormsModule,
    NzAvatarModule,
    NzBadgeModule,
    NzButtonModule,
    NzCardModule,
    NzDrawerModule,
    NzIconModule,
    NzLayoutModule,
    NzMenuModule,
    NzProgressModule,
    NzTagModule,
    InternshipManagementComponent,
    ProfileComponent,
    UserManagementComponent,
  ],
  styles: [
    `
      :host ::ng-deep {
        nz-sider.sidebar,
        .sidebar {
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          bottom: 0 !important;
          height: 100vh !important;
          width: 250px !important;
          min-width: 250px !important;
          max-width: 250px !important;
          z-index: 100 !important;
          overflow-y: auto !important;
          overflow-x: hidden !important;
          background: #fff !important;
          border-right: 1px solid #e8edf5 !important;
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
          min-height: 100vh !important;
          width: calc(100% - 250px) !important;
          display: flex !important;
          flex-direction: column !important;
          background: #f4f7fc !important;
        }

        .topbar {
          position: sticky !important;
          top: 0 !important;
          z-index: 90 !important;
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

        @media (max-width: 760px) {
          .dashboard-main,
          nz-layout.dashboard-main {
            margin-left: 0 !important;
            width: 100% !important;
          }
        }
      }
    `,
  ],
  template: `
    <div class="dashboard-shell">
      <nz-layout>
        <nz-sider
          class="sidebar"
          [class.sidebar--open]="isMenuOpen()"
          [nzWidth]="250"
          nzTheme="light"
        >
          <div class="sidebar-brand">
            <img src="/itms-logo.png" alt="ITMS — Hệ thống quản lý thực tập sinh" />
          </div>
          <ul nz-menu nzMode="inline" class="sidebar__nav" aria-label="Chức năng">
            <li
              nz-menu-item
              role="button"
              tabindex="0"
              [nzSelected]="section() === 'overview'"
              (click)="choose('overview')"
              (keydown.enter)="choose('overview')"
            >
              <span nz-icon nzType="home"></span>Tổng quan
            </li>
            @for (item of dashboard().nav; track item.id) {
              <li
                nz-menu-item
                role="button"
                tabindex="0"
                [nzSelected]="section() === item.id"
                (click)="openSection(item.id)"
                (keydown.enter)="openSection(item.id)"
              >
                <span nz-icon [nzType]="item.icon"></span>{{ item.label }}
              </li>
            }
          </ul>
          <div class="sidebar__bottom">
            <button nz-button nzType="text" class="nav-item" (click)="choose('settings')">
              <span nz-icon nzType="setting"></span>Cài đặt</button
            ><button nz-button nzType="text" class="nav-item" (click)="logout()">
              <span nz-icon nzType="logout"></span>Đăng xuất
            </button>
          </div>
        </nz-sider>
        <nz-layout class="dashboard-main">
          <nz-header class="topbar"
            ><button nz-button nzType="text" class="menu-toggle" (click)="toggleMenu()">
              <span nz-icon nzType="menu"></span>
            </button>
            <div class="topbar__right">
              <nz-badge [nzCount]="3"
                ><button nz-button nzType="text" class="notification">
                  <span nz-icon nzType="bell"></span></button
              ></nz-badge>
              <nz-avatar
                class="avatar avatar--clickable"
                [nzSrc]="userAvatar() ?? undefined"
                [nzText]="userInitials()"
                (click)="choose('profile')"
                role="button"
                tabindex="0"
                (keydown.enter)="choose('profile')"
                title="Xem hồ sơ cá nhân"
              ></nz-avatar>
              <div
                class="user-summary user-summary--clickable"
                (click)="choose('profile')"
                role="button"
                tabindex="0"
                (keydown.enter)="choose('profile')"
                title="Xem hồ sơ cá nhân"
              >
                <strong>{{ userName() }}</strong
                ><small>{{ dashboard().roleLabel }}</small>
              </div>
            </div></nz-header
          >
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
                  nzSubTitle="Vui lòng thử lại sau."
                >
                  <div nz-result-extra>
                    <button nz-button nzType="primary" (click)="loadDashboard()">Thử lại</button>
                  </div>
                </nz-result>
              } @else {
                <section class="metric-grid">
                  @for (metric of dashboardData()?.metrics; track metric.label) {
                    <nz-card class="metric-card" [nzBordered]="false" style="text-align: center;">
                      <div class="metric-card__content" style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; width: 100%;">
                        <i
                          class="metric-icon metric-icon--{{
                            metricStyles[metric.key]?.tone || 'blue'
                          }}"
                          nz-icon
                          [nzType]="metricStyles[metric.key]?.icon || 'appstore'"
                          style="margin: 0 auto 10px auto;"
                        ></i>
                        <p class="metric-card__label" style="text-align: center; margin: 2px 0 6px 0; width: 100%;">{{ metric.label }}</p>
                        <strong class="metric-card__value" style="display: block; text-align: center; width: 100%; font-size: 28px; line-height: 1.2;">{{ metric.value }}</strong>
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
                      <button nz-button nzType="link" (click)="choose('tasks')">Xem tất cả</button>
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
                            row.status
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
                          [nzPercent]="dashboardData()?.progress?.percent"
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

                  <nz-card class="panel panel--chart" [nzBordered]="false">
                    <div class="panel__title">
                      <h2>Phân bố công việc</h2>
                      <button nz-button nzType="link" (click)="choose(analyticsTarget())">
                        Chi tiết
                      </button>
                    </div>
                    <div class="chart">
                      <ul>
                        <li>
                          <i class="dot dot--green"></i>Hoàn thành
                          <b>{{ dashboardData()?.task_breakdown?.completed }}</b>
                        </li>
                        <li>
                          <i class="dot dot--blue"></i>Đang thực hiện
                          <b>{{ dashboardData()?.task_breakdown?.in_progress }}</b>
                        </li>
                        <li>
                          <i class="dot dot--orange"></i>Chờ review
                          <b>{{ dashboardData()?.task_breakdown?.submitted }}</b>
                        </li>
                        <li>
                          <i class="dot dot--pink"></i>Quá hạn
                          <b>{{ dashboardData()?.task_breakdown?.overdue }}</b>
                        </li>
                        <li>
                          <i class="dot dot--purple"></i>Cần sửa
                          <b>{{ dashboardData()?.task_breakdown?.revision_required }}</b>
                        </li>
                        <li>
                          <i class="dot dot--gray"></i>Chưa làm
                          <b>{{ dashboardData()?.task_breakdown?.todo }}</b>
                        </li>
                      </ul>
                    </div>
                  </nz-card>
                </section>
              }
            } @else if (section() === 'profile') {
              <!-- UC-5: Hồ sơ cá nhân -->
              <app-profile />
            } @else if (section() === 'internships' && role() === 'ADMIN') {
              <app-internship-management />
            } @else if (section() === 'users' && role() === 'ADMIN') {
              <!-- UC-14: Quản lý người dùng -->
              <app-user-management />
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
      <button
        class="ai-launcher"
        type="button"
        aria-label="Mở hội thoại với Trợ lý AI"
        (click)="openAiChat()"
      >
        <img src="/chat_bot_logo.png" alt="" />
      </button>
      <nz-drawer
        nzTitle="Trợ lý AI ITMS"
        nzPlacement="right"
        [nzWidth]="360"
        [nzVisible]="isAiChatOpen()"
        (nzOnClose)="closeAiChat()"
      >
        <ng-container *nzDrawerContent>
          <div class="ai-conversation">
            <p class="ai-message">
              Xin chào! Tôi có thể hỗ trợ Roadmap, Task, deadline và tiến độ học tập của bạn.
            </p>
            <p class="ai-hint">Hãy nhập câu hỏi để bắt đầu hội thoại.</p>
            <div class="ai-composer">
              <input
                aria-label="Câu hỏi cho Trợ lý AI"
                placeholder="Nhập câu hỏi của bạn..."
              /><button nz-button nzType="primary">Gửi</button>
            </div>
          </div>
        </ng-container>
      </nz-drawer>
    </div>
  `,
})
export class DashboardShellComponent implements OnInit {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly dashboardService = inject(DashboardService);

  protected readonly dashboardData = signal<DashboardResponse | null>(null);
  protected readonly isLoading = signal(true);
  protected readonly hasError = signal(false);
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
    in_progress_tasks: { tone: 'green', icon: 'check-square' },
    tasks_needing_action: { tone: 'pink', icon: 'warning' },
    completed_quizzes: { tone: 'purple', icon: 'form' },
    latest_evaluation_score: { tone: 'orange', icon: 'star' },
    pending_reviews: { tone: 'pink', icon: 'file-text' },
    draft_evaluations: { tone: 'orange', icon: 'star' },
  };
  protected readonly role = signal<Role>(Role.Intern);
  protected readonly section = signal('overview');
  protected readonly isMenuOpen = signal(false);
  protected readonly isAiChatOpen = signal(false);
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
    // Fetch latest user profile to ensure avatar and details are up to date
    this.authService.getProfile().subscribe({ error: () => undefined });
    this.loadDashboard();

    if (this.role() === Role.Admin) {
      this.internshipService.getInternships().subscribe({
        next: (internships) => this.internships.set(internships),
        error: () => undefined,
      });
    }
  }

  protected loadDashboard(): void {
    this.isLoading.set(true);
    this.hasError.set(false);
    this.dashboardService.getDashboard(this.selectedInternshipId || undefined).subscribe({
      next: (res) => {
        this.dashboardData.set(res);
        if (Object.values(Role).includes(res.role as Role)) {
          this.role.set(res.role as Role);
        }
        this.isLoading.set(false);
      },
      error: () => {
        this.hasError.set(true);
        this.isLoading.set(false);
      },
    });
  }
  protected readonly activeLabel = computed(() =>
    this.section() === 'overview'
      ? 'Tổng quan'
      : this.section() === 'settings'
        ? 'Cài đặt'
        : this.section() === 'logout'
          ? 'Đăng xuất'
          : (this.dashboard().nav.find((item) => item.id === this.section())?.label ?? 'Chức năng'),
  );
  protected readonly activeIcon = computed(
    () => this.dashboard().nav.find((item) => item.id === this.section())?.icon ?? 'setting',
  );

  constructor() {
    this.activatedRoute.paramMap.subscribe((params) => {
      const requestedRole = params.get('role')?.toUpperCase();
      if (Object.values(Role).includes(requestedRole as Role)) {
        this.role.set(requestedRole as Role);
      }
    });
    this.activatedRoute.queryParamMap.subscribe((queryParams) => {
      const sec = queryParams.get('section') || queryParams.get('tab');
      if (sec) {
        this.section.set(sec);
      }
    });
  }

  protected choose(section: string): void {
    this.section.set(section);
    this.isMenuOpen.set(false);
  }

  protected openSection(section: string): void {
    if (section === 'change-password') {
      void this.router.navigate(['/change-password']);
      return;
    }
    this.choose(section);
  }

  protected toggleMenu(): void {
    this.isMenuOpen.update((open) => !open);
  }

  protected logout(): void {
    this.authService.logout().subscribe({
      next: () => this.finishLogout(),
      error: () => this.finishLogout(),
    });
  }

  protected openAiChat(): void {
    this.isAiChatOpen.set(true);
  }

  protected closeAiChat(): void {
    this.isAiChatOpen.set(false);
  }

  private finishLogout(): void {
    this.authService.clearSession();
    void this.router.navigate(['/login']);
  }

  protected detailsTarget(): string {
    return this.role() === Role.Intern
      ? 'roadmap'
      : this.role() === Role.Mentor
        ? 'learning'
        : 'training';
  }

  protected analyticsTarget(): string {
    return this.role() === Role.Admin ? 'reports' : 'evaluations';
  }

  protected statusColor(status: string): string {
    if (status === 'COMPLETED') return 'success';
    if (status === 'SUBMITTED' || status === 'REVISION_REQUIRED') return 'warning';
    if (status === 'TODO') return 'default';
    return 'processing';
  }
}
