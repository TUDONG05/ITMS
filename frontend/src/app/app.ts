import { Component, inject, signal } from '@angular/core';
import { BackendHealth, BackendHealthService } from './core/api/backend-health.service';

@Component({
  selector: 'app-root',
  template: `
    <main>
      <p class="eyebrow">ITMS · Sprint 0</p>
      <h1>Internship Management System</h1>
      <p class="description">Bộ khung Angular đã sẵn sàng kết nối với Backend API.</p>
      @if (health(); as health) {
        <p class="status status--ok">{{ health.service }}: {{ health.status }}</p>
      } @else if (isUnavailable()) {
        <p class="status status--error">
          Không kết nối được Backend. Hãy chạy FastAPI tại cổng 8000.
        </p>
      } @else {
        <p class="status">Đang kiểm tra Backend…</p>
      }
    </main>
  `,
})
export class App {
  private readonly backendHealth = inject(BackendHealthService);

  protected readonly health = signal<BackendHealth | null>(null);
  protected readonly isUnavailable = signal(false);

  constructor() {
    this.backendHealth.getStatus().subscribe({
      next: (health) => this.health.set(health),
      error: () => this.isUnavailable.set(true),
    });
  }
}
