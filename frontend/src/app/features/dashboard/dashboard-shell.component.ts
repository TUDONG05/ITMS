import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NzAvatarModule } from 'ng-zorro-antd/avatar';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzLayoutModule } from 'ng-zorro-antd/layout';
import { NzMenuModule } from 'ng-zorro-antd/menu';
import { NzProgressModule } from 'ng-zorro-antd/progress';
import { NzTagModule } from 'ng-zorro-antd/tag';

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
  roleLabel: string; name: string; initials: string; greeting: string; description: string;
  nav: Item[]; metrics: { label: string; value: string; note: string; tone: string }[];
}

const common: Item[] = [
  { id: 'notifications', label: 'Thông báo', icon: '♧' },
  { id: 'ai', label: 'Trợ lý AI', icon: '✦' },
  { id: 'change-password', label: 'Đổi mật khẩu', icon: '◌' },
];

const dashboards: Record<Role, Dashboard> = {
  [Role.Intern]: {
    roleLabel: 'Thực tập sinh', name: 'Nguyễn Văn An', initials: 'NA',
    greeting: 'Chào buổi sáng, Nguyễn Văn An!', description: 'Theo dõi lộ trình, task và kết quả thực tập của bạn.',
    nav: [
      { id: 'profile', label: 'Hồ sơ cá nhân', icon: '◉' }, { id: 'roadmap', label: 'Lộ trình học tập', icon: '▤' },
      { id: 'documents', label: 'Tài liệu học tập', icon: '▱' }, { id: 'quizzes', label: 'Bài kiểm tra', icon: '☑' },
      { id: 'tasks', label: 'Task của tôi', icon: '▣' }, { id: 'internship', label: 'Theo dõi thực tập', icon: '▥' },
      { id: 'evaluations', label: 'Đánh giá', icon: '★' }, ...common,
    ],
    metrics: [
      { label: 'Tiến độ học tập', value: '75%', note: '9/12 nội dung hoàn thành', tone: 'green' },
      { label: 'Bài kiểm tra', value: '4/6', note: 'Đã hoàn thành', tone: 'purple' },
      { label: 'Task được giao', value: '7', note: '5 đang thực hiện', tone: 'orange' },
      { label: 'Đánh giá hiện tại', value: '8.5/10', note: 'Điểm trung bình', tone: 'pink' },
    ],
  },
  [Role.Mentor]: {
    roleLabel: 'Mentor', name: 'Lê Minh Hoàng', initials: 'LH',
    greeting: 'Xin chào, Lê Minh Hoàng!', description: 'Đồng hành và phát triển các thực tập sinh phụ trách.',
    nav: [
      { id: 'interns', label: 'Quản lý Intern', icon: '◉' }, { id: 'tasks', label: 'Quản lý Task', icon: '▣' },
      { id: 'learning', label: 'Theo dõi đào tạo', icon: '▤' }, { id: 'evaluations', label: 'Đánh giá', icon: '★' },
      { id: 'internship-status', label: 'Trạng thái thực tập', icon: '▥' }, ...common,
    ],
    metrics: [
      { label: 'Intern phụ trách', value: '8', note: '6 đang thực tập', tone: 'blue' },
      { label: 'Task đang thực hiện', value: '24', note: '3 task mới tuần này', tone: 'green' },
      { label: 'Bài nộp chờ review', value: '7', note: 'Cần phản hồi', tone: 'pink' },
      { label: 'Đánh giá sắp hạn', value: '5', note: 'Trong 7 ngày tới', tone: 'orange' },
    ],
  },
  [Role.Admin]: {
    roleLabel: 'Quản trị viên', name: 'Administrator', initials: 'AD',
    greeting: 'Xin chào, Administrator!', description: 'Tổng quan vận hành hệ thống quản lý thực tập sinh.',
    nav: [
      { id: 'users', label: 'Quản lý người dùng', icon: '◉' }, { id: 'internships', label: 'Quản lý thực tập', icon: '▥' },
      { id: 'training', label: 'Quản lý đào tạo (LMS)', icon: '▤' }, { id: 'tasks', label: 'Quản lý Task', icon: '▣' },
      { id: 'evaluations', label: 'Quản lý đánh giá', icon: '★' }, { id: 'requests', label: 'Quản lý yêu cầu', icon: '☑' },
      { id: 'reports', label: 'Báo cáo & thống kê', icon: '▥' }, ...common,
    ],
    metrics: [
      { label: 'Tổng người dùng', value: '156', note: 'Tăng 12% so với tháng trước', tone: 'blue' },
      { label: 'Tổng thực tập sinh', value: '48', note: 'Đang hoạt động', tone: 'green' },
      { label: 'Tổng Mentor', value: '12', note: 'Đang phụ trách Intern', tone: 'orange' },
      { label: 'Yêu cầu chờ duyệt', value: '5', note: 'Gia hạn, dừng, kết thúc', tone: 'pink' },
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
    NzLayoutModule,
    NzMenuModule,
    NzProgressModule,
    NzTagModule,
  ],
  template: `
    <div class="dashboard-shell">
      <nz-layout>
      <nz-sider class="sidebar" [class.sidebar--open]="isMenuOpen()" [nzWidth]="250" nzTheme="light">
        <div class="brand"><span class="brand__mark">◆</span><span>ITMS<small>Internship Training<br>Management System</small></span></div>
        <ul nz-menu nzMode="inline" class="sidebar__nav" aria-label="Chức năng">
          <li nz-menu-item role="button" tabindex="0" [nzSelected]="section() === 'overview'" (click)="choose('overview')" (keydown.enter)="choose('overview')"><span>⌂</span>Tổng quan</li>
          @for (item of dashboard().nav; track item.id) { <li nz-menu-item role="button" tabindex="0" [nzSelected]="section() === item.id" (click)="choose(item.id)" (keydown.enter)="choose(item.id)"><span>{{ item.icon }}</span>{{ item.label }}</li> }
        </ul>
        <div class="sidebar__bottom"><button nz-button nzType="text" class="nav-item" (click)="choose('settings')"><span>⚙</span>Cài đặt</button><button nz-button nzType="text" class="nav-item" (click)="choose('logout')"><span>⇥</span>Đăng xuất</button></div>
      </nz-sider>
      <nz-layout class="dashboard-main">
        <nz-header class="topbar"><button nz-button nzType="text" class="menu-toggle" (click)="toggleMenu()">☰</button><div class="topbar__right"><nz-badge [nzCount]="3"><button nz-button nzType="text" class="notification">♧</button></nz-badge><nz-avatar class="avatar" [nzText]="dashboard().initials"></nz-avatar><div><strong>{{ dashboard().name }}</strong><small>{{ dashboard().roleLabel }}</small></div></div></nz-header>
        <nz-content class="content">
          <div class="breadcrumb">⌂ <span>/</span> {{ activeLabel() }}</div>
          <div class="role-preview">@for (candidate of roles; track candidate) { <button [class.role-preview__active]="candidate === role()" (click)="switchRole(candidate)">{{ dashboards[candidate].roleLabel }}</button> }</div>
          @if (section() === 'overview') {
            <section class="hero"><div><p>ITMS · {{ dashboard().roleLabel }}</p><h1>{{ dashboard().greeting }}</h1><h3>{{ dashboard().description }}</h3><span>“Cùng học hỏi hôm nay, tạo nên cơ hội ngày mai.”</span></div><div class="hero__art"><b>✓</b><b>▤</b><b>✦</b></div></section>
            <section class="metric-grid">@for (metric of dashboard().metrics; track metric.label) { <nz-card class="metric-card" [nzBordered]="false"><i class="metric-icon metric-icon--{{ metric.tone }}">◈</i><div><p>{{ metric.label }}</p><strong>{{ metric.value }}</strong><small>{{ metric.note }}</small></div></nz-card> }</section>
            <section class="dashboard-grid">
              <nz-card class="panel panel--wide" [nzBordered]="false"><div class="panel__title"><h2>{{ dashboard().roleLabel === 'Mentor' ? 'Danh sách Intern của tôi' : dashboard().roleLabel === 'Quản trị viên' ? 'Đợt thực tập gần đây' : 'Task gần đây' }}</h2><button nz-button nzType="link" (click)="choose('tasks')">Xem tất cả</button></div><div class="table-head"><span>Tên / thông tin</span><span>Tiến độ</span><span>Trạng thái</span></div>@for (row of rows; track row.name) { <div class="table-row"><span><b>{{ row.name }}</b><small>{{ row.sub }}</small></span><span class="progress"><nz-progress [nzPercent]="row.progress" nzSize="small" [nzShowInfo]="false"></nz-progress>{{ row.progress }}%</span><nz-tag nzColor="green" class="tag">{{ row.status }}</nz-tag></div> }</nz-card>
              <nz-card class="panel" [nzBordered]="false"><div class="panel__title"><h2>Lộ trình & tiến độ</h2><button nz-button nzType="link" (click)="choose(detailsTarget())">Xem chi tiết</button></div><ol class="timeline"><li><b>Phase 1: Kiến thức nền tảng</b><small>Hoàn thành 100%</small></li><li><b>Phase 2: Kỹ năng chuyên môn</b><small>Đang học 60%</small></li><li><b>Phase 3: Dự án thực hành</b><small>Chưa bắt đầu</small></li></ol></nz-card>
              <nz-card class="panel" [nzBordered]="false"><div class="panel__title"><h2>Thông báo mới</h2><button nz-button nzType="link" (click)="choose('notifications')">Xem tất cả</button></div><ul class="notice-list"><li>● <span><b>Cập nhật kế hoạch tuần này</b><small>2 giờ trước</small></span></li><li>● <span><b>Có task cần xử lý</b><small>5 giờ trước</small></span></li><li>● <span><b>Tài liệu đào tạo mới</b><small>Hôm qua</small></span></li></ul></nz-card>
              <nz-card class="panel panel--chart" [nzBordered]="false"><div class="panel__title"><h2>Phân bố công việc</h2><button nz-button nzType="link" (click)="choose(analyticsTarget())">Chi tiết</button></div><div class="chart"><div class="chart__donut"><b>24</b><small>Tổng task</small></div><ul><li><i class="dot dot--green"></i>Hoàn thành <b>10</b></li><li><i class="dot dot--blue"></i>Đang thực hiện <b>8</b></li><li><i class="dot dot--orange"></i>Chờ review <b>4</b></li><li><i class="dot dot--pink"></i>Quá hạn <b>2</b></li></ul></div></nz-card>
            </section>
          } @else { <section class="feature-placeholder"><span>{{ activeIcon() }}</span><h1>{{ activeLabel() }}</h1><p>Đây là vị trí dành cho chức năng <b>{{ activeLabel() }}</b>. Giao diện chi tiết và Backend sẽ được phát triển ở use case tương ứng.</p><button (click)="choose('overview')">← Quay về tổng quan</button></section> }
        </nz-content>
      </nz-layout>
      </nz-layout>
    </div>
  `,
})
export class DashboardShellComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  protected readonly roles: Role[] = [Role.Intern, Role.Mentor, Role.Admin];
  protected readonly dashboards = dashboards;
  protected readonly role = signal<Role>(Role.Intern);
  protected readonly section = signal('overview');
  protected readonly isMenuOpen = signal(false);
  protected readonly dashboard = computed(() => dashboards[this.role()]);
  protected readonly rows = [
    { name: 'Viết báo cáo phân tích yêu cầu', sub: 'Hạn: 28/08/2026', progress: 65, status: 'Đang thực hiện' },
    { name: 'Thiết kế database mẫu', sub: 'Hạn: 30/08/2026', progress: 40, status: 'Chờ review' },
    { name: 'Xây dựng giao diện đăng nhập', sub: 'Hạn: 05/09/2026', progress: 100, status: 'Hoàn thành' },
  ];
  protected readonly activeLabel = computed(() => this.section() === 'overview' ? 'Tổng quan' : this.section() === 'settings' ? 'Cài đặt' : this.section() === 'logout' ? 'Đăng xuất' : this.dashboard().nav.find((item) => item.id === this.section())?.label ?? 'Chức năng');
  protected readonly activeIcon = computed(() => this.dashboard().nav.find((item) => item.id === this.section())?.icon ?? '⚙');
  constructor() {
    this.activatedRoute.paramMap.subscribe((params) => {
      const requestedRole = params.get('role')?.toUpperCase();
      if (Object.values(Role).includes(requestedRole as Role)) {
        this.role.set(requestedRole as Role);
      }
    });
  }
  protected switchRole(role: Role): void { this.role.set(role); this.section.set('overview'); this.isMenuOpen.set(false); }
  protected choose(section: string): void { this.section.set(section); this.isMenuOpen.set(false); }
  protected toggleMenu(): void { this.isMenuOpen.update((open) => !open); }
  protected detailsTarget(): string { return this.role() === Role.Intern ? 'roadmap' : this.role() === Role.Mentor ? 'learning' : 'training'; }
  protected analyticsTarget(): string { return this.role() === Role.Admin ? 'reports' : 'evaluations'; }
}
