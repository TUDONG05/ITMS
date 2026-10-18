import { inject } from '@angular/core';
import { Routes } from '@angular/router';
import { AuthService } from './core/api/auth.service';
import { dashboardRoleGuard } from './core/guards/dashboard-role.guard';
import { ChangePasswordComponent } from './features/auth/change-password.component';
import { ForgotPasswordComponent } from './features/auth/forgot-password.component';
import { LoginComponent } from './features/auth/login.component';
import { ResetPasswordComponent } from './features/auth/reset-password.component';
import { DashboardShellComponent } from './features/dashboard/dashboard-shell.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'forgot-password', component: ForgotPasswordComponent },
  { path: 'reset-password', component: ResetPasswordComponent },
  { path: 'change-password', component: ChangePasswordComponent },
  {
    path: 'dashboard/:role',
    component: DashboardShellComponent,
    canActivate: [dashboardRoleGuard],
  },
  {
    path: 'profile',
    redirectTo: () => {
      const user = inject(AuthService).currentUser();
      if (!user) return '/login';
      const role = user.role?.toLowerCase() || 'intern';
      return `/dashboard/${role}?section=profile`;
    },
  },
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
