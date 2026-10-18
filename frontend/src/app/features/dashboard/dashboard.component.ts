import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/api/auth.service';

const DASHBOARDS: Record<string, { title: string; description: string }> = {
  admin: {
    title: 'Dashboard Quản trị',
    description: 'Quản lý tài khoản, đợt thực tập và cấu hình hệ thống.',
  },
  mentor: { title: 'Dashboard Mentor', description: 'Theo dõi Intern, Task, tiến độ và đánh giá.' },
  intern: {
    title: 'Dashboard Thực tập sinh',
    description: 'Theo dõi lộ trình, Task, bài kiểm tra và kết quả.',
  },
};

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="dashboard-page">
      <section class="dashboard-card">
        <span class="dashboard-card__eyebrow">ITMS</span>
        <h1>{{ dashboard().title }}</h1>
        <p>{{ dashboard().description }}</p>
        <div class="dashboard-card__actions">
          <a routerLink="/change-password">Đổi mật khẩu</a>
          <button type="button" (click)="logout()" [disabled]="isLoggingOut()">
            {{ isLoggingOut() ? 'Đang đăng xuất…' : 'Đăng xuất' }}
          </button>
        </div>
      </section>
    </main>
  `,
})
export class DashboardComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  protected readonly isLoggingOut = signal(false);
  protected readonly dashboard = computed(
    () => DASHBOARDS[this.route.snapshot.paramMap.get('role') ?? ''] ?? DASHBOARDS['intern'],
  );

  protected logout(): void {
    this.isLoggingOut.set(true);
    this.authService
      .logout()
      .pipe(finalize(() => this.isLoggingOut.set(false)))
      .subscribe({ next: () => this.finishLogout(), error: () => this.finishLogout() });
  }

  private finishLogout(): void {
    this.authService.clearSession();
    void this.router.navigate(['/login']);
  }
}
