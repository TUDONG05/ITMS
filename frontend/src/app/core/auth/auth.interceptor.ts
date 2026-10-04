import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';

import { AuthService } from '../api/auth.service';

const PUBLIC_AUTH_PATTERNS = [
  '/api/v1/auth/login',
  '/api/v1/auth/refresh',
  '/api/v1/auth/forgot-password',
  '/api/v1/auth/reset-password',
];

function isPublicAuthRequest(url: string): boolean {
  return PUBLIC_AUTH_PATTERNS.some((pattern) => url.includes(pattern));
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (isPublicAuthRequest(req.url)) {
    return next(req);
  }

  const token = auth.accessToken();
  const authorized = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(authorized).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || error.status !== 401) {
        return throwError(() => error);
      }
      return auth.refreshSession().pipe(
        switchMap(() => {
          const freshToken = auth.accessToken();
          const retried = freshToken
            ? req.clone({ setHeaders: { Authorization: `Bearer ${freshToken}` } })
            : req;
          return next(retried);
        }),
        catchError((refreshError: unknown) => {
          auth.clearSession();
          void router.navigate(['/login']);
          return throwError(() => refreshError);
        }),
      );
    }),
  );
};
