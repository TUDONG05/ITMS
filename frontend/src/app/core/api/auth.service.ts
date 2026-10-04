import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { catchError, finalize, firstValueFrom, Observable, of, shareReplay, tap } from 'rxjs';

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  avatar_url?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: AuthenticatedUser;
}

export interface ApiErrorResponse {
  error?: {
    code: string;
    message: string;
  };
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  email: string;
  otp: string;
  new_password: string;
}

export interface MessageResponse {
  message: string;
}

// UC-5 – Profile types
export interface MentorSummary {
  id: string;
  full_name: string;
  email: string;
}

export interface InternProfileRead {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  avatar_url: string | null;
  role: string;
  status: string;
  created_at: string;
  mentor: MentorSummary | null;
}

export interface UpdateProfileRequest {
  full_name?: string | null;
  phone: string | null;
  avatar_url: string | null;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  private readonly accessTokenSignal = signal<string | null>(null);
  readonly accessToken = this.accessTokenSignal.asReadonly();
  readonly currentUser = signal<AuthenticatedUser | null>(null);

  private refreshInFlight$: Observable<LoginResponse> | null = null;

  login(payload: LoginRequest) {
    return this.http
      .post<LoginResponse>('/api/v1/auth/login', payload, { withCredentials: true })
      .pipe(tap((res) => this.storeSession(res)));
  }

  initialize(): Promise<void> {
    return firstValueFrom(
      this.refreshSession().pipe(
        catchError(() => {
          this.clearSession();
          return of(null);
        }),
      ),
    ).then(() => undefined);
  }

  refreshSession(): Observable<LoginResponse> {
    if (!this.refreshInFlight$) {
      this.refreshInFlight$ = this.http
        .post<LoginResponse>('/api/v1/auth/refresh', {}, { withCredentials: true })
        .pipe(
          tap((res) => this.storeSession(res)),
          shareReplay(1),
          finalize(() => {
            this.refreshInFlight$ = null;
          }),
        );
    }
    return this.refreshInFlight$;
  }

  changePassword(payload: ChangePasswordRequest) {
    return this.http.post<MessageResponse>('/api/v1/auth/change-password', payload, {
      withCredentials: true,
    });
  }

  requestPasswordReset(payload: ForgotPasswordRequest) {
    return this.http.post<MessageResponse>('/api/v1/auth/forgot-password', payload);
  }

  resetPassword(payload: ResetPasswordRequest) {
    return this.http.post<MessageResponse>('/api/v1/auth/reset-password', payload);
  }

  logout() {
    return this.http
      .post<MessageResponse>('/api/v1/auth/logout', {}, { withCredentials: true })
      .pipe(tap(() => this.clearSession()));
  }

  // UC-5 – Profile
  getProfile() {
    return this.http
      .get<InternProfileRead>('/api/v1/profile', { withCredentials: true })
      .pipe(tap((profile) => this.syncWithProfile(profile)));
  }

  updateProfile(payload: UpdateProfileRequest) {
    return this.http
      .patch<InternProfileRead>('/api/v1/profile', payload, { withCredentials: true })
      .pipe(tap((profile) => this.syncWithProfile(profile)));
  }

  uploadAvatar(file: File) {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.http
      .post<InternProfileRead>('/api/v1/profile/avatar', form, { withCredentials: true })
      .pipe(tap((profile) => this.syncWithProfile(profile)));
  }

  storeSession(response: LoginResponse): void {
    this.accessTokenSignal.set(response.access_token);
    this.currentUser.set(response.user);
  }

  clearSession(): void {
    this.accessTokenSignal.set(null);
    this.currentUser.set(null);
  }

  syncWithProfile(profile: InternProfileRead): void {
    const updated: AuthenticatedUser = {
      id: profile.id,
      email: profile.email,
      full_name: profile.full_name,
      role: profile.role,
      avatar_url: profile.avatar_url,
    };
    this.currentUser.set(updated);
  }
}
