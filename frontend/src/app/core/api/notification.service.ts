import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

export interface Notification {
  id: string;
  title: string;
  content: string;
  target_type: 'ALL' | 'ROLE' | 'USER';
  target_data?: string[] | null;
  created_by: string;
  created_at: string;
  creator_name?: string | null;
  is_read?: boolean;
  read_at?: string | null;
  read_count?: number;
}

export interface NotificationCreate {
  title: string;
  content: string;
  target_type: 'ALL' | 'ROLE' | 'USER';
  target_data?: string[] | null;
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly http = inject(HttpClient);
  private readonly unreadCountSubject = new BehaviorSubject<number>(0);
  readonly unreadCount$ = this.unreadCountSubject.asObservable();

  getNotifications(): Observable<Notification[]> {
    return this.http.get<Notification[]>('/api/v1/notifications');
  }

  getUnreadCount(): Observable<{ unread_count: number }> {
    return this.http
      .get<{ unread_count: number }>('/api/v1/notifications/unread-count')
      .pipe(tap((res) => this.unreadCountSubject.next(res.unread_count)));
  }

  refreshUnreadCount(): void {
    this.getUnreadCount().subscribe({ error: () => undefined });
  }

  setUnreadCount(count: number): void {
    this.unreadCountSubject.next(Math.max(0, count));
  }

  getNotification(id: string): Observable<Notification> {
    return this.http.get<Notification>(`/api/v1/notifications/${id}`);
  }

  createNotification(payload: NotificationCreate): Observable<Notification> {
    return this.http.post<Notification>('/api/v1/notifications', payload).pipe(
      tap(() => this.refreshUnreadCount()),
    );
  }

  markAsRead(id: string): Observable<Notification> {
    return this.http.post<Notification>(`/api/v1/notifications/${id}/read`, {}).pipe(
      tap(() => {
        const current = this.unreadCountSubject.value;
        if (current > 0) {
          this.unreadCountSubject.next(current - 1);
        }
      }),
    );
  }

  markAllAsRead(): Observable<{ marked_count: number }> {
    return this.http.post<{ marked_count: number }>('/api/v1/notifications/read-all', {}).pipe(
      tap(() => this.unreadCountSubject.next(0)),
    );
  }

  deleteNotification(id: string): Observable<void> {
    return this.http.delete<void>(`/api/v1/notifications/${id}`).pipe(
      tap(() => this.refreshUnreadCount()),
    );
  }
}
