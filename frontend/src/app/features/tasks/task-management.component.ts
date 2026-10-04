import { CommonModule, DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
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

import { AuthService } from '../../core/api/auth.service';
import { Internship, InternshipService } from '../../core/api/internship.service';
import { MentorInternListItem, MentorService } from '../../core/api/mentor.service';
import { Task, TaskDetail, TaskService, TaskSubmission } from '../../core/api/task.service';

const STATUS_LABEL: Record<string, string> = {
  TODO: 'Chưa nộp',
  SUBMITTED: 'Chờ review',
  REVISION_REQUIRED: 'Yêu cầu làm lại',
  COMPLETED: 'Hoàn thành',
  CANCELLED: 'Đã hủy',
};

const STATUS_COLOR: Record<string, string> = {
  TODO: 'default',
  SUBMITTED: 'warning',
  REVISION_REQUIRED: 'error',
  COMPLETED: 'success',
  CANCELLED: 'default',
};

@Component({
  selector: 'app-task-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    NzButtonModule,
    NzCardModule,
    NzDrawerModule,
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
  ],
  providers: [DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './task-management.component.html',
  styleUrl: './task-management.component.scss',
})
export class TaskManagementComponent implements OnInit {
  private readonly taskService = inject(TaskService);
  private readonly mentorService = inject(MentorService);
  private readonly internshipService = inject(InternshipService);
  private readonly authService = inject(AuthService);
  private readonly message = inject(NzMessageService);
  private readonly cdr = inject(ChangeDetectorRef);

  protected readonly tasks = signal<Task[]>([]);
  protected readonly isLoading = signal(false);
  protected readonly searchQuery = signal('');
  protected readonly statusFilter = signal('');
  protected readonly overdueOnly = signal(false);
  protected readonly internshipFilter = signal('');
  protected readonly internships = signal<Internship[]>([]);

  protected readonly detail = signal<TaskDetail | null>(null);
  protected readonly isDetailOpen = signal(false);
  protected readonly isDetailLoading = signal(false);

  protected readonly isFormOpen = signal(false);
  protected readonly isSaving = signal(false);
  protected readonly isUploading = signal(false);
  protected readonly editingTask = signal<Task | null>(null);
  protected readonly form = signal<{
    internship_member_id: string;
    title: string;
    description: string;
    deadline: string;
    priority: string;
    attachment_url: string;
    attachment_name: string;
  }>({
    internship_member_id: '',
    title: '',
    description: '',
    deadline: '',
    priority: 'MEDIUM',
    attachment_url: '',
    attachment_name: '',
  });

  protected readonly interns = signal<MentorInternListItem[]>([]);
  protected readonly submitContent = signal('');
  protected readonly submitLink = signal('');
  protected readonly submitFileUrl = signal('');
  protected readonly submitFileName = signal('');
  protected readonly isEditingSubmission = signal(false);
  protected readonly reviewDecision = signal<'COMPLETED' | 'REVISION_REQUIRED'>('COMPLETED');
  protected readonly reviewComment = signal('');
  protected readonly commentContent = signal('');
  protected readonly isSubmitting = signal(false);
  protected readonly isDeletingSubmission = signal(false);

  protected readonly currentRole = computed(() => this.authService.currentUser()?.role ?? '');
  // UC-7: Mentor quản lý Task, Intern thực hiện. Admin không tham gia.
  protected readonly isMentorSide = computed(() => this.currentRole() === 'MENTOR');

  protected readonly filteredTasks = computed(() => this.tasks());

  private searchTimer?: ReturnType<typeof setTimeout>;

  ngOnInit(): void {
    this.loadTasks();
    this.loadInternships();
    if (this.isMentorSide()) this.loadInterns();
  }

  protected statusLabel(s: string): string {
    return STATUS_LABEL[s] ?? s;
  }

  protected statusColor(s: string): string {
    return STATUS_COLOR[s] ?? 'default';
  }

  protected onSearchChange(value: string): void {
    this.searchQuery.set(value);
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.loadTasks(), 350);
  }

  protected loadTasks(): void {
    this.isLoading.set(true);
    const filters: Record<string, string | boolean> = {};
    if (this.searchQuery().trim()) filters['search'] = this.searchQuery().trim();
    if (this.statusFilter()) filters['status'] = this.statusFilter();
    if (this.overdueOnly()) filters['overdue'] = true;
    if (this.internshipFilter()) filters['internship_id'] = this.internshipFilter();
    this.taskService.getTasks(filters).subscribe({
      next: (list) => {
        this.tasks.set(list);
        this.isLoading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoading.set(false);
        this.message.error('Không tải được danh sách task');
        this.cdr.markForCheck();
      },
    });
  }

  private loadInterns(): void {
    this.mentorService.getInterns().subscribe({
      next: (list) => this.interns.set(list),
      error: () => undefined,
    });
  }

  private loadInternships(): void {
    this.internshipService.getInternships().subscribe({
      next: (list) => this.internships.set(list),
      error: () => undefined,
    });
  }

  // ── Create / Edit ──
  protected openCreate(): void {
    this.editingTask.set(null);
    this.form.set({
      internship_member_id: '',
      title: '',
      description: '',
      deadline: '',
      priority: 'MEDIUM',
      attachment_url: '',
      attachment_name: '',
    });
    this.isFormOpen.set(true);
  }

  protected openEdit(task: Task): void {
    this.editingTask.set(task);
    this.form.set({
      internship_member_id: task.internship_member_id,
      title: task.title,
      description: task.description ?? '',
      deadline: task.deadline ? task.deadline.slice(0, 16) : '',
      priority: task.priority ?? 'MEDIUM',
      attachment_url: task.attachment_url ?? '',
      attachment_name: task.attachment_url?.split('/').pop() ?? '',
    });
    this.isFormOpen.set(true);
  }

  protected onTaskFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.isUploading.set(true);
    this.taskService.uploadFiles([file]).subscribe({
      next: (res) => {
        this.form.set({
          ...this.form(),
          attachment_url: res.urls[0] ?? '',
          attachment_name: file.name,
        });
        this.isUploading.set(false);
        this.message.success('Đã tải lên tệp đính kèm');
        this.cdr.markForCheck();
      },
      error: () => {
        this.isUploading.set(false);
        this.message.error('Tải tệp thất bại (tối đa 50MB, đúng định dạng cho phép)');
        this.cdr.markForCheck();
      },
    });
  }

  protected clearAttachment(): void {
    this.form.set({ ...this.form(), attachment_url: '', attachment_name: '' });
  }

  protected onSubmitFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.isUploading.set(true);
    this.taskService.uploadFiles([file]).subscribe({
      next: (res) => {
        this.submitFileUrl.set(res.urls[0] ?? '');
        this.submitFileName.set(file.name);
        this.isUploading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isUploading.set(false);
        this.message.error('Tải tệp thất bại (tối đa 50MB, đúng định dạng cho phép)');
        this.cdr.markForCheck();
      },
    });
  }

  protected saveForm(): void {
    const f = this.form();
    if (!f.title.trim()) {
      this.message.warning('Vui lòng nhập tiêu đề task');
      return;
    }
    if (!this.editingTask() && !f.internship_member_id) {
      this.message.warning('Vui lòng chọn intern nhận task');
      return;
    }
    this.isSaving.set(true);
    const payload = {
      internship_member_id: f.internship_member_id,
      title: f.title.trim(),
      description: f.description?.trim() || null,
      deadline: f.deadline ? new Date(f.deadline).toISOString() : null,
      priority: f.priority as 'LOW' | 'MEDIUM' | 'HIGH',
      attachment_url: f.attachment_url || null,
    };
    const editing = this.editingTask();
    const req = editing
      ? this.taskService.updateTask(editing.id, {
          title: payload.title,
          description: payload.description,
          deadline: payload.deadline,
          priority: payload.priority,
          attachment_url: payload.attachment_url,
        })
      : this.taskService.createTask(payload);
    req.subscribe({
      next: () => {
        this.message.success(editing ? 'Đã cập nhật task' : 'Đã giao task');
        this.isFormOpen.set(false);
        this.isSaving.set(false);
        this.loadTasks();
        if (this.detail()) this.openDetail(this.detail()!.id, true);
      },
      error: (err) => {
        this.isSaving.set(false);
        this.message.error(err?.error?.detail ?? 'Lưu task thất bại');
        this.cdr.markForCheck();
      },
    });
  }

  protected cancelTask(task: Task): void {
    this.taskService.cancelTask(task.id).subscribe({
      next: () => {
        this.message.success('Đã hủy task');
        this.loadTasks();
        if (this.detail()?.id === task.id) this.openDetail(task.id, true);
      },
      error: (err) => this.message.error(err?.error?.detail ?? 'Hủy task thất bại'),
    });
  }

  // ── Detail ──
  protected openDetail(id: string, silent = false): void {
    if (!silent) {
      this.resetSubmissionForm();
      this.isDetailOpen.set(true);
    }
    this.isDetailLoading.set(true);
    this.taskService.getTask(id).subscribe({
      next: (d) => {
        this.detail.set(d);
        this.isDetailLoading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isDetailLoading.set(false);
        this.message.error('Không tải được chi tiết task');
        this.cdr.markForCheck();
      },
    });
  }

  protected closeDetail(): void {
    this.isDetailOpen.set(false);
    this.detail.set(null);
    this.resetSubmissionForm();
  }

  // ── Submit (Intern) ──
  protected editSubmission(submission: TaskSubmission): void {
    const fileUrl = submission.file_url?.trim() ?? '';
    const isExternalLink = /^https?:\/\//i.test(fileUrl);

    this.submitContent.set(submission.content ?? '');
    this.submitLink.set(isExternalLink ? fileUrl : '');
    this.submitFileUrl.set(isExternalLink ? '' : fileUrl);
    this.submitFileName.set(isExternalLink ? '' : this.fileNameFromUrl(fileUrl));
    this.isEditingSubmission.set(true);
  }

  protected cancelEditSubmission(): void {
    this.resetSubmissionForm();
  }

  protected deleteSubmission(): void {
    const d = this.detail();
    if (!d) return;
    this.isDeletingSubmission.set(true);
    this.taskService.deleteSubmission(d.id).subscribe({
      next: () => {
        this.message.success('Đã xóa bài nộp');
        this.isDeletingSubmission.set(false);
        this.resetSubmissionForm();
        this.loadTasks();
        this.openDetail(d.id, true);
      },
      error: (err) => {
        this.isDeletingSubmission.set(false);
        this.message.error(err?.error?.detail ?? 'Xóa bài nộp thất bại');
        this.cdr.markForCheck();
      },
    });
  }

  protected submitWork(): void {
    const d = this.detail();
    if (!d) return;
    if (!this.submitContent().trim() && !this.submitLink().trim() && !this.submitFileUrl()) {
      this.message.warning('Nhập nội dung, link hoặc đính kèm tệp bài nộp');
      return;
    }
    this.isSubmitting.set(true);
    this.taskService
      .submitTask(d.id, {
        content: this.submitContent().trim() || null,
        link: this.submitLink().trim() || null,
        attachment_url: this.submitFileUrl() || null,
      })
      .subscribe({
        next: () => {
          this.message.success(this.isEditingSubmission() ? 'Đã cập nhật bài nộp' : 'Đã nộp bài');
          this.resetSubmissionForm();
          this.isSubmitting.set(false);
          this.loadTasks();
          this.openDetail(d.id, true);
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.message.error(err?.error?.detail ?? 'Nộp bài thất bại');
          this.cdr.markForCheck();
        },
      });
  }

  private resetSubmissionForm(): void {
    this.submitContent.set('');
    this.submitLink.set('');
    this.submitFileUrl.set('');
    this.submitFileName.set('');
    this.isEditingSubmission.set(false);
  }

  private fileNameFromUrl(url: string): string {
    if (!url) return '';
    const cleanUrl = url.split(/[?#]/, 1)[0];
    return decodeURIComponent(cleanUrl.split('/').pop() || url);
  }

  // ── Review (Mentor) ──
  protected reviewWork(): void {
    const d = this.detail();
    if (!d) return;
    this.isSubmitting.set(true);
    this.taskService
      .reviewTask(d.id, {
        decision: this.reviewDecision(),
        review_comment: this.reviewComment().trim() || null,
      })
      .subscribe({
        next: () => {
          this.message.success(
            this.reviewDecision() === 'COMPLETED' ? 'Đã xác nhận hoàn thành' : 'Đã yêu cầu làm lại',
          );
          this.reviewComment.set('');
          this.isSubmitting.set(false);
          this.loadTasks();
          this.openDetail(d.id, true);
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.message.error(err?.error?.detail ?? 'Review thất bại');
          this.cdr.markForCheck();
        },
      });
  }

  // ── Comment (FR-20) ──
  protected sendComment(): void {
    const d = this.detail();
    if (!d || !this.commentContent().trim()) return;
    this.taskService.addComment(d.id, this.commentContent().trim()).subscribe({
      next: () => {
        this.commentContent.set('');
        this.openDetail(d.id, true);
      },
      error: (err) => this.message.error(err?.error?.detail ?? 'Gửi bình luận thất bại'),
    });
  }
}
