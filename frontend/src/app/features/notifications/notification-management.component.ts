import { DatePipe, SlicePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormsModule } from '@angular/forms';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTooltipModule } from 'ng-zorro-antd/tooltip';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzCardModule } from 'ng-zorro-antd/card';
import { AuthService } from '../../core/api/auth.service';
import { User, UserManagementService } from '../../core/api/user-management.service';
import {
  Notification,
  NotificationService,
} from '../../core/api/notification.service';

@Component({
  selector: 'app-notification-management',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    DatePipe,
    SlicePipe,
    FormsModule,
    ReactiveFormsModule,
    NzAlertModule,
    NzBadgeModule,
    NzButtonModule,
    NzCardModule,
    NzDividerModule,
    NzEmptyModule,
    NzFormModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzPopconfirmModule,
    NzSelectModule,
    NzSpinModule,
    NzTableModule,
    NzTagModule,
    NzTooltipModule,
  ],
  template: `
    <div class="notif-page">
      <!-- ===== ADMIN VIEW ===== -->
      @if (role === 'ADMIN') {
        <div class="page-header">
          <h2>
            <span nz-icon nzType="bell"></span> Quản lý Thông báo
          </h2>
          <button nz-button nzType="primary" (click)="openCreateModal()">
            <span nz-icon nzType="plus"></span> Tạo thông báo mới
          </button>
        </div>

        @if (errorMsg()) {
          <nz-alert nzType="error" [nzMessage]="errorMsg()!" nzShowIcon style="margin-bottom:16px;"></nz-alert>
        }

        <nz-spin [nzSpinning]="isLoading()">
          @if (notifications().length === 0 && !isLoading()) {
            <nz-empty nzNotFoundContent="Chưa có thông báo nào"></nz-empty>
          } @else {
            <nz-table
              #adminTable
              [nzData]="notifications()"
              [nzBordered]="true"
              nzSize="middle"
              [nzShowPagination]="notifications().length > 10"
            >
              <thead>
                <tr>
                  <th nzWidth="35%">Tiêu đề</th>
                  <th nzWidth="15%">Đối tượng</th>
                  <th nzWidth="12%">Lượt đọc</th>
                  <th nzWidth="18%">Ngày gửi</th>
                  <th nzWidth="10%">Người tạo</th>
                  <th nzWidth="10%">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                @for (n of adminTable.data; track n.id) {
                  <tr
                    class="notif-row"
                    (click)="viewDetail(n)"
                    style="cursor:pointer;"
                  >
                    <td>
                      <b>{{ n.title }}</b>
                      <div class="notif-content-preview">{{ n.content | slice: 0 : 80 }}{{ n.content.length > 80 ? '...' : '' }}</div>
                    </td>
                    <td>
                      <nz-tag [nzColor]="targetColor(n.target_type)">{{ targetLabel(n.target_type) }}</nz-tag>
                    </td>
                    <td>
                      <span nz-icon nzType="eye"></span> {{ n.read_count ?? 0 }}
                    </td>
                    <td>{{ n.created_at | date: 'dd/MM/yyyy HH:mm' }}</td>
                    <td>{{ n.creator_name ?? '-' }}</td>
                    <td>
                      <button
                        nz-button
                        nzType="text"
                        nzDanger
                        nz-popconfirm
                        nzPopconfirmTitle="Xóa thông báo này?"
                        nzPopconfirmPlacement="left"
                        (nzOnConfirm)="deleteNotification(n.id)"
                        (click)="$event.stopPropagation()"
                        nz-tooltip
                        nzTooltipTitle="Xóa"
                      >
                        <span nz-icon nzType="delete"></span>
                      </button>
                    </td>
                  </tr>
                }
              </tbody>
            </nz-table>
          }
        </nz-spin>

        <!-- Create Modal -->
        <nz-modal
          [(nzVisible)]="isCreateModalOpen"
          nzTitle="Tạo thông báo mới"
          [nzFooter]="null"
          (nzOnCancel)="closeCreateModal()"
          [nzWidth]="640"
        >
          <ng-container *nzModalContent>
            <form nz-form [formGroup]="createForm" nzLayout="vertical" (ngSubmit)="submitCreate()">
              <nz-form-item>
                <nz-form-label nzRequired>Tiêu đề</nz-form-label>
                <nz-form-control nzErrorTip="Vui lòng nhập tiêu đề">
                  <input nz-input formControlName="title" placeholder="Tiêu đề thông báo..." />
                </nz-form-control>
              </nz-form-item>
              <nz-form-item>
                <nz-form-label nzRequired>Nội dung</nz-form-label>
                <nz-form-control nzErrorTip="Vui lòng nhập nội dung">
                  <textarea
                    nz-input
                    formControlName="content"
                    placeholder="Nội dung thông báo..."
                    rows="4"
                  ></textarea>
                </nz-form-control>
              </nz-form-item>
              <nz-form-item>
                <nz-form-label nzRequired>Đối tượng nhận</nz-form-label>
                <nz-form-control>
                  <nz-select
                    formControlName="target_type"
                    (ngModelChange)="onTargetTypeChange()"
                    style="width: 100%;"
                  >
                    <nz-option nzValue="ALL" nzLabel="Tất cả người dùng"></nz-option>
                    <nz-option nzValue="ROLE" nzLabel="Theo vai trò"></nz-option>
                    <nz-option nzValue="USER" nzLabel="Người dùng cụ thể"></nz-option>
                  </nz-select>
                </nz-form-control>
              </nz-form-item>
              @if (createForm.get('target_type')?.value === 'ROLE') {
                <nz-form-item>
                  <nz-form-label nzRequired>Chọn vai trò</nz-form-label>
                  <nz-form-control>
                    <nz-select
                      formControlName="target_roles"
                      nzMode="multiple"
                      nzPlaceHolder="Chọn vai trò..."
                      style="width: 100%;"
                    >
                      <nz-option nzValue="INTERN" nzLabel="Thực tập sinh (INTERN)"></nz-option>
                      <nz-option nzValue="MENTOR" nzLabel="Mentor"></nz-option>
                    </nz-select>
                  </nz-form-control>
                </nz-form-item>
              }
              @if (createForm.get('target_type')?.value === 'USER') {
                <nz-form-item>
                  <nz-form-label nzRequired>Chọn người nhận</nz-form-label>
                  <nz-form-control>
                    <nz-select
                      formControlName="target_users"
                      nzMode="multiple"
                      [nzShowSearch]="true"
                      [nzServerSearch]="true"
                      (nzOnSearch)="onSearchUsers($event)"
                      [nzLoading]="isLoadingUsers()"
                      nzPlaceHolder="Tìm theo tên hoặc email người dùng..."
                      style="width: 100%;"
                    >
                      @for (u of usersList(); track u.id) {
                        <nz-option
                          [nzValue]="u.id"
                          [nzLabel]="u.full_name + ' (' + u.email + ') - ' + u.role"
                        ></nz-option>
                      }
                    </nz-select>
                  </nz-form-control>
                </nz-form-item>
              }
              <div style="display:flex; gap:8px; justify-content:flex-end; margin-top:16px;">
                <button nz-button nzType="default" type="button" (click)="closeCreateModal()">Hủy</button>
                <button
                  nz-button
                  nzType="primary"
                  type="submit"
                  [nzLoading]="isSubmitting()"
                  [disabled]="createForm.invalid"
                >
                  <span nz-icon nzType="send"></span> Gửi thông báo
                </button>
              </div>
            </form>
          </ng-container>
        </nz-modal>
      }

      <!-- ===== INTERN / MENTOR VIEW ===== -->
      @if (role === 'INTERN' || role === 'MENTOR') {
        <div class="page-header">
          <h2>
            <span nz-icon nzType="bell"></span> Thông báo của tôi
            @if (unreadCount() > 0) {
              <nz-badge [nzCount]="unreadCount()" style="margin-left:8px;"></nz-badge>
            }
          </h2>
          @if (unreadCount() > 0) {
            <button nz-button nzType="default" (click)="markAllAsRead()" [nzLoading]="isMarkingAll()">
              <span nz-icon nzType="check"></span> Đánh dấu tất cả đã đọc
            </button>
          }
        </div>

        @if (errorMsg()) {
          <nz-alert nzType="error" [nzMessage]="errorMsg()!" nzShowIcon style="margin-bottom:16px;"></nz-alert>
        }

        <nz-spin [nzSpinning]="isLoading()">
          @if (notifications().length === 0 && !isLoading()) {
            <nz-empty nzNotFoundContent="Không có thông báo nào"></nz-empty>
          } @else {
            <div class="notif-list">
              @for (n of notifications(); track n.id) {
                <nz-card
                  class="notif-card"
                  [class.notif-card--unread]="!n.is_read"
                  (click)="openUserDetail(n)"
                  style="cursor:pointer; margin-bottom:12px;"
                  [nzBordered]="true"
                >
                  <div class="notif-card__header">
                    <div class="notif-card__title-row">
                      @if (!n.is_read) {
                        <span class="unread-dot"></span>
                      }
                      <b class="notif-card__title">{{ n.title }}</b>
                      <nz-tag [nzColor]="targetColor(n.target_type)" style="margin-left:auto;">{{ targetLabel(n.target_type) }}</nz-tag>
                    </div>
                    <div class="notif-card__meta">
                      <span nz-icon nzType="clock-circle"></span>
                      {{ n.created_at | date: 'dd/MM/yyyy HH:mm' }}
                      @if (n.creator_name) {
                        &nbsp;&bull;&nbsp;{{ n.creator_name }}
                      }
                      @if (n.is_read && n.read_at) {
                        &nbsp;&bull;&nbsp;<span style="color:#52c41a;"><span nz-icon nzType="check-circle"></span> Đã đọc {{ n.read_at | date: 'dd/MM' }}</span>
                      }
                    </div>
                  </div>
                  <div class="notif-card__preview">{{ n.content | slice: 0 : 120 }}{{ n.content.length > 120 ? '...' : '' }}</div>
                </nz-card>
              }
            </div>
          }
        </nz-spin>

        <!-- Detail Modal for Intern/Mentor -->
        <nz-modal
          [(nzVisible)]="isDetailModalOpen"
          [nzTitle]="selectedNotif()?.title ?? 'Chi tiết thông báo'"
          [nzFooter]="null"
          (nzOnCancel)="closeDetailModal()"
          [nzWidth]="560"
        >
          <ng-container *nzModalContent>
            @if (selectedNotif(); as n) {
              <div class="notif-detail">
                <div class="notif-detail__meta">
                  <nz-tag [nzColor]="targetColor(n.target_type)">{{ targetLabel(n.target_type) }}</nz-tag>
                  <span class="notif-detail__date">
                    <span nz-icon nzType="clock-circle"></span>
                    {{ n.created_at | date: 'dd/MM/yyyy HH:mm' }}
                  </span>
                  @if (n.creator_name) {
                    <span>
                      <span nz-icon nzType="user"></span> {{ n.creator_name }}
                    </span>
                  }
                </div>
                <nz-divider></nz-divider>
                <div class="notif-detail__content">{{ n.content }}</div>
                @if (n.is_read && n.read_at) {
                  <div class="notif-detail__read-status">
                    <span nz-icon nzType="check-circle" nzTheme="fill" style="color:#52c41a;"></span>
                    Đã đọc lúc {{ n.read_at | date: 'dd/MM/yyyy HH:mm' }}
                  </div>
                }
              </div>
            }
          </ng-container>
        </nz-modal>
      }
    </div>
  `,
  styles: [
    `
      .notif-page {
        padding: 24px;
        max-width: 960px;
        margin: 0 auto;
      }
      .page-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 24px;
        h2 {
          font-size: 22px;
          font-weight: 700;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
      }
      .notif-content-preview {
        font-size: 12px;
        color: #888;
        margin-top: 2px;
        line-height: 1.4;
      }
      .notif-card--unread {
        border-left: 4px solid #1890ff !important;
        background: #f0f7ff !important;
      }
      .notif-card__header {
        margin-bottom: 6px;
      }
      .notif-card__title-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
      }
      .notif-card__title {
        font-size: 15px;
      }
      .notif-card__meta {
        font-size: 12px;
        color: #888;
        display: flex;
        align-items: center;
        gap: 4px;
      }
      .notif-card__preview {
        color: #555;
        font-size: 13px;
        line-height: 1.5;
      }
      .unread-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #1890ff;
        flex-shrink: 0;
      }
      .notif-detail {
        padding: 8px 0;
      }
      .notif-detail__meta {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        font-size: 13px;
        color: #666;
      }
      .notif-detail__date {
        display: flex;
        align-items: center;
        gap: 4px;
      }
      .notif-detail__content {
        white-space: pre-wrap;
        font-size: 14px;
        line-height: 1.7;
        color: #333;
        margin-bottom: 16px;
      }
      .notif-detail__read-status {
        color: #52c41a;
        font-size: 13px;
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .notif-row:hover td {
        background: #f5f5f5;
      }
    `,
  ],
})
export class NotificationManagementComponent implements OnInit {
  private readonly notifService = inject(NotificationService);
  private readonly authService = inject(AuthService);
  private readonly message = inject(NzMessageService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly userMgmtService = inject(UserManagementService);
  private readonly fb = inject(FormBuilder);

  protected readonly notifications = signal<Notification[]>([]);
  protected readonly isLoading = signal(false);
  protected readonly errorMsg = signal<string | null>(null);
  protected readonly isSubmitting = signal(false);
  protected readonly isMarkingAll = signal(false);
  protected readonly selectedNotif = signal<Notification | null>(null);

  protected readonly usersList = signal<User[]>([]);
  protected readonly isLoadingUsers = signal(false);

  protected isCreateModalOpen = false;
  protected isDetailModalOpen = false;

  protected role: string = 'INTERN';

  protected readonly createForm = this.fb.group({
    title: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(255)]],
    content: ['', [Validators.required, Validators.minLength(1)]],
    target_type: ['ALL', Validators.required],
    target_roles: [[] as string[]],
    target_users: [[] as string[]],
  });

  protected readonly unreadCount = () =>
    this.notifications().filter((n) => !n.is_read).length;

  ngOnInit(): void {
    const user = this.authService.currentUser();
    this.role = user?.role ?? 'INTERN';
    this.loadNotifications();
  }

  private loadNotifications(): void {
    this.isLoading.set(true);
    this.errorMsg.set(null);
    this.notifService.getNotifications().subscribe({
      next: (data) => {
        this.notifications.set(data);
        const count = this.role === 'ADMIN' ? data.length : data.filter((n) => !n.is_read).length;
        this.notifService.setUnreadCount(count);
        this.isLoading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.errorMsg.set('Không thể tải danh sách thông báo. Vui lòng thử lại.');
        this.isLoading.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  protected loadUsers(search?: string): void {
    this.isLoadingUsers.set(true);
    this.userMgmtService.getUsers({ search, limit: 50 }).subscribe({
      next: (users) => {
        this.usersList.set(users);
        this.isLoadingUsers.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoadingUsers.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  protected onSearchUsers(value: string): void {
    this.loadUsers(value.trim() || undefined);
  }

  protected openCreateModal(): void {
    this.createForm.reset({ target_type: 'ALL', target_roles: [], target_users: [] });
    this.isCreateModalOpen = true;
    this.loadUsers();
    this.cdr.markForCheck();
  }

  protected closeCreateModal(): void {
    this.isCreateModalOpen = false;
    this.cdr.markForCheck();
  }

  protected onTargetTypeChange(): void {
    this.createForm.patchValue({ target_roles: [], target_users: [] });
    if (this.createForm.get('target_type')?.value === 'USER' && this.usersList().length === 0) {
      this.loadUsers();
    }
    this.cdr.markForCheck();
  }

  protected submitCreate(): void {
    if (this.createForm.invalid) return;
    const val = this.createForm.value;
    let target_data: string[] | null = null;
    if (val.target_type === 'ROLE') {
      target_data = (val.target_roles as string[]) || [];
    } else if (val.target_type === 'USER') {
      target_data = (val.target_users as string[]) || [];
    }
    this.isSubmitting.set(true);
    this.notifService
      .createNotification({
        title: val.title!.trim(),
        content: val.content!.trim(),
        target_type: val.target_type as 'ALL' | 'ROLE' | 'USER',
        target_data,
      })
      .subscribe({
        next: (created) => {
          this.notifications.update((list) => [created, ...list]);
          this.message.success('Thông báo đã được gửi thành công!');
          this.isSubmitting.set(false);
          this.closeCreateModal();
          this.cdr.markForCheck();
        },
        error: (err: { error?: { detail?: string } }) => {
          this.message.error(err?.error?.detail ?? 'Không thể gửi thông báo. Vui lòng thử lại.');
          this.isSubmitting.set(false);
          this.cdr.markForCheck();
        },
      });
  }

  protected deleteNotification(id: string): void {
    this.notifService.deleteNotification(id).subscribe({
      next: () => {
        this.notifications.update((list) => list.filter((n) => n.id !== id));
        this.message.success('Xóa thông báo thành công!');
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Không thể xóa thông báo.');
        this.cdr.markForCheck();
      },
    });
  }

  protected viewDetail(n: Notification): void {
    this.selectedNotif.set(n);
    this.isDetailModalOpen = true;
    this.cdr.markForCheck();
  }

  protected openUserDetail(n: Notification): void {
    this.selectedNotif.set(n);
    this.isDetailModalOpen = true;
    // Auto-mark as read
    if (!n.is_read) {
      this.notifService.markAsRead(n.id).subscribe({
        next: (updated) => {
          this.notifications.update((list) =>
            list.map((item) => (item.id === n.id ? { ...item, ...updated } : item)),
          );
          this.selectedNotif.set({ ...n, ...updated });
          this.cdr.markForCheck();
        },
        error: () => undefined,
      });
    }
    this.cdr.markForCheck();
  }

  protected closeDetailModal(): void {
    this.isDetailModalOpen = false;
    this.selectedNotif.set(null);
    this.cdr.markForCheck();
  }

  protected markAllAsRead(): void {
    this.isMarkingAll.set(true);
    this.notifService.markAllAsRead().subscribe({
      next: () => {
        this.notifications.update((list) => list.map((n) => ({ ...n, is_read: true })));
        this.message.success('Đã đánh dấu tất cả thông báo là đã đọc!');
        this.isMarkingAll.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Không thể đánh dấu đã đọc. Vui lòng thử lại.');
        this.isMarkingAll.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  protected targetColor(type: string): string {
    if (type === 'ALL') return 'blue';
    if (type === 'ROLE') return 'green';
    if (type === 'USER') return 'orange';
    return 'default';
  }

  protected targetLabel(type: string): string {
    if (type === 'ALL') return 'Tất cả';
    if (type === 'ROLE') return 'Theo vai trò';
    if (type === 'USER') return 'Cụ thể';
    return type;
  }
}
