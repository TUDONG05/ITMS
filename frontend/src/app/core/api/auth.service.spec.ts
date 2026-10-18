import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService, LoginResponse } from './auth.service';

const LOGIN_RESPONSE: LoginResponse = {
  access_token: 'access-token',
  token_type: 'bearer',
  expires_in: 900,
  user: {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'intern@itms.local',
    full_name: 'Thực tập sinh',
    role: 'INTERN',
    avatar_url: null,
  },
};

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    sessionStorage.clear();
  });

  it('chỉ giữ access token và người dùng trong bộ nhớ', () => {
    service.storeSession(LOGIN_RESPONSE);

    expect(service.currentUser()).toEqual(LOGIN_RESPONSE.user);
    expect(service.accessToken()).toBe('access-token');
    expect(sessionStorage.getItem('itms_access_token')).toBeNull();
    expect(sessionStorage.getItem('itms_authenticated_user')).toBeNull();
  });

  it('khôi phục phiên từ refresh cookie khi khởi tạo ứng dụng', async () => {
    const initialized = service.initialize();
    const request = httpMock.expectOne('/api/v1/auth/refresh');
    expect(request.request.withCredentials).toBe(true);
    request.flush(LOGIN_RESPONSE);

    await initialized;
    expect(service.currentUser()).toEqual(LOGIN_RESPONSE.user);
    expect(service.accessToken()).toBe('access-token');
  });
});
