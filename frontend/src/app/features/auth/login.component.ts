import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';

import { ApiErrorResponse, AuthenticatedUser, AuthService } from '../../core/api/auth.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="login-page">
      <section class="company-panel" aria-label="Trụ sở công ty">
        <img src="cong_ty.png" alt="Trụ sở công ty" />
      </section>

      <section class="login-panel" aria-labelledby="login-heading">
        <form class="login-card" [formGroup]="form" (ngSubmit)="submit()">
          <div class="brand" aria-label="ITMS">
            <span class="brand__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                <path d="M6 12v5c3 3 9 3 12 0v-5" />
              </svg>
            </span>
            <span>ITMS</span>
          </div>

          <h1 id="login-heading">Đăng nhập</h1>

          @if (authenticatedUser(); as user) {
            <div class="notice notice--success" role="status">
              Đăng nhập thành công. Xin chào {{ user.full_name }} ({{ user.role }}).
            </div>
          }

          @if (errorMessage(); as error) {
            <div class="notice notice--error" role="alert">{{ error }}</div>
          }

          <div class="form-group">
            <label for="email">Email</label>
            <div class="input-wrapper">
              <svg
                class="input-icon"
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <rect width="20" height="16" x="2" y="4" rx="2" />
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L1 7" />
              </svg>
              <input
                id="email"
                type="email"
                formControlName="email"
                autocomplete="email"
                placeholder="Nhập email của bạn"
              />
            </div>
            @if (form.controls.email.touched && form.controls.email.invalid) {
              <p class="field-error">Nhập email hợp lệ.</p>
            }
          </div>

          <div class="form-group">
            <label for="password">Mật khẩu</label>
            <div class="input-wrapper">
              <svg
                class="input-icon"
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <input
                id="password"
                [type]="isPasswordVisible() ? 'text' : 'password'"
                formControlName="password"
                autocomplete="current-password"
                placeholder="Nhập mật khẩu"
              />
              <button
                class="password-toggle"
                type="button"
                [attr.aria-label]="isPasswordVisible() ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
                (click)="togglePasswordVisibility()"
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
            @if (form.controls.password.touched && form.controls.password.invalid) {
              <p class="field-error">Nhập mật khẩu.</p>
            }
          </div>

          <div class="form-options">
            <label class="remember-me" for="remember-me">
              <input id="remember-me" type="checkbox" formControlName="rememberMe" />
              <span>Ghi nhớ đăng nhập</span>
            </label>
            <a routerLink="/forgot-password">Quên mật khẩu?</a>
          </div>

          <button class="submit-button" type="submit" [disabled]="isSubmitting()">
            {{ isSubmitting() ? 'Đang đăng nhập…' : 'Đăng nhập' }}
          </button>
        </form>
      </section>
    </main>
  `,
})
export class LoginComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly formBuilder = inject(FormBuilder).nonNullable;

  protected readonly form = this.formBuilder.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
    rememberMe: [false],
  });
  protected readonly authenticatedUser = signal<AuthenticatedUser | null>(null);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly isPasswordVisible = signal(false);
  protected readonly isSubmitting = signal(false);

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const { email, password } = this.form.getRawValue();
    this.errorMessage.set(null);
    this.authenticatedUser.set(null);
    this.isSubmitting.set(true);

    this.authService
      .login({ email, password })
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: (response) => {
          this.authService.storeSession(response);
          this.authenticatedUser.set(response.user);
          void this.router.navigate(['/dashboard', response.user.role.toLowerCase()]);
        },
        error: (error: unknown) => this.errorMessage.set(getErrorMessage(error)),
      });
  }

  protected togglePasswordVisibility(): void {
    this.isPasswordVisible.update((visible) => !visible);
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    const apiError = error.error as ApiErrorResponse;
    return apiError.error?.message ?? 'Không thể đăng nhập. Vui lòng thử lại.';
  }
  return 'Không thể kết nối đến máy chủ. Vui lòng thử lại.';
}
