import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
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


@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  login(payload: LoginRequest) {
    return this.http.post<LoginResponse>('/api/v1/auth/login', payload);
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

  storeSession(response: LoginResponse): void {
    sessionStorage.setItem('itms_access_token', response.access_token);
    sessionStorage.setItem('itms_authenticated_user', JSON.stringify(response.user));
  }

  clearSession(): void {
    sessionStorage.removeItem('itms_access_token');
    sessionStorage.removeItem('itms_authenticated_user');
  }

  private authorizedOptions(): { headers: HttpHeaders } {
    const token = sessionStorage.getItem('itms_access_token');
    return { headers: new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {}) };
  }
}
