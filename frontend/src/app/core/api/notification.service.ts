import { HttpClient } from '@angular/common/http';
import { Injectable, inject, OnDestroy } from '@angular/core';
import { BehaviorSubject, Observable, Subject, Subscription, interval, tap } from 'rxjs';
import { AuthService } from './auth.service';

export interface Notification {
  id: string;
  title: string;
  content: string;
  target_type: 'ALL' | 'ROLE' | 'USER';
  target_data?: string[] | null;
  recipient_names?: string[] | null;
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

export interface NotificationUpdate {
  title?: string;
  content?: string;
  target_type?: 'ALL' | 'ROLE' | 'USER';
  target_data?: string[] | null;
}

@Injectable({ providedIn: 'root' })
export class NotificationService implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);

  private readonly unreadCountSubject = new BehaviorSubject<number>(0);
  readonly unreadCount$ = this.unreadCountSubject.asObservable();

  readonly notificationsChanged$ = new Subject<void>();

  private isRefreshing = false;
  private pollSubscription?: Subscription;
  private visibilityListener?: () => void;
  private focusListener?: () => void;

  constructor() {
    this.setupWindowListeners();
  }

  notifyChanged(): void {
    this.notificationsChanged$.next();
  }

  private setupWindowListeners(): void {
    if (typeof window !== 'undefined') {
      this.visibilityListener = () => {
        if (document.visibilityState === 'visible' && this.authService.currentUser()) {
          this.refreshUnreadCount();
          this.notifyChanged();
        }
      };
      this.focusListener = () => {
        if (this.authService.currentUser()) {
          this.refreshUnreadCount();
          this.notifyChanged();
        }
      };
      document.addEventListener('visibilitychange', this.visibilityListener);
      window.addEventListener('focus', this.focusListener);
    }
  }

  startPolling(intervalMs = 3000): void {
    this.stopPolling();
    this.refreshUnreadCount();
    this.pollSubscription = interval(intervalMs).subscribe(() => {
      this.refreshUnreadCount();
    });
  }

  stopPolling(): void {
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
      this.pollSubscription = undefined;
    }
  }

  clear(): void {
    this.stopPolling();
    this.unreadCountSubject.next(0);
  }

  getNotifications(): Observable<Notification[]> {
    return this.http.get<Notification[]>('/api/v1/notifications');
  }

  getUnreadCount(): Observable<{ unread_count: number }> {
    return this.http.get<{ unread_count: number }>('/api/v1/notifications/unread-count').pipe(
      tap({
        next: (res) => {
          const previous = this.unreadCountSubject.value;
          this.unreadCountSubject.next(res.unread_count);
          if (previous !== res.unread_count) {
            this.notifyChanged();
          }
        },
        error: (err: { status?: number }) => {
          if (err?.status === 401) {
            this.stopPolling();
            this.unreadCountSubject.next(0);
          }
        },
      }),
    );
  }

  refreshUnreadCount(): void {
    if (!this.authService.currentUser()) {
      return;
    }
    if (this.isRefreshing) {
      return;
    }
    this.isRefreshing = true;
    this.getUnreadCount().subscribe({
      next: () => {
        this.isRefreshing = false;
      },
      error: () => {
        this.isRefreshing = false;
      },
    });
  }

  setUnreadCount(count: number): void {
    this.unreadCountSubject.next(Math.max(0, count));
  }

  getNotification(id: string): Observable<Notification> {
    return this.http.get<Notification>(`/api/v1/notifications/${id}`);
  }

  createNotification(payload: NotificationCreate): Observable<Notification> {
    return this.http.post<Notification>('/api/v1/notifications', payload).pipe(
      tap(() => {
        this.refreshUnreadCount();
        this.notifyChanged();
      }),
    );
  }

  updateNotification(id: string, payload: NotificationUpdate): Observable<Notification> {
    return this.http.put<Notification>(`/api/v1/notifications/${id}`, payload).pipe(
      tap(() => {
        this.refreshUnreadCount();
        this.notifyChanged();
      }),
    );
  }

  markAsRead(id: string): Observable<Notification> {
    return this.http.post<Notification>(`/api/v1/notifications/${id}/read`, {}).pipe(
      tap(() => {
        const current = this.unreadCountSubject.value;
        if (current > 0) {
          this.unreadCountSubject.next(current - 1);
        }
        this.notifyChanged();
      }),
    );
  }

  markAllAsRead(): Observable<{ marked_count: number }> {
    return this.http.post<{ marked_count: number }>('/api/v1/notifications/read-all', {}).pipe(
      tap(() => {
        this.unreadCountSubject.next(0);
        this.notifyChanged();
      }),
    );
  }

  deleteNotification(id: string): Observable<void> {
    return this.http.delete<void>(`/api/v1/notifications/${id}`).pipe(
      tap(() => {
        this.refreshUnreadCount();
        this.notifyChanged();
      }),
    );
  }

  ngOnDestroy(): void {
    this.stopPolling();
    if (typeof window !== 'undefined') {
      if (this.visibilityListener) {
        document.removeEventListener('visibilitychange', this.visibilityListener);
      }
      if (this.focusListener) {
        window.removeEventListener('focus', this.focusListener);
      }
    }
  }
}
