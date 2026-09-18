import { ChangeDetectionStrategy, Component } from '@angular/core';
import { LoginComponent } from './features/auth/login.component';

@Component({
  selector: 'app-root',
  imports: [LoginComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<app-login />',
})
export class App {}
