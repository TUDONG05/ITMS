import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type UserRole = 'ADMIN' | 'MENTOR' | 'INTERN';
export type UserStatus = 'ACTIVE' | 'LOCKED' | 'INACTIVE';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  status: UserStatus;
  phone: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateUserPayload {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  status?: UserStatus;
  phone?: string | null;
}

export interface UpdateUserPayload {
  full_name?: string;
  phone?: string | null;
  role?: UserRole;
}

export interface UpdateUserStatusPayload {
  status: UserStatus;
}

@Injectable({ providedIn: 'root' })
export class UserManagementService {
  private readonly http = inject(HttpClient);

  private getHeaders(): HttpHeaders {
    const token = sessionStorage.getItem('itms_access_token');
    return new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {});
  }

  getUsers(filters?: {
    role?: UserRole;
    status?: UserStatus;
    search?: string;
    skip?: number;
    limit?: number;
  }): Observable<User[]> {
    let params = new HttpParams();
    if (filters?.role) params = params.set('role', filters.role);
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.search) params = params.set('search', filters.search);
    if (filters?.skip != null) params = params.set('skip', filters.skip);
    if (filters?.limit != null) params = params.set('limit', filters.limit);
    return this.http.get<User[]>('/api/v1/users', {
      headers: this.getHeaders(),
      params,
    });
  }

  createUser(payload: CreateUserPayload): Observable<User> {
    return this.http.post<User>('/api/v1/users', payload, {
      headers: this.getHeaders(),
    });
  }

  getUser(userId: string): Observable<User> {
    return this.http.get<User>(`/api/v1/users/${userId}`, {
      headers: this.getHeaders(),
    });
  }

  updateUser(userId: string, payload: UpdateUserPayload): Observable<User> {
    return this.http.patch<User>(`/api/v1/users/${userId}`, payload, {
      headers: this.getHeaders(),
    });
  }

  updateUserStatus(userId: string, payload: UpdateUserStatusPayload): Observable<User> {
    return this.http.patch<User>(`/api/v1/users/${userId}/status`, payload, {
      headers: this.getHeaders(),
    });
  }
}

