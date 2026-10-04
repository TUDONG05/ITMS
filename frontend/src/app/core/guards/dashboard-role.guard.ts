import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../api/auth.service';

const VALID_ROLES = new Set(['intern', 'mentor', 'admin']);

export const dashboardRoleGuard: CanActivateFn = (route) => {
  const router = inject(Router);
  const auth = inject(AuthService);
  const requestedRole = route.paramMap.get('role')?.toLowerCase();
  const user = auth.currentUser();

  if (!requestedRole || !VALID_ROLES.has(requestedRole) || !user) {
    return router.createUrlTree(['/login']);
  }

  return user.role?.toLowerCase() === requestedRole || router.createUrlTree(['/login']);
};
