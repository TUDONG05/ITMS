import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

export interface BackendHealth {
  environment: string;
  service: string;
  status: string;
}

@Injectable({ providedIn: 'root' })
export class BackendHealthService {
  private readonly http = inject(HttpClient);

  getStatus() {
    return this.http.get<BackendHealth>('/api/v1/health');
  }
}
