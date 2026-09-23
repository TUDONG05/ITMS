import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ApiErrorResponse, AuthService } from '../../core/api/auth.service';

@Component({
  selector: 'app-change-password',
  imports: [ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="auth-page">
      <form class="auth-card" [formGroup]="form" (ngSubmit)="submit()">
        <a class="back-link" [routerLink]="dashboardLink">← Quay lại dashboard</a>
        <h1>Đổi mật khẩu</h1>
        <p class="auth-card__intro">Đặt mật khẩu mới để bảo vệ tài khoản ITMS của bạn.</p>

        @if (message(); as message) {
          <p class="notice notice--success" role="status">{{ message }}</p>
        }
        @if (errorMessage(); as error) {
          <p class="notice notice--error" role="alert">{{ error }}</p>
        }

        <div class="form-group">
          <label for="current-password">Mật khẩu hiện tại</label>
          <input
            id="current-password"
            type="password"
            autocomplete="current-password"
            formControlName="currentPassword"
          />
        </div>
        <div class="form-group">
          <label for="new-password">Mật khẩu mới</label>
          <input
            id="new-password"
            type="password"
            autocomplete="new-password"
            formControlName="newPassword"
          />
          @if (form.controls.newPassword.touched && form.controls.newPassword.invalid) {
            <p class="field-error">Mật khẩu mới cần ít nhất 8 ký tự.</p>
          }
        </div>
        <div class="form-group">
          <label for="confirm-password">Xác nhận mật khẩu mới</label>
          <input
            id="confirm-password"
            type="password"
            autocomplete="new-password"
            formControlName="confirmation"
          />
          @if (
            form.controls.confirmation.touched &&
            form.controls.confirmation.value !== form.controls.newPassword.value
          ) {
            <p class="field-error">Mật khẩu xác nhận chưa khớp.</p>
          }
        </div>
        <button class="submit-button" type="submit" [disabled]="isSubmitting()">
          {{ isSubmitting() ? 'Đang cập nhật…' : 'Cập nhật mật khẩu' }}
        </button>
      </form>
    </main>
  `,
})
export class ChangePasswordComponent {
  private readonly authService = inject(AuthService);
  private readonly formBuilder = inject(FormBuilder).nonNullable;
  private readonly router = inject(Router);

  protected readonly form = this.formBuilder.group({
    currentPassword: ['', Validators.required],
    newPassword: ['', [Validators.required, Validators.minLength(8)]],
    confirmation: ['', Validators.required],
  });
  protected readonly isSubmitting = signal(false);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly dashboardLink = dashboardLinkForCurrentUser();

  protected submit(): void {
    if (
      this.form.invalid ||
      this.form.controls.confirmation.value !== this.form.controls.newPassword.value
    ) {
      this.form.markAllAsTouched();
      return;
    }
    const { currentPassword, newPassword } = this.form.getRawValue();
    this.errorMessage.set(null);
    this.message.set(null);
    this.isSubmitting.set(true);
    this.authService
      .changePassword({ current_password: currentPassword, new_password: newPassword })
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: () => {
          this.authService.clearSession();
          this.message.set('Đổi mật khẩu thành công. Vui lòng đăng nhập lại.');
          setTimeout(() => void this.router.navigate(['/login']), 1000);
        },
        error: (error: unknown) =>
          this.errorMessage.set(errorMessage(error, 'Không thể đổi mật khẩu.')),
      });
  }
}

function dashboardLinkForCurrentUser(): string[] {
  try {
    const role = (
      JSON.parse(sessionStorage.getItem('itms_authenticated_user') ?? '{}') as { role?: string }
    ).role?.toLowerCase();
    return role && ['intern', 'mentor', 'admin'].includes(role) ? ['/dashboard', role] : ['/login'];
  } catch {
    return ['/login'];
  }
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof HttpErrorResponse) {
    return (error.error as ApiErrorResponse).error?.message ?? fallback;
  }
  return fallback;
}
