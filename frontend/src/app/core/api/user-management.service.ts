import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

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

interface UserFilters {
  role?: UserRole;
  status?: UserStatus;
  search?: string;
  skip?: number;
  limit?: number;
}

@Injectable({ providedIn: 'root' })
export class UserManagementService {
  private readonly http = inject(HttpClient);

  getUsers(filters?: UserFilters): Observable<User[]> {
    return this.http.get<User[]>('/api/v1/users', { params: this.userParams(filters) });
  }

  getUserPage(filters: UserFilters): Observable<{ users: User[]; total: number }> {
    return this.http
      .get<User[]>('/api/v1/users', {
        params: this.userParams(filters).set('include_total', true),
        observe: 'response',
      })
      .pipe(
        map((response) => {
          const users = response.body ?? [];
          return { users, total: Number(response.headers.get('X-Total-Count') ?? users.length) };
        }),
      );
  }

  private userParams(filters?: UserFilters): HttpParams {
    let params = new HttpParams();
    if (filters?.role) params = params.set('role', filters.role);
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.search) params = params.set('search', filters.search);
    if (filters?.skip != null) params = params.set('skip', filters.skip);
    if (filters?.limit != null) params = params.set('limit', filters.limit);
    return params;
  }

  createUser(payload: CreateUserPayload): Observable<User> {
    return this.http.post<User>('/api/v1/users', payload, {});
  }

  getUser(userId: string): Observable<User> {
    return this.http.get<User>(`/api/v1/users/${userId}`, {});
  }

  updateUser(userId: string, payload: UpdateUserPayload): Observable<User> {
    return this.http.patch<User>(`/api/v1/users/${userId}`, payload, {});
  }

  updateUserStatus(userId: string, payload: UpdateUserStatusPayload): Observable<User> {
    return this.http.patch<User>(`/api/v1/users/${userId}/status`, payload, {});
  }
}
