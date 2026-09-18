import { HttpClient } from '@angular/common/http';
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

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  login(payload: LoginRequest) {
    return this.http.post<LoginResponse>('/api/v1/auth/login', payload);
  }
}
