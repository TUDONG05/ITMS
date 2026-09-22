import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

const DASHBOARDS: Record<string, { title: string; description: string }> = {
  admin: { title: 'Dashboard Quản trị', description: 'Quản lý tài khoản, đợt thực tập và cấu hình hệ thống.' },
  mentor: { title: 'Dashboard Mentor', description: 'Theo dõi Intern, Task, tiến độ và đánh giá.' },
  intern: { title: 'Dashboard Thực tập sinh', description: 'Theo dõi lộ trình, Task, bài kiểm tra và kết quả.' },
};

@Component({
  selector: 'app-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="dashboard-page">
      <section class="dashboard-card">
        <span class="dashboard-card__eyebrow">ITMS</span>
        <h1>{{ dashboard().title }}</h1>
        <p>{{ dashboard().description }}</p>
        <button type="button" (click)="logout()">Đăng xuất</button>
      </section>
    </main>
  `,
})
export class DashboardComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  protected readonly dashboard = computed(
    () => DASHBOARDS[this.route.snapshot.paramMap.get('role') ?? ''] ?? DASHBOARDS['intern'],
  );

  protected logout(): void {
    sessionStorage.clear();
    void this.router.navigate(['/login']);
  }
}
