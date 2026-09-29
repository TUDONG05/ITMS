import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type DashboardRole = 'ADMIN' | 'MENTOR' | 'INTERN';

export interface DashboardMetric {
  key: string;
  label: string;
  value: number | string;
}

export interface DashboardTaskBreakdown {
  todo: number;
  in_progress: number;
  submitted: number;
  revision_required: number;
  completed: number;
  overdue: number;
}

export interface DashboardProgress {
  percent: number;
  completed: number;
  total: number;
}

export interface DashboardRecentItem {
  title: string;
  subtitle: string | null;
  status: string | null;
  due_at: string | null;
}

export interface DashboardResponse {
  role: DashboardRole;
  metrics: DashboardMetric[];
  task_breakdown: DashboardTaskBreakdown;
  progress: DashboardProgress | null;
  recent_items: DashboardRecentItem[];
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);

  getDashboard(internshipId?: string): Observable<DashboardResponse> {
    let params = new HttpParams();
    if (internshipId) {
      params = params.set('internship_id', internshipId);
    }
    return this.http.get<DashboardResponse>('/api/v1/dashboard', {
      headers: this.getHeaders(),
      params,
    });
  }

  private getHeaders(): HttpHeaders {
    const token = sessionStorage.getItem('itms_access_token');
    return new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {});
  }
}
