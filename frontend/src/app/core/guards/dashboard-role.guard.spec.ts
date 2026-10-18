import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, convertToParamMap, Router, UrlTree } from '@angular/router';

import { AuthService } from '../api/auth.service';
import { dashboardRoleGuard } from './dashboard-role.guard';

async function setup(role: string | null, userRole: string | null): Promise<boolean | UrlTree> {
  TestBed.configureTestingModule({
    providers: [provideHttpClient(), provideHttpClientTesting()],
  });
  const auth = TestBed.inject(AuthService);
  if (userRole) {
    auth.storeSession({
      access_token: 'token',
      token_type: 'bearer',
      expires_in: 900,
      user: {
        id: '00000000-0000-0000-0000-000000000001',
        email: 'intern@itms.local',
        full_name: 'Thực tập sinh',
        role: userRole,
        avatar_url: null,
      },
    });
  }
  const route = {
    paramMap: convertToParamMap(role ? { role } : {}),
  } as ActivatedRouteSnapshot;
  const result = await TestBed.runInInjectionContext(() => dashboardRoleGuard(route, {} as never));
  return result as boolean | UrlTree;
}

describe('dashboardRoleGuard', () => {
  it('về /login khi chưa có currentUser', async () => {
    const result = (await setup('intern', null)) as UrlTree;
    const router = TestBed.inject(Router);
    expect(result).toEqual(router.createUrlTree(['/login']));
  });

  it('cho phép khi role khớp', async () => {
    expect(await setup('intern', 'INTERN')).toBe(true);
  });

  it('về /login khi role không khớp', async () => {
    const result = (await setup('admin', 'INTERN')) as UrlTree;
    const router = TestBed.inject(Router);
    expect(result).toEqual(router.createUrlTree(['/login']));
  });
});
