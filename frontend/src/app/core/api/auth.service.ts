import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { tap } from 'rxjs';

export interface LoginRequest {
  email: string;
  password: string;
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
  phone: string | null;
  avatar_url: string | null;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  readonly currentUser = signal<AuthenticatedUser | null>(this.readStoredUser());

  login(payload: LoginRequest) {
    return this.http
      .post<LoginResponse>('/api/v1/auth/login', payload)
      .pipe(tap((res) => this.storeSession(res)));
  }

  changePassword(payload: ChangePasswordRequest) {
    return this.http.post<MessageResponse>(
      '/api/v1/auth/change-password',
      payload,
      this.authorizedOptions(),
    );
  }

  requestPasswordReset(payload: ForgotPasswordRequest) {
    return this.http.post<MessageResponse>('/api/v1/auth/forgot-password', payload);
  }

  resetPassword(payload: ResetPasswordRequest) {
    return this.http.post<MessageResponse>('/api/v1/auth/reset-password', payload);
  }

  logout() {
    return this.http.post<MessageResponse>('/api/v1/auth/logout', {}, this.authorizedOptions());
  }

  // UC-5 – Profile
  getProfile() {
    return this.http
      .get<InternProfileRead>('/api/v1/profile', this.authorizedOptions())
      .pipe(tap((profile) => this.syncWithProfile(profile)));
  }

  updateProfile(payload: UpdateProfileRequest) {
    return this.http
      .patch<InternProfileRead>('/api/v1/profile', payload, this.authorizedOptions())
      .pipe(tap((profile) => this.syncWithProfile(profile)));
  }

  uploadAvatar(file: File) {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.http
      .post<InternProfileRead>('/api/v1/profile/avatar', form, this.authorizedOptions())
      .pipe(tap((profile) => this.syncWithProfile(profile)));
  }

  storeSession(response: LoginResponse): void {
    sessionStorage.setItem('itms_access_token', response.access_token);
    sessionStorage.setItem('itms_authenticated_user', JSON.stringify(response.user));
    this.currentUser.set(response.user);
  }

  clearSession(): void {
    sessionStorage.removeItem('itms_access_token');
    sessionStorage.removeItem('itms_authenticated_user');
    this.currentUser.set(null);
  }

  syncWithProfile(profile: InternProfileRead): void {
    const current = this.currentUser();
    const updated: AuthenticatedUser = {
      id: profile.id,
      email: profile.email,
      full_name: profile.full_name,
      role: profile.role,
      avatar_url: profile.avatar_url,
    };
    this.currentUser.set(updated);
    sessionStorage.setItem('itms_authenticated_user', JSON.stringify(updated));
  }

  private readStoredUser(): AuthenticatedUser | null {
    try {
      const raw = sessionStorage.getItem('itms_authenticated_user');
      return raw ? (JSON.parse(raw) as AuthenticatedUser) : null;
    } catch {
      return null;
    }
  }

  private authorizedOptions(): { headers: HttpHeaders } {
    const token = sessionStorage.getItem('itms_access_token');
    return { headers: new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {}) };
  }
}
