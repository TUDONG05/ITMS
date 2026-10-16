import { DatePipe, NgTemplateOutlet } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzProgressModule } from 'ng-zorro-antd/progress';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzTagModule } from 'ng-zorro-antd/tag';

import { apiMessage } from '../../core/api/api-error';
import {
  Evaluation,
  EvaluationCriterion,
  EvaluationService,
  EvaluationStatus,
  EvaluationType,
  previewTotal,
} from '../../core/api/evaluation.service';
import { AuthService } from '../../core/api/auth.service';
import { MentorInternListItem, MentorService } from '../../core/api/mentor.service';
import { EvaluationCriteriaComponent } from './evaluation-criteria.component';

const TYPE_LABEL: Record<EvaluationType, string> = {
  PERIODIC: 'Đánh giá định kỳ',
  FINAL: 'Đánh giá cuối kỳ',
};

const STATUS_LABEL: Record<EvaluationStatus, string> = {
  DRAFT: 'Bản nháp',
  PUBLISHED: 'Đã công bố',
};

/**
 * UC-12: Quản lý đánh giá, hiển thị theo vai trò.
 * - Intern: xem kết quả đã công bố của mình.
 * - Mentor: lập, lưu nháp và công bố đánh giá cho Intern mình phụ trách.
 * - Admin: quản lý tiêu chí; xem đánh giá (kể cả nháp) để giám sát, không sửa/công bố.
 */
@Component({
  selector: 'app-evaluations',
  standalone: true,
  imports: [
    DatePipe,
    NgTemplateOutlet,
    FormsModule,
    NzAlertModule,
    NzButtonModule,
    NzCardModule,
    NzDrawerModule,
    NzEmptyModule,
    NzInputModule,
    NzInputNumberModule,
    NzModalModule,
    NzPopconfirmModule,
    NzProgressModule,
    NzSelectModule,
    NzSpinModule,
    NzTableModule,
    NzTabsModule,
    NzTagModule,
    EvaluationCriteriaComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './evaluations.component.html',
  styleUrl: './evaluations.component.scss',
})
export class EvaluationsComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly evaluationService = inject(EvaluationService);
  private readonly mentorService = inject(MentorService);
  private readonly message = inject(NzMessageService);

  protected readonly role = computed(() => this.auth.currentUser()?.role ?? '');
  protected readonly isIntern = computed(() => this.role() === 'INTERN');
  protected readonly isMentor = computed(() => this.role() === 'MENTOR');
  protected readonly isAdmin = computed(() => this.role() === 'ADMIN');

  protected readonly evaluations = signal<Evaluation[]>([]);
  protected readonly isLoading = signal(true);
  protected readonly loadError = signal<string | null>(null);
  protected readonly statusFilter = signal<EvaluationStatus | ''>('');

  protected readonly detail = signal<Evaluation | null>(null);
  protected readonly isDetailOpen = signal(false);

  // ── Trình soạn đánh giá (Mentor) ──
  protected readonly criteria = signal<EvaluationCriterion[]>([]);
  protected readonly interns = signal<MentorInternListItem[]>([]);
  protected readonly isEditorOpen = signal(false);
  protected readonly isLoadingLookups = signal(false);
  protected readonly isSaving = signal(false);
  protected readonly editingId = signal<string | null>(null);
  protected readonly editorError = signal<string | null>(null);
  protected readonly memberId = signal<string | null>(null);
  protected readonly evaluationType = signal<EvaluationType>('PERIODIC');
  protected readonly scoreMap = signal<Record<string, number | null>>({});
  protected readonly comment = signal('');

  protected readonly typeOptions = (Object.keys(TYPE_LABEL) as EvaluationType[]).map((value) => ({
    value,
    label: TYPE_LABEL[value],
  }));

  protected readonly internOptions = computed(() =>
    this.interns().map((item) => ({
      value: item.id,
      label: `${item.intern_name} (${item.internship_name})`,
    })),
  );

  /** Tổng điểm tạm tính; chỉ có khi đã chấm đủ mọi tiêu chí đang áp dụng. */
  protected readonly previewScore = computed(() => {
    const criteria = this.criteria();
    const scores = this.scoreMap();
    if (criteria.length === 0) return null;
    const items: { score: number; max_score: number; weight: number }[] = [];
    for (const criterion of criteria) {
      const value = scores[criterion.id];
      if (value === null || value === undefined) return null;
      items.push({ score: value, max_score: criterion.max_score, weight: criterion.weight });
    }
    return previewTotal(items);
  });

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.isLoading.set(true);
    this.loadError.set(null);
    this.evaluationService.listEvaluations({ status: this.statusFilter() }).subscribe({
      next: (data) => {
        this.evaluations.set(data);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.loadError.set(apiMessage(err, 'Không tải được danh sách đánh giá.'));
      },
    });
  }

  protected setStatusFilter(value: EvaluationStatus | ''): void {
    this.statusFilter.set(value ?? '');
    this.load();
  }

  // ── Hiển thị ──
  protected typeLabel(type: EvaluationType): string {
    return TYPE_LABEL[type];
  }

  protected statusLabel(status: EvaluationStatus): string {
    return STATUS_LABEL[status];
  }

  protected statusColor(status: EvaluationStatus): string {
    return status === 'PUBLISHED' ? 'success' : 'orange';
  }

  protected scorePercent(evaluation: Evaluation): number {
    return Math.round((evaluation.total_score ?? 0) * 10);
  }

  protected openDetail(evaluation: Evaluation): void {
    this.detail.set(evaluation);
    this.isDetailOpen.set(true);
  }

  protected closeDetail(): void {
    this.isDetailOpen.set(false);
    this.detail.set(null);
  }

  // ── Mentor: soạn đánh giá ──
  protected openCreate(): void {
    this.editingId.set(null);
    this.memberId.set(null);
    this.evaluationType.set('PERIODIC');
    this.scoreMap.set({});
    this.comment.set('');
    this.editorError.set(null);
    this.openEditor();
  }

  protected openEdit(evaluation: Evaluation): void {
    this.editingId.set(evaluation.id);
    this.memberId.set(evaluation.internship_member_id);
    this.evaluationType.set(evaluation.evaluation_type);
    this.scoreMap.set(
      Object.fromEntries(evaluation.scores.map((item) => [item.criterion_id, item.score])),
    );
    this.comment.set(evaluation.comment ?? '');
    this.editorError.set(null);
    this.openEditor();
  }

  private openEditor(): void {
    this.isEditorOpen.set(true);
    this.isLoadingLookups.set(true);
    let pending = 2;
    const done = (): void => {
      pending -= 1;
      if (pending === 0) this.isLoadingLookups.set(false);
    };
    this.evaluationService.listCriteria().subscribe({
      next: (data) => {
        this.criteria.set(data.items);
        done();
      },
      error: (err) => {
        this.editorError.set(apiMessage(err, 'Không tải được tiêu chí đánh giá.'));
        done();
      },
    });
    this.mentorService.getInterns().subscribe({
      next: (data) => {
        this.interns.set(data);
        done();
      },
      error: (err) => {
        this.editorError.set(apiMessage(err, 'Không tải được danh sách Intern.'));
        done();
      },
    });
  }

  protected closeEditor(): void {
    this.isEditorOpen.set(false);
  }

  protected setScore(criterionId: string, value: number | null): void {
    this.scoreMap.update((current) => ({ ...current, [criterionId]: value }));
  }

  protected scoreOf(criterionId: string): number | null {
    return this.scoreMap()[criterionId] ?? null;
  }

  private buildScores(): { criterion_id: string; score: number }[] | null {
    const scores: { criterion_id: string; score: number }[] = [];
    for (const criterion of this.criteria()) {
      const value = this.scoreMap()[criterion.id];
      if (value === null || value === undefined) continue;
      if (value < 0 || value > criterion.max_score) {
        this.editorError.set(
          `Điểm của tiêu chí "${criterion.name}" phải từ 0 đến ${criterion.max_score}.`,
        );
        return null;
      }
      scores.push({ criterion_id: criterion.id, score: value });
    }
    return scores;
  }

  protected saveDraft(): void {
    this.submitEditor(false);
  }

  protected saveAndPublish(): void {
    this.submitEditor(true);
  }

  private submitEditor(publish: boolean): void {
    this.editorError.set(null);
    const existingId = this.editingId();
    const memberId = this.memberId();
    if (!existingId && !memberId) {
      this.editorError.set('Vui lòng chọn Intern cần đánh giá.');
      return;
    }
    const scores = this.buildScores();
    if (scores === null) return;
    const comment = this.comment().trim() || null;

    this.isSaving.set(true);
    const save$ = existingId
      ? this.evaluationService.updateEvaluation(existingId, {
          evaluation_type: this.evaluationType(),
          scores,
          comment,
        })
      : this.evaluationService.createEvaluation({
          internship_member_id: memberId as string,
          evaluation_type: this.evaluationType(),
          scores,
          comment,
        });

    save$.subscribe({
      next: (saved) => {
        // Từ đây bản nháp đã tồn tại: lưu lại id để lần bấm tiếp theo không tạo bản trùng.
        this.editingId.set(saved.id);
        if (!publish) {
          this.finishSave('Đã lưu bản nháp');
          return;
        }
        this.evaluationService.publishEvaluation(saved.id).subscribe({
          next: () => this.finishSave('Đã công bố đánh giá cho Intern'),
          error: (err) => {
            this.isSaving.set(false);
            this.editorError.set(
              `${apiMessage(err, 'Không công bố được đánh giá.')} Bản nháp đã được lưu.`,
            );
            this.load();
          },
        });
      },
      error: (err) => {
        this.isSaving.set(false);
        this.editorError.set(apiMessage(err, 'Không lưu được đánh giá.'));
      },
    });
  }

  private finishSave(successMessage: string): void {
    this.isSaving.set(false);
    this.isEditorOpen.set(false);
    this.message.success(successMessage);
    this.load();
  }

  protected publishRow(evaluation: Evaluation): void {
    this.evaluationService.publishEvaluation(evaluation.id).subscribe({
      next: () => {
        this.message.success('Đã công bố đánh giá cho Intern');
        this.load();
      },
      error: (err) => this.message.error(apiMessage(err, 'Không công bố được đánh giá.')),
    });
  }
}
