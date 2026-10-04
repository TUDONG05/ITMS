import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AuthService, LoginResponse } from '../api/auth.service';
import { authInterceptor } from './auth.interceptor';

const response = (token: string): LoginResponse => ({
  access_token: token,
  token_type: 'bearer',
  expires_in: 900,
  user: {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'intern@itms.local',
    full_name: 'Thực tập sinh',
    role: 'INTERN',
    avatar_url: null,
  },
});

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let auth: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    auth.storeSession(response('expired-token'));
  });

  afterEach(() => httpMock.verify());

  it('dùng chung một refresh request cho hai phản hồi 401 đồng thời', () => {
    http.get('/api/v1/dashboard').subscribe();
    http.get('/api/v1/profile').subscribe();

    const dashboard = httpMock.expectOne('/api/v1/dashboard');
    const profile = httpMock.expectOne('/api/v1/profile');
    expect(dashboard.request.headers.get('Authorization')).toBe('Bearer expired-token');
    expect(profile.request.headers.get('Authorization')).toBe('Bearer expired-token');
    dashboard.flush({}, { status: 401, statusText: 'Unauthorized' });
    profile.flush({}, { status: 401, statusText: 'Unauthorized' });

    const refreshRequests = httpMock.match('/api/v1/auth/refresh');
    expect(refreshRequests).toHaveLength(1);
    refreshRequests[0].flush(response('fresh-token'));

    const retriedDashboard = httpMock.expectOne('/api/v1/dashboard');
    const retriedProfile = httpMock.expectOne('/api/v1/profile');
    expect(retriedDashboard.request.headers.get('Authorization')).toBe('Bearer fresh-token');
    expect(retriedProfile.request.headers.get('Authorization')).toBe('Bearer fresh-token');
    retriedDashboard.flush({});
    retriedProfile.flush({});
  });
});
