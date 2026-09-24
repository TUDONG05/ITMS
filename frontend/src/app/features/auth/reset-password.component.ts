import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ApiErrorResponse, AuthService } from '../../core/api/auth.service';

@Component({
  selector: 'app-reset-password',
  imports: [ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="auth-page">
      <form class="auth-card" [formGroup]="form" (ngSubmit)="submit()">
        <a class="back-link" routerLink="/login">← Quay lại đăng nhập</a>
        <h1>Đặt lại mật khẩu</h1>
        <p class="auth-card__intro">Tạo mật khẩu mới cho tài khoản của bạn.</p>
        @if (message(); as message) {
          <p class="notice notice--success" role="status">{{ message }}</p>
        }
        @if (errorMessage(); as error) {
          <p class="notice notice--error" role="alert">{{ error }}</p>
        }
        <div class="form-group">
          <label for="reset-email">Email</label>
          <input
            id="reset-email"
            type="email"
            autocomplete="email"
            formControlName="email"
          />
        </div>
        <div class="form-group">
          <label for="reset-otp">Mã OTP</label>
          <input id="reset-otp" inputmode="numeric" autocomplete="one-time-code" formControlName="otp" />
        </div>
        <div class="form-group">
          <label for="reset-new-password">Mật khẩu mới</label>
          <input
            id="reset-new-password"
            type="password"
            autocomplete="new-password"
            formControlName="newPassword"
          />
          @if (form.controls.newPassword.touched && form.controls.newPassword.invalid) {
            <p class="field-error">Mật khẩu cần ít nhất 8 ký tự.</p>
          }
        </div>
        <div class="form-group">
          <label for="reset-confirmation">Xác nhận mật khẩu mới</label>
          <input
            id="reset-confirmation"
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
          {{ isSubmitting() ? 'Đang đặt lại…' : 'Đặt lại mật khẩu' }}
        </button>
      </form>
    </main>
  `,
})
export class ResetPasswordComponent {
  private readonly authService = inject(AuthService);
  private readonly formBuilder = inject(FormBuilder).nonNullable;
  private readonly router = inject(Router);
  protected readonly form = this.formBuilder.group({
    email: ['', [Validators.required, Validators.email]],
    otp: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
    newPassword: ['', [Validators.required, Validators.minLength(8)]],
    confirmation: ['', Validators.required],
  });
  protected readonly isSubmitting = signal(false);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);

  protected submit(): void {
    if (
      this.form.invalid ||
      this.form.controls.confirmation.value !== this.form.controls.newPassword.value
    ) {
      this.form.markAllAsTouched();
      return;
    }
    const { email, otp, newPassword } = this.form.getRawValue();
    this.isSubmitting.set(true);
    this.errorMessage.set(null);
    this.authService
      .resetPassword({ email, otp, new_password: newPassword })
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: () => {
          this.message.set('Đặt lại mật khẩu thành công. Bạn có thể đăng nhập lại.');
          setTimeout(() => void this.router.navigate(['/login']), 1000);
        },
        error: (error: unknown) => this.errorMessage.set(errorMessage(error)),
      });
  }
}

function errorMessage(error: unknown): string {
  return error instanceof HttpErrorResponse
    ? ((error.error as ApiErrorResponse).error?.message ??
        'Mã OTP không hợp lệ hoặc đã hết hạn.')
    : 'Không thể kết nối đến máy chủ.';
}
