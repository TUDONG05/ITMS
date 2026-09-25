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
import { ProfileComponent } from '../profile/profile.component';

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
    ProfileComponent,
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
              <section class="metric-grid">
                @for (metric of dashboard().metrics; track metric.label) {
                  <nz-card class="metric-card" [nzBordered]="false"
                    ><i
                      class="metric-icon metric-icon--{{ metric.tone }}"
                      nz-icon
                      [nzType]="metric.icon"
                    ></i>
                    <div>
                      <p>{{ metric.label }}</p>
                      <strong>{{ metric.value }}</strong
                      ><small>{{ metric.note }}</small>
                    </div></nz-card
                  >
                }
              </section>
              <section class="dashboard-grid">
                <nz-card class="panel panel--wide" [nzBordered]="false"
                  ><div class="panel__title">
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
                  <div class="table-head">
                    <span>Tên / thông tin</span><span>Tiến độ</span><span>Trạng thái</span>
                  </div>
                  @for (row of rows; track row.name) {
                    <div class="table-row">
                      <span
                        ><b>{{ row.name }}</b
                        ><small>{{ row.sub }}</small></span
                      ><span class="progress"
                        ><nz-progress
                          [nzPercent]="row.progress"
                          nzSize="small"
                          [nzShowInfo]="false"
                        ></nz-progress
                        >{{ row.progress }}%</span
                      ><nz-tag [nzColor]="statusColor(row.status)" class="tag">{{
                        row.status
                      }}</nz-tag>
                    </div>
                  }
                </nz-card>
                <nz-card class="panel" [nzBordered]="false"
                  ><div class="panel__title">
                    <h2>Lộ trình & tiến độ</h2>
                    <button nz-button nzType="link" (click)="choose(detailsTarget())">
                      Xem chi tiết
                    </button>
                  </div>
                  <ol class="timeline">
                    <li><b>Phase 1: Kiến thức nền tảng</b><small>Hoàn thành 100%</small></li>
                    <li><b>Phase 2: Kỹ năng chuyên môn</b><small>Đang học 60%</small></li>
                    <li><b>Phase 3: Dự án thực hành</b><small>Chưa bắt đầu</small></li>
                  </ol></nz-card
                >
                <nz-card class="panel" [nzBordered]="false"
                  ><div class="panel__title">
                    <h2>Thông báo mới</h2>
                    <button nz-button nzType="link" (click)="choose('notifications')">
                      Xem tất cả
                    </button>
                  </div>
                  <ul class="notice-list">
                    <li>
                      ● <span><b>Cập nhật kế hoạch tuần này</b><small>2 giờ trước</small></span>
                    </li>
                    <li>
                      ● <span><b>Có task cần xử lý</b><small>5 giờ trước</small></span>
                    </li>
                    <li>
                      ● <span><b>Tài liệu đào tạo mới</b><small>Hôm qua</small></span>
                    </li>
                  </ul></nz-card
                >
                <nz-card class="panel panel--chart" [nzBordered]="false"
                  ><div class="panel__title">
                    <h2>Phân bố công việc</h2>
                    <button nz-button nzType="link" (click)="choose(analyticsTarget())">
                      Chi tiết
                    </button>
                  </div>
                  <div class="chart">
                    <div class="chart__donut"><b>24</b><small>Tổng task</small></div>
                    <ul>
                      <li><i class="dot dot--green"></i>Hoàn thành <b>10</b></li>
                      <li><i class="dot dot--blue"></i>Đang thực hiện <b>8</b></li>
                      <li><i class="dot dot--orange"></i>Chờ review <b>4</b></li>
                      <li><i class="dot dot--pink"></i>Quá hạn <b>2</b></li>
                    </ul>
                  </div></nz-card
                >
              </section>
            } @else if (section() === 'profile') {
              <!-- UC-5: Hồ sơ cá nhân -->
              <app-profile />
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
    this.authService.getProfile().subscribe({ error: () => {} });
  }
  protected readonly rows = [
    {
      name: 'Viết báo cáo phân tích yêu cầu',
      sub: 'Hạn: 28/08/2026',
      progress: 65,
      status: 'Đang thực hiện',
    },
    { name: 'Thiết kế database mẫu', sub: 'Hạn: 30/08/2026', progress: 40, status: 'Chờ review' },
    {
      name: 'Xây dựng giao diện đăng nhập',
      sub: 'Hạn: 05/09/2026',
      progress: 100,
      status: 'Hoàn thành',
    },
  ];
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
    return status === 'Hoàn thành' ? 'success' : status === 'Chờ review' ? 'warning' : 'processing';
  }
}
