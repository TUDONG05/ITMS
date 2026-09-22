import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

const VALID_ROLES = new Set(['intern', 'mentor', 'admin']);

export const dashboardRoleGuard: CanActivateFn = (route) => {
  const router = inject(Router);
  const requestedRole = route.paramMap.get('role')?.toLowerCase();
  const savedUser = sessionStorage.getItem('itms_authenticated_user');

  if (!requestedRole || !VALID_ROLES.has(requestedRole) || !savedUser) {
    return router.createUrlTree(['/login']);
  }

  try {
    const user = JSON.parse(savedUser) as { role?: string };
    return user.role?.toLowerCase() === requestedRole || router.createUrlTree(['/login']);
  } catch {
    return router.createUrlTree(['/login']);
  }
};
