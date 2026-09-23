import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ApiErrorResponse, AuthService } from '../../core/api/auth.service';

@Component({
  selector: 'app-forgot-password',
  imports: [ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="auth-page">
      <form class="auth-card" [formGroup]="form" (ngSubmit)="submit()">
        <a class="back-link" routerLink="/login">← Quay lại đăng nhập</a>
        <h1>Quên mật khẩu</h1>
        <p class="auth-card__intro">
          Nhập email đã đăng ký. Chúng tôi sẽ gửi mã OTP nếu tài khoản tồn tại.
        </p>
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
            placeholder="Nhập email của bạn"
          />
          @if (form.controls.email.touched && form.controls.email.invalid) {
            <p class="field-error">Nhập email hợp lệ.</p>
          }
        </div>
        <div class="otp-reset" [formGroup]="otpForm">
          <div class="form-group">
            <label for="otp">Mã OTP</label>
            <div class="otp-row">
              <input id="otp" autocomplete="one-time-code" formControlName="otp" maxlength="6" />
              <button class="otp-send-button" type="submit" [disabled]="isSubmitting()">
                {{ isSubmitting() ? 'Đang gửi…' : 'Gửi mã OTP' }}
              </button>
            </div>
          </div>
          <div class="form-group">
            <label for="new-password">Mật khẩu mới</label>
            <div class="input-wrapper">
              <input
                id="new-password"
                [type]="isNewPasswordVisible() ? 'text' : 'password'"
                autocomplete="new-password"
                formControlName="newPassword"
              />
              <button
                class="password-toggle"
                type="button"
                [attr.aria-label]="isNewPasswordVisible() ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
                (click)="toggleNewPasswordVisibility()"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
            </div>
          </div>
          <div class="form-group">
            <label for="confirmation">Xác nhận mật khẩu mới</label>
            <div class="input-wrapper">
              <input
                id="confirmation"
                [type]="isConfirmationVisible() ? 'text' : 'password'"
                autocomplete="new-password"
                formControlName="confirmation"
              />
              <button
                class="password-toggle"
                type="button"
                [attr.aria-label]="isConfirmationVisible() ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
                (click)="toggleConfirmationVisibility()"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
            </div>
          </div>
          <button
            class="submit-button"
            type="button"
            [disabled]="isSubmitting()"
            (click)="resetPassword()"
          >
            Đặt lại mật khẩu
          </button>
        </div>
      </form>
    </main>
  `,
})
export class ForgotPasswordComponent {
  private readonly authService = inject(AuthService);
  private readonly formBuilder = inject(FormBuilder).nonNullable;
  protected readonly form = this.formBuilder.group({
    email: ['', [Validators.required, Validators.email]],
  });
  protected readonly otpForm = this.formBuilder.group({
    otp: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
    newPassword: ['', [Validators.required, Validators.minLength(8)]],
    confirmation: ['', [Validators.required]],
  });
  protected readonly isSubmitting = signal(false);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);
  protected readonly isNewPasswordVisible = signal(false);
  protected readonly isConfirmationVisible = signal(false);

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.isSubmitting.set(true);
    this.errorMessage.set(null);
    this.authService
      .requestPasswordReset(this.form.getRawValue())
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: (response) => this.message.set(response.message),
        error: (error: unknown) => this.errorMessage.set(errorMessage(error)),
      });
  }

  protected resetPassword(): void {
    if (this.otpForm.controls.newPassword.invalid) {
      this.errorMessage.set('Mật khẩu mới cần ít nhất 8 ký tự.');
      return;
    }
    if (
      this.otpForm.controls.otp.invalid ||
      this.otpForm.value.newPassword !== this.otpForm.value.confirmation
    ) {
      this.otpForm.markAllAsTouched();
      this.errorMessage.set('Kiểm tra lại mã OTP và xác nhận mật khẩu mới.');
      return;
    }
    this.isSubmitting.set(true);
    this.authService
      .resetPassword({
        email: this.form.value.email ?? '',
        otp: this.otpForm.value.otp ?? '',
        new_password: this.otpForm.value.newPassword ?? '',
      })
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: () => this.message.set('Đặt lại mật khẩu thành công. Bạn có thể đăng nhập lại.'),
        error: (error: unknown) => this.errorMessage.set(errorMessage(error)),
      });
  }

  protected toggleNewPasswordVisibility(): void {
    this.isNewPasswordVisible.update((value) => !value);
  }

  protected toggleConfirmationVisibility(): void {
    this.isConfirmationVisible.update((value) => !value);
  }
}

function errorMessage(error: unknown): string {
  return error instanceof HttpErrorResponse
    ? ((error.error as ApiErrorResponse).error?.message ?? 'Không thể gửi yêu cầu.')
    : 'Không thể kết nối đến máy chủ.';
}
