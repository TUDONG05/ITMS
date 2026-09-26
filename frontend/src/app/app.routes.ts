import { Routes } from '@angular/router';
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
      const savedUser = sessionStorage.getItem('itms_authenticated_user');
      if (!savedUser) return '/login';
      try {
        const user = JSON.parse(savedUser) as { role?: string };
        const role = user.role?.toLowerCase() || 'intern';
        return `/dashboard/${role}?section=profile`;
      } catch {
        return '/login';
      }
    },
  },
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
