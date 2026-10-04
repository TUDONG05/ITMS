import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';

import { AuthService } from '../../core/api/auth.service';
import { LoginComponent } from './login.component';

@Component({ standalone: true, template: '' })
class DummyComponent {}

describe('LoginComponent', () => {
  it('tự chuyển về dashboard khi phiên đã được khôi phục', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([{ path: 'dashboard/:role', component: DummyComponent }]),
      ],
    });
    TestBed.inject(AuthService).storeSession({
      access_token: 'token',
      token_type: 'bearer',
      expires_in: 900,
      user: {
        id: '00000000-0000-0000-0000-000000000001',
        email: 'admin@itms.local',
        full_name: 'Quản trị viên',
        role: 'ADMIN',
        avatar_url: null,
      },
    });

    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/dashboard/admin');
  });
});
