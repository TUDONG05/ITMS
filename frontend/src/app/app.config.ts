import { registerLocaleData } from '@angular/common';
import { provideHttpClient } from '@angular/common/http';
import vi from '@angular/common/locales/vi';
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';

import {
  AppstoreOutline,
  ArrowRightOutline,
  AuditOutline,
  BarChartOutline,
  BellOutline,
  BookOutline,
  CalendarOutline,
  CameraOutline,
  CheckCircleOutline,
  CheckSquareOutline,
  DeleteOutline,
  EditOutline,
  FileTextOutline,
  FormOutline,
  HomeOutline,
  InboxOutline,
  InfoCircleOutline,
  KeyOutline,
  LockOutline,
  LoginOutline,
  LogoutOutline,
  MailOutline,
  MenuOutline,
  PartitionOutline,
  PlusOutline,
  ReadOutline,
  ReloadOutline,
  RobotOutline,
  SearchOutline,
  SettingOutline,
  SolutionOutline,
  StarOutline,
  SwapOutline,
  TeamOutline,
  TrophyOutline,
  UnlockOutline,
  UserAddOutline,
  UserOutline,
  WarningOutline,
} from '@ant-design/icons-angular/icons';

// Import đầy đủ các I18n & Date Adapter provider từ Ng-Zorro
import { provideNzNativeDateAdapter } from 'ng-zorro-antd/core/time';
import { NZ_I18N, NzI18nService, provideNzI18n, vi_VN } from 'ng-zorro-antd/i18n';
import { provideNzIcons } from 'ng-zorro-antd/icon';

import { routes } from './app.routes';

// Đăng ký locale tiếng Việt cho Angular
registerLocaleData(vi);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideAnimations(),
    provideRouter(routes),
    provideHttpClient(),

    // 👉 Cấp Provider I18n & NzI18nService để giải quyết lỗi NG0201
    provideNzI18n(vi_VN),
    provideNzNativeDateAdapter(),

    provideNzIcons([
      AppstoreOutline,
      ArrowRightOutline,
      AuditOutline,
      BarChartOutline,
      BellOutline,
      BookOutline,
      CalendarOutline,
      CameraOutline,
      CheckCircleOutline,
      CheckSquareOutline,
      DeleteOutline,
      EditOutline,
      FileTextOutline,
      FormOutline,
      HomeOutline,
      InboxOutline,
      InfoCircleOutline,
      KeyOutline,
      LockOutline,
      LoginOutline,
      LogoutOutline,
      MailOutline,
      MenuOutline,
      PartitionOutline,
      PlusOutline,
      ReadOutline,
      ReloadOutline,
      RobotOutline,
      SearchOutline,
      SettingOutline,
      SolutionOutline,
      StarOutline,
      SwapOutline,
      TeamOutline,
      TrophyOutline,
      UnlockOutline,
      UserAddOutline,
      UserOutline,
      WarningOutline,
    ]),
  ],
};