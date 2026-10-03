import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzCollapseModule } from 'ng-zorro-antd/collapse';
import { NzDividerModule } from 'ng-zorro-antd/divider';
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

import {
  ContentType,
  LearningContent,
  Phase,
  Question,
  QuestionType,
  Quiz,
  QuizStatus,
  Roadmap,
  RoadmapDetail,
  RoadmapStatus,
  TrainingService,
} from '../../core/api/training.service';
import { forkJoin } from 'rxjs';

export interface DraftQuestion {
  tempId: string;
  content: string;
  type: QuestionType;
  score: number;
  options: { key: string; text: string }[];
  singleCorrectKey: string;
  multiCorrectKeys: Set<string>;
  text_answer_hint: string;
}

@Component({
  selector: 'app-training-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NzButtonModule,
    NzCardModule,
    NzCollapseModule,
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
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './training-management.component.html',
  styleUrl: './training-management.component.scss',
})
export class TrainingManagementComponent implements OnInit {
  private readonly trainingService = inject(TrainingService);
  private readonly fb = inject(FormBuilder);
  private readonly message = inject(NzMessageService);
  private readonly cdr = inject(ChangeDetectorRef);

  // ── State signals ──────────────────────────────────────────────────────────

  protected readonly roadmaps = signal<Roadmap[]>([]);
  protected readonly isLoading = signal<boolean>(false);
  protected readonly searchQuery = signal<string>('');
  protected readonly statusFilter = signal<RoadmapStatus | ''>('');

  protected readonly selectedRoadmap = signal<Roadmap | null>(null);
  protected readonly selectedRoadmapDetail = signal<RoadmapDetail | null>(null);
  protected readonly isDetailLoading = signal<boolean>(false);

  /** Map of roadmapId → phase count */
  protected readonly phaseCounts = signal<Record<string, number>>({});

  /** Map of phaseId → Quiz[] fetched on demand */
  protected readonly quizzesByPhase = signal<Record<string, Quiz[]>>({});

  protected readonly selectedQuiz = signal<Quiz | null>(null);
  protected readonly questionViewMode = signal<'list' | 'form'>('list');
  protected readonly questions = signal<Question[]>([]);
  protected readonly isQuestionsLoading = signal<boolean>(false);

  protected readonly isSaving = signal<boolean>(false);

  protected readonly expandedPhaseId = signal<string | null>(null);

  private searchDebounceTimer?: ReturnType<typeof setTimeout>;

  // ── Computed ───────────────────────────────────────────────────────────────

  protected readonly filteredRoadmaps = computed(() => {
    const q = this.searchQuery().trim().toLowerCase();
    const status = this.statusFilter();
    let list = this.roadmaps();
    if (status) {
      list = list.filter((r) => r.status === status);
    }
    if (q) {
      list = list.filter((r) => r.name.toLowerCase().includes(q));
    }
    return list;
  });

  // ── Modal visibility ───────────────────────────────────────────────────────

  protected isRoadmapModalVisible = false;
  protected readonly editingRoadmap = signal<Roadmap | null>(null);

  protected isPhaseModalVisible = false;
  protected readonly editingPhase = signal<Phase | null>(null);
  private pendingPhaseRoadmapId = '';

  protected isContentModalVisible = false;
  protected readonly editingContent = signal<LearningContent | null>(null);
  private pendingContentPhaseId = '';
  /** Files newly selected by the user (not yet uploaded) */
  protected readonly resourceFiles = signal<File[]>([]);
  /** URLs already saved on the server (from existing content or just uploaded) */
  protected readonly resourceUrls = signal<string[]>([]);
  protected readonly isUploadingFiles = signal<boolean>(false);

  protected isQuizModalVisible = false;
  protected readonly editingQuiz = signal<Quiz | null>(null);
  protected quizDraftQuestions: DraftQuestion[] = [];
  private pendingQuizPhaseId = '';

  protected isQuestionModalVisible = false;
  protected readonly editingQuestion = signal<Question | null>(null);

  /** State for the option builder in the question modal */
  protected choiceOptions: { key: string; text: string }[] = [];
  protected singleCorrectKey = '';
  protected multiCorrectKeys = new Set<string>();

  private static readonly OPTION_KEYS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

  // ── Forms ──────────────────────────────────────────────────────────────────

  protected readonly roadmapForm = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(3)]],
    description: [''],
    status: ['DRAFT' as RoadmapStatus, [Validators.required]],
  });

  protected readonly phaseForm = this.fb.group({
    name: ['', [Validators.required]],
    description: [''],
    order_no: [1, [Validators.required, Validators.min(1)]],
  });

  protected readonly contentForm = this.fb.group({
    title: ['', [Validators.required]],
    type: ['LESSON' as ContentType, [Validators.required]],
    description: [''],
    content: [''],
    resource_url: [''],
    order_no: [1, [Validators.required, Validators.min(1)]],
  });

  protected readonly quizForm = this.fb.group({
    title: ['', [Validators.required]],
    description: [''],
    duration_minutes: [30, [Validators.required, Validators.min(1)]],
    pass_score: [60, [Validators.required, Validators.min(0), Validators.max(100)]],
    max_attempts: [3, [Validators.required, Validators.min(1)]],
  });

  protected readonly questionForm = this.fb.group({
    content: ['', [Validators.required]],
    type: ['SINGLE_CHOICE' as QuestionType, [Validators.required]],
    score: [10, [Validators.required, Validators.min(0)]],
    order_no: [1, [Validators.required, Validators.min(1)]],
    text_answer_hint: [''],
  });

  // ── Lifecycle ──────────────────────────────────────────────────────────────

  ngOnInit(): void {
    this.loadRoadmaps();
  }

  // ── Roadmap methods ────────────────────────────────────────────────────────

  loadRoadmaps(): void {
    this.isLoading.set(true);
    this.trainingService.getRoadmaps(this.searchQuery(), this.statusFilter()).subscribe({
      next: (data) => {
        this.roadmaps.set(data);
        this.isLoading.set(false);

        // Update phaseCounts map with backend values
        const currentCounts = { ...this.phaseCounts() };
        data.forEach((r) => {
          if (r.phase_count !== undefined) {
            currentCounts[r.id] = r.phase_count;
          }
        });
        this.phaseCounts.set(currentCounts);

        // Refresh selected roadmap detail if one is open
        const current = this.selectedRoadmap();
        if (current) {
          const updated = data.find((r) => r.id === current.id);
          if (updated) {
            this.selectedRoadmap.set(updated);
          }
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Không thể tải danh sách Roadmap.');
        this.isLoading.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  onSearchChange(value: string): void {
    this.searchQuery.set(value);
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
    this.searchDebounceTimer = setTimeout(() => this.loadRoadmaps(), 300);
  }

  onStatusFilterChange(value: RoadmapStatus | ''): void {
    this.statusFilter.set(value);
    this.loadRoadmaps();
  }

  selectRoadmap(rm: Roadmap): void {
    if (this.selectedRoadmap()?.id === rm.id) {
      // Toggle off
      this.selectedRoadmap.set(null);
      this.selectedRoadmapDetail.set(null);
      this.selectedQuiz.set(null);
      this.questions.set([]);
      return;
    }
    this.selectedRoadmap.set(rm);
    this.selectedQuiz.set(null);
    this.questions.set([]);
    this.loadRoadmapDetail(rm.id);
  }

  loadRoadmapDetail(id: string): void {
    this.isDetailLoading.set(true);
    this.trainingService.getRoadmap(id).subscribe({
      next: (detail) => {
        this.selectedRoadmapDetail.set(detail);
        this.isDetailLoading.set(false);

        // Update phase count for this roadmap
        this.phaseCounts.update((m) => ({ ...m, [id]: detail.phases.length }));

        // Load quizzes for each phase
        detail.phases.forEach((phase) => this.loadPhaseQuizzes(phase.id));
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Không thể tải chi tiết Roadmap.');
        this.isDetailLoading.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  getRoadmapPhaseCount(roadmapId: string): number {
    // 1. Check phaseCounts map (always maintained)
    const cached = this.phaseCounts()[roadmapId];
    if (cached !== undefined) {
      return cached;
    }
    // 2. Check selected detail
    const detail = this.selectedRoadmapDetail();
    if (detail?.id === roadmapId) {
      return detail.phases.length;
    }
    // 3. Fallback to roadmap object property
    const rm = this.roadmaps().find((r) => r.id === roadmapId);
    return rm?.phase_count ?? 0;
  }

  openCreateRoadmapModal(): void {
    this.editingRoadmap.set(null);
    this.roadmapForm.reset({ name: '', description: '', status: 'DRAFT' });
    this.isRoadmapModalVisible = true;
  }

  openEditRoadmapModal(rm: Roadmap): void {
    this.editingRoadmap.set(rm);
    this.roadmapForm.patchValue({
      name: rm.name,
      description: rm.description ?? '',
      status: rm.status,
    });
    this.isRoadmapModalVisible = true;
  }

  closeRoadmapModal(): void {
    this.isRoadmapModalVisible = false;
  }

  saveRoadmap(): void {
    if (this.roadmapForm.invalid) {
      this.roadmapForm.markAllAsTouched();
      return;
    }
    const val = this.roadmapForm.value;
    const payload = {
      name: val.name!,
      description: val.description || null,
      status: val.status as RoadmapStatus,
    };
    this.isSaving.set(true);
    const editing = this.editingRoadmap();
    const op$ = editing
      ? this.trainingService.updateRoadmap(editing.id, payload)
      : this.trainingService.createRoadmap(payload);

    op$.subscribe({
      next: () => {
        this.message.success(editing ? 'Cập nhật Roadmap thành công!' : 'Tạo Roadmap thành công!');
        this.isSaving.set(false);
        this.isRoadmapModalVisible = false;
        this.loadRoadmaps();
        if (editing && this.selectedRoadmap()?.id === editing.id) {
          this.loadRoadmapDetail(editing.id);
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Thao tác thất bại. Vui lòng thử lại.');
        this.isSaving.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  deleteRoadmap(id: string): void {
    this.trainingService.deleteRoadmap(id).subscribe({
      next: () => {
        this.message.success('Đã xóa Roadmap.');
        if (this.selectedRoadmap()?.id === id) {
          this.selectedRoadmap.set(null);
          this.selectedRoadmapDetail.set(null);
          this.selectedQuiz.set(null);
          this.questions.set([]);
        }
        this.loadRoadmaps();
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Xóa Roadmap thất bại.');
        this.cdr.markForCheck();
      },
    });
  }

  // ── Phase methods ──────────────────────────────────────────────────────────

  onPhaseExpand(active: boolean, phaseId: string): void {
    this.expandedPhaseId.set(active ? phaseId : null);
    if (active) {
      this.loadPhaseQuizzes(phaseId);
    }
  }

  openCreatePhaseModal(): void {
    const detail = this.selectedRoadmapDetail();
    if (!detail) return;
    this.pendingPhaseRoadmapId = detail.id;
    this.editingPhase.set(null);
    const nextOrder = (detail.phases.length ?? 0) + 1;
    this.phaseForm.reset({ name: '', description: '', order_no: nextOrder });
    this.isPhaseModalVisible = true;
  }

  openEditPhaseModal(phase: Phase): void {
    this.editingPhase.set(phase);
    this.phaseForm.patchValue({
      name: phase.name,
      description: phase.description ?? '',
      order_no: phase.order_no,
    });
    this.isPhaseModalVisible = true;
  }

  closePhaseModal(): void {
    this.isPhaseModalVisible = false;
  }

  savePhase(): void {
    if (this.phaseForm.invalid) {
      this.phaseForm.markAllAsTouched();
      return;
    }
    const val = this.phaseForm.value;
    this.isSaving.set(true);
    const editing = this.editingPhase();
    const op$ = editing
      ? this.trainingService.updatePhase(editing.id, {
          name: val.name!,
          description: val.description || null,
          order_no: Number(val.order_no),
        })
      : this.trainingService.createPhase({
          roadmap_id: this.pendingPhaseRoadmapId,
          name: val.name!,
          description: val.description || null,
          order_no: Number(val.order_no),
        });

    op$.subscribe({
      next: () => {
        this.message.success(editing ? 'Cập nhật Phase thành công!' : 'Thêm Phase thành công!');
        this.isSaving.set(false);
        this.isPhaseModalVisible = false;
        const detail = this.selectedRoadmapDetail();
        if (detail) this.loadRoadmapDetail(detail.id);
        this.loadRoadmaps();
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Thao tác thất bại. Vui lòng thử lại.');
        this.isSaving.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  deletePhase(id: string): void {
    this.trainingService.deletePhase(id).subscribe({
      next: () => {
        this.message.success('Đã xóa Phase.');
        const detail = this.selectedRoadmapDetail();
        if (detail) this.loadRoadmapDetail(detail.id);
        this.loadRoadmaps();
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Xóa Phase thất bại.');
        this.cdr.markForCheck();
      },
    });
  }

  // ── Content methods ────────────────────────────────────────────────────────

  openCreateContentModal(phaseId: string): void {
    this.pendingContentPhaseId = phaseId;
    this.editingContent.set(null);
    this.resourceFiles.set([]);
    this.resourceUrls.set([]);
    this.contentForm.reset({
      title: '',
      type: 'LESSON',
      description: '',
      content: '',
      resource_url: '',
      order_no: 1,
    });
    this.isContentModalVisible = true;
  }

  openEditContentModal(c: LearningContent): void {
    this.editingContent.set(c);
    this.resourceFiles.set([]);
    // Parse existing resource_url: may be JSON array or single URL
    let existingUrls: string[] = [];
    if (c.resource_url) {
      try {
        const parsed = JSON.parse(c.resource_url) as unknown;
        existingUrls = Array.isArray(parsed) ? (parsed as string[]) : [c.resource_url];
      } catch {
        existingUrls = [c.resource_url];
      }
    }
    this.resourceUrls.set(existingUrls);
    this.contentForm.patchValue({
      title: c.title,
      type: c.type,
      description: c.description ?? '',
      content: c.content ?? '',
      resource_url: '',
      order_no: c.order_no,
    });
    this.isContentModalVisible = true;
  }

  closeContentModal(): void {
    this.isContentModalVisible = false;
    this.resourceFiles.set([]);
    this.resourceUrls.set([]);
  }

  /** Called when user picks files via the hidden input */
  onContentFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files) return;
    const newFiles = Array.from(input.files);
    this.resourceFiles.update((existing) => [...existing, ...newFiles]);
    // Reset the input so the same file can be selected again if removed
    input.value = '';
    this.cdr.markForCheck();
  }

  removeSelectedFile(index: number): void {
    this.resourceFiles.update((files) => files.filter((_, i) => i !== index));
    this.cdr.markForCheck();
  }

  removeResourceUrl(index: number): void {
    this.resourceUrls.update((urls) => urls.filter((_, i) => i !== index));
    this.cdr.markForCheck();
  }

  saveContent(): void {
    if (this.contentForm.invalid) {
      this.contentForm.markAllAsTouched();
      return;
    }

    const doSave = (allUrls: string[]) => {
      const val = this.contentForm.value;
      const editing = this.editingContent();
      const resourceUrlValue = allUrls.length > 0 ? JSON.stringify(allUrls) : null;
      const op$ = editing
        ? this.trainingService.updateContent(editing.id, {
            title: val.title!,
            type: val.type as ContentType,
            description: val.description || null,
            content: val.content || null,
            resource_url: resourceUrlValue,
            order_no: Number(val.order_no),
          })
        : this.trainingService.createContent({
            phase_id: this.pendingContentPhaseId,
            title: val.title!,
            type: val.type as ContentType,
            description: val.description || null,
            content: val.content || null,
            resource_url: resourceUrlValue,
            order_no: Number(val.order_no),
          });

      op$.subscribe({
        next: () => {
          this.message.success(
            editing ? 'Cập nhật nội dung thành công!' : 'Thêm nội dung thành công!',
          );
          this.isSaving.set(false);
          this.isUploadingFiles.set(false);
          this.isContentModalVisible = false;
          this.resourceFiles.set([]);
          this.resourceUrls.set([]);
          const detail = this.selectedRoadmapDetail();
          if (detail) this.loadRoadmapDetail(detail.id);
          this.cdr.markForCheck();
        },
        error: () => {
          this.message.error('Thao tác thất bại. Vui lòng thử lại.');
          this.isSaving.set(false);
          this.isUploadingFiles.set(false);
          this.cdr.markForCheck();
        },
      });
    };

    const newFiles = this.resourceFiles();
    const existingUrls = this.resourceUrls();

    if (newFiles.length > 0) {
      this.isSaving.set(true);
      this.isUploadingFiles.set(true);
      this.trainingService.uploadFiles(newFiles).subscribe({
        next: (result) => {
          this.isUploadingFiles.set(false);
          doSave([...existingUrls, ...result.urls]);
        },
        error: () => {
          this.message.error('Tải lên tệp thất bại. Vui lòng thử lại.');
          this.isSaving.set(false);
          this.isUploadingFiles.set(false);
          this.cdr.markForCheck();
        },
      });
    } else {
      this.isSaving.set(true);
      doSave(existingUrls);
    }
  }

  deleteContent(id: string, phaseId?: string): void {
    this.trainingService.deleteContent(id).subscribe({
      next: () => {
        this.message.success('Đã xóa nội dung.');
        const detail = this.selectedRoadmapDetail();
        if (detail) {
          this.loadRoadmapDetail(detail.id);
        } else if (phaseId) {
          this.loadPhaseQuizzes(phaseId);
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Xóa nội dung thất bại.');
        this.cdr.markForCheck();
      },
    });
  }

  // ── Quiz methods ───────────────────────────────────────────────────────────

  loadPhaseQuizzes(phaseId: string): void {
    this.trainingService.getQuizzes(phaseId).subscribe({
      next: (quizzes) => {
        this.quizzesByPhase.update((map) => ({ ...map, [phaseId]: quizzes }));
        this.cdr.markForCheck();
      },
      error: () => {
        // Silently fail — quizzes section will just be empty
      },
    });
  }

  getPhaseQuizzes(phaseId: string): Quiz[] {
    return this.quizzesByPhase()[phaseId] ?? [];
  }

  /** Parse resource_url which may be a JSON array string or a legacy single URL */
  parseResourceUrls(resourceUrl: string | null): string[] {
    if (!resourceUrl) return [];
    try {
      const parsed = JSON.parse(resourceUrl) as unknown;
      return Array.isArray(parsed) ? (parsed as string[]) : [resourceUrl];
    } catch {
      return [resourceUrl];
    }
  }

  getFileNameFromUrl(url: string): string {
    return url.split('/').pop() ?? url;
  }

  createBlankDraftQuestion(): DraftQuestion {
    return {
      tempId: 'draft_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7),
      content: '',
      type: 'SINGLE_CHOICE',
      score: 10,
      options: [
        { key: 'A', text: '' },
        { key: 'B', text: '' },
        { key: 'C', text: '' },
        { key: 'D', text: '' },
      ],
      singleCorrectKey: 'A',
      multiCorrectKeys: new Set(['A']),
      text_answer_hint: '',
    };
  }

  addDraftQuestion(): void {
    this.quizDraftQuestions.push(this.createBlankDraftQuestion());
    this.cdr.markForCheck();
  }

  removeDraftQuestion(index: number): void {
    this.quizDraftQuestions.splice(index, 1);
    this.cdr.markForCheck();
  }

  onDraftQuestionTypeChange(dq: DraftQuestion): void {
    if (dq.type === 'TRUE_FALSE') {
      dq.options = [
        { key: 'A', text: 'Đúng' },
        { key: 'B', text: 'Sai' },
      ];
      dq.singleCorrectKey = 'A';
      dq.multiCorrectKeys = new Set(['A']);
    } else if (dq.type === 'TEXT') {
      dq.options = [];
      dq.singleCorrectKey = '';
      dq.multiCorrectKeys.clear();
    } else {
      if (dq.options.length < 2) {
        dq.options = [
          { key: 'A', text: '' },
          { key: 'B', text: '' },
          { key: 'C', text: '' },
          { key: 'D', text: '' },
        ];
        dq.singleCorrectKey = 'A';
        dq.multiCorrectKeys = new Set(['A']);
      }
    }
    this.cdr.markForCheck();
  }

  addDraftQuestionOption(dq: DraftQuestion): void {
    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    if (dq.options.length >= letters.length) return;
    const nextKey = letters[dq.options.length];
    dq.options.push({ key: nextKey, text: '' });
    this.cdr.markForCheck();
  }

  removeDraftQuestionOption(dq: DraftQuestion, optIndex: number): void {
    if (dq.options.length <= 2) {
      this.message.warning('Câu hỏi trắc nghiệm cần có ít nhất 2 lựa chọn.');
      return;
    }
    const removedKey = dq.options[optIndex].key;
    dq.options.splice(optIndex, 1);
    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    dq.options.forEach((opt, idx) => {
      opt.key = letters[idx];
    });
    if (
      dq.singleCorrectKey === removedKey ||
      !dq.options.some((o) => o.key === dq.singleCorrectKey)
    ) {
      dq.singleCorrectKey = dq.options[0]?.key ?? 'A';
    }
    dq.multiCorrectKeys.delete(removedKey);
    if (dq.multiCorrectKeys.size === 0 && dq.options.length > 0) {
      dq.multiCorrectKeys.add(dq.options[0].key);
    }
    this.cdr.markForCheck();
  }

  toggleDraftQuestionMultiCorrect(dq: DraftQuestion, key: string): void {
    if (dq.multiCorrectKeys.has(key)) {
      if (dq.multiCorrectKeys.size === 1) {
        this.message.warning('Cần chọn ít nhất 1 đáp án đúng.');
        return;
      }
      dq.multiCorrectKeys.delete(key);
    } else {
      dq.multiCorrectKeys.add(key);
    }
    this.cdr.markForCheck();
  }

  openQuestionsFromEditModal(quiz: Quiz): void {
    this.isQuizModalVisible = false;
    this.selectQuizForQuestions(quiz);
  }

  openCreateQuizModal(phaseId: string): void {
    this.pendingQuizPhaseId = phaseId;
    this.editingQuiz.set(null);
    this.quizForm.reset({
      title: '',
      description: '',
      duration_minutes: 30,
      pass_score: 60,
      max_attempts: 3,
    });
    this.quizDraftQuestions = [this.createBlankDraftQuestion()];
    this.isQuizModalVisible = true;
    this.cdr.markForCheck();
  }

  openEditQuizModal(quiz: Quiz): void {
    this.editingQuiz.set(quiz);
    this.quizForm.patchValue({
      title: quiz.title,
      description: quiz.description ?? '',
      duration_minutes: quiz.duration_minutes,
      pass_score: quiz.pass_score,
      max_attempts: quiz.max_attempts,
    });
    this.quizDraftQuestions = [];
    this.isQuizModalVisible = true;
    this.cdr.markForCheck();
  }

  closeQuizModal(): void {
    this.isQuizModalVisible = false;
    this.quizDraftQuestions = [];
  }

  saveQuiz(): void {
    if (this.quizForm.invalid) {
      this.quizForm.markAllAsTouched();
      this.message.warning('Vui lòng điền đầy đủ thông tin bài kiểm tra.');
      return;
    }
    const val = this.quizForm.value;
    const editing = this.editingQuiz();

    // Lọc các câu hỏi nháp có nội dung
    const activeDrafts = !editing
      ? this.quizDraftQuestions.filter((q) => q.content && q.content.trim().length > 0)
      : [];

    // Kiểm tra tính hợp lệ của từng câu hỏi nháp
    for (let i = 0; i < activeDrafts.length; i++) {
      const dq = activeDrafts[i];
      const qNum = i + 1;
      if (dq.type === 'TRUE_FALSE') {
        if (!dq.singleCorrectKey) {
          this.message.warning(`Câu hỏi ${qNum}: Vui lòng chọn đáp án Đúng hoặc Sai.`);
          return;
        }
      } else if (dq.type === 'SINGLE_CHOICE' || dq.type === 'MULTIPLE_CHOICE') {
        if (dq.options.length < 2) {
          this.message.warning(`Câu hỏi ${qNum}: Cần có ít nhất 2 lựa chọn.`);
          return;
        }
        const emptyOpt = dq.options.find((o) => !o.text.trim());
        if (emptyOpt) {
          this.message.warning(
            `Câu hỏi ${qNum}: Vui lòng nhập nội dung cho lựa chọn ${emptyOpt.key}.`,
          );
          return;
        }
        if (dq.type === 'SINGLE_CHOICE' && !dq.singleCorrectKey) {
          this.message.warning(`Câu hỏi ${qNum}: Vui lòng chọn 1 đáp án đúng.`);
          return;
        }
        if (dq.type === 'MULTIPLE_CHOICE' && dq.multiCorrectKeys.size === 0) {
          this.message.warning(`Câu hỏi ${qNum}: Vui lòng chọn ít nhất 1 đáp án đúng.`);
          return;
        }
      }
    }

    this.isSaving.set(true);

    if (editing) {
      this.trainingService
        .updateQuiz(editing.id, {
          title: val.title!,
          description: val.description || null,
          duration_minutes: Number(val.duration_minutes),
          pass_score: Number(val.pass_score),
          max_attempts: Number(val.max_attempts),
        })
        .subscribe({
          next: () => {
            this.message.success('Cập nhật bài kiểm tra thành công!');
            this.isSaving.set(false);
            this.isQuizModalVisible = false;
            this.loadPhaseQuizzes(editing.phase_id);
            this.cdr.markForCheck();
          },
          error: (err) => {
            console.error('Error updating quiz:', err);
            this.message.error('Cập nhật bài kiểm tra thất bại.');
            this.isSaving.set(false);
            this.cdr.markForCheck();
          },
        });
    } else {
      const phaseId = this.pendingQuizPhaseId;
      this.trainingService
        .createQuiz({
          phase_id: phaseId,
          title: val.title!,
          description: val.description || null,
          duration_minutes: Number(val.duration_minutes),
          pass_score: Number(val.pass_score),
          max_attempts: Number(val.max_attempts),
        })
        .subscribe({
          next: (newQuiz) => {
            this.loadPhaseQuizzes(phaseId);

            if (activeDrafts.length === 0) {
              this.message.success('Tạo bài kiểm tra thành công!');
              this.isSaving.set(false);
              this.isQuizModalVisible = false;
              this.cdr.markForCheck();
              return;
            }

            // Gửi các câu hỏi nháp lên server
            const questionObservables = activeDrafts.map((dq, idx) => {
              let optionsPayload: unknown;
              let correctAnswerPayload: unknown;

              if (dq.type === 'TRUE_FALSE') {
                optionsPayload = [
                  { key: 'A', text: 'Đúng' },
                  { key: 'B', text: 'Sai' },
                ];
                correctAnswerPayload = [dq.singleCorrectKey];
              } else if (dq.type === 'SINGLE_CHOICE') {
                optionsPayload = dq.options.map((o) => ({ key: o.key, text: o.text.trim() }));
                correctAnswerPayload = [dq.singleCorrectKey];
              } else if (dq.type === 'MULTIPLE_CHOICE') {
                optionsPayload = dq.options.map((o) => ({ key: o.key, text: o.text.trim() }));
                correctAnswerPayload = Array.from(dq.multiCorrectKeys);
              } else {
                // TEXT
                optionsPayload = null;
                correctAnswerPayload = dq.text_answer_hint?.trim()
                  ? [dq.text_answer_hint.trim()]
                  : [''];
              }

              return this.trainingService.createQuestion({
                quiz_id: newQuiz.id,
                content: dq.content.trim(),
                type: dq.type,
                options: optionsPayload,
                correct_answer: correctAnswerPayload,
                score: Number(dq.score) || 10,
                order_no: idx + 1,
              });
            });

            forkJoin(questionObservables).subscribe({
              next: () => {
                this.message.success(
                  `Tạo bài kiểm tra và ${activeDrafts.length} câu hỏi thành công!`,
                );
                this.isSaving.set(false);
                this.isQuizModalVisible = false;
                this.quizDraftQuestions = [];
                // Mở ngay modal quản lý câu hỏi để người dùng xem kết quả
                this.selectQuizForQuestions(newQuiz);
                this.cdr.markForCheck();
              },
              error: (err) => {
                console.error('Error saving drafted questions:', err);
                this.message.warning('Đã tạo bài kiểm tra, nhưng có lỗi khi lưu một số câu hỏi.');
                this.isSaving.set(false);
                this.isQuizModalVisible = false;
                this.quizDraftQuestions = [];
                this.selectQuizForQuestions(newQuiz);
                this.cdr.markForCheck();
              },
            });
          },
          error: (err) => {
            console.error('Error creating quiz:', err);
            const detail = err?.error?.detail;
            const msg = typeof detail === 'string' ? detail : 'Vui lòng thử lại.';
            this.message.error(`Tạo bài kiểm tra thất bại: ${msg}`);
            this.isSaving.set(false);
            this.cdr.markForCheck();
          },
        });
    }
  }

  deleteQuiz(id: string, phaseId: string): void {
    this.trainingService.deleteQuiz(id).subscribe({
      next: () => {
        this.message.success('Đã xóa Quiz.');
        if (this.selectedQuiz()?.id === id) {
          this.selectedQuiz.set(null);
          this.questions.set([]);
        }
        this.loadPhaseQuizzes(phaseId);
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Xóa Quiz thất bại.');
        this.cdr.markForCheck();
      },
    });
  }

  publishQuiz(id: string): void {
    this.trainingService.publishQuiz(id).subscribe({
      next: (updated) => {
        this.message.success('Đã phát hành thành công!');
        // Update in quizzesByPhase map
        this.quizzesByPhase.update((map) => {
          const newMap = { ...map };
          for (const phaseId of Object.keys(newMap)) {
            newMap[phaseId] = newMap[phaseId].map((q) => (q.id === updated.id ? updated : q));
          }
          return newMap;
        });
        if (this.selectedQuiz()?.id === id) {
          this.selectedQuiz.set(updated);
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Phát hành Quiz thất bại.');
        this.cdr.markForCheck();
      },
    });
  }

  // ── Question methods ───────────────────────────────────────────────────────

  selectQuizForQuestions(quiz: Quiz): void {
    if (this.selectedQuiz()?.id === quiz.id) {
      this.selectedQuiz.set(null);
      this.questionViewMode.set('list');
      this.questions.set([]);
      return;
    }
    this.selectedQuiz.set(quiz);
    this.questionViewMode.set('list');
    this.loadQuestions(quiz.id);
  }

  closeQuestionPanel(): void {
    this.selectedQuiz.set(null);
    this.questionViewMode.set('list');
    this.questions.set([]);
  }

  switchToListMode(): void {
    this.questionViewMode.set('list');
    this.editingQuestion.set(null);
    this.cdr.markForCheck();
  }

  loadQuestions(quizId: string): void {
    this.isQuestionsLoading.set(true);
    this.trainingService.getQuestions(quizId).subscribe({
      next: (data) => {
        this.questions.set(data);
        this.isQuestionsLoading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Không thể tải danh sách câu hỏi.');
        this.isQuestionsLoading.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  // ── Option builder handlers ────────────────────────────────────────────────

  addOption(): void {
    const nextIndex = this.choiceOptions.length;
    const key = TrainingManagementComponent.OPTION_KEYS[nextIndex] || `OPT${nextIndex + 1}`;
    this.choiceOptions.push({ key, text: '' });
  }

  removeOption(index: number): void {
    if (this.choiceOptions.length <= 2) {
      this.message.warning('Câu hỏi trắc nghiệm cần có ít nhất 2 lựa chọn.');
      return;
    }
    const removedKey = this.choiceOptions[index].key;
    this.choiceOptions.splice(index, 1);
    // Re-index keys A, B, C...
    this.choiceOptions.forEach((opt, idx) => {
      opt.key = TrainingManagementComponent.OPTION_KEYS[idx] || `OPT${idx + 1}`;
    });
    // Adjust correct answers
    if (this.singleCorrectKey === removedKey) {
      this.singleCorrectKey = this.choiceOptions[0]?.key || '';
    }
    this.multiCorrectKeys.delete(removedKey);
  }

  setSingleCorrect(key: string): void {
    this.singleCorrectKey = key;
  }

  toggleMultiCorrect(key: string): void {
    if (this.multiCorrectKeys.has(key)) {
      this.multiCorrectKeys.delete(key);
    } else {
      this.multiCorrectKeys.add(key);
    }
  }

  onQuestionTypeChange(type: QuestionType): void {
    if (type === 'TRUE_FALSE') {
      this.choiceOptions = [
        { key: 'A', text: 'Đúng' },
        { key: 'B', text: 'Sai' },
      ];
      this.singleCorrectKey = 'A';
      this.multiCorrectKeys = new Set(['A']);
    } else if (type === 'TEXT') {
      this.choiceOptions = [];
      this.singleCorrectKey = '';
      this.multiCorrectKeys.clear();
    } else {
      if (
        this.choiceOptions.length === 0 ||
        (this.choiceOptions.length === 2 && this.choiceOptions[0].text === 'Đúng')
      ) {
        this.initDefaultChoiceOptions();
      }
    }
    this.cdr.markForCheck();
  }

  private initDefaultChoiceOptions(): void {
    this.choiceOptions = [
      { key: 'A', text: '' },
      { key: 'B', text: '' },
      { key: 'C', text: '' },
      { key: 'D', text: '' },
    ];
    this.singleCorrectKey = 'A';
    this.multiCorrectKeys = new Set(['A']);
  }

  getQuestionOptionsList(options: unknown): { key: string; text: string }[] {
    if (!options) return [];
    if (Array.isArray(options)) {
      return options.map((item, idx) => {
        if (typeof item === 'object' && item !== null && 'key' in item) {
          const optObj = item as { key: unknown; text?: unknown };
          return { key: String(optObj.key), text: String(optObj.text ?? '') };
        }
        const key = TrainingManagementComponent.OPTION_KEYS[idx] || `OPT${idx + 1}`;
        if (typeof item === 'boolean') {
          return { key, text: item ? 'Đúng' : 'Sai' };
        }
        return { key, text: String(item) };
      });
    }
    if (typeof options === 'object') {
      return Object.entries(options as Record<string, unknown>).map(([k, v]) => ({
        key: k,
        text: String(v),
      }));
    }
    if (typeof options === 'string') {
      try {
        const parsed = JSON.parse(options);
        return this.getQuestionOptionsList(parsed);
      } catch {
        return options.split(',').map((part, idx) => {
          const trimmed = part.trim();
          const match = trimmed.match(/^([A-Za-z])[.:)]\s*(.*)$/);
          if (match) {
            return { key: match[1].toUpperCase(), text: match[2] };
          }
          const key = TrainingManagementComponent.OPTION_KEYS[idx] || `OPT${idx + 1}`;
          return { key, text: trimmed };
        });
      }
    }
    return [];
  }

  extractCorrectKeys(
    correctAnswer: unknown,
    optionsList?: { key: string; text: string }[],
  ): string[] {
    if (correctAnswer === null || correctAnswer === undefined || correctAnswer === '') return [];
    const rawItems: unknown[] = Array.isArray(correctAnswer) ? correctAnswer : [correctAnswer];

    const keys: string[] = [];
    for (const item of rawItems) {
      if (typeof item === 'object' && item !== null) {
        if ('key' in item) {
          keys.push(String((item as { key: unknown }).key));
        } else if ('keys' in item && Array.isArray((item as { keys: unknown[] }).keys)) {
          keys.push(...(item as { keys: unknown[] }).keys.map((k) => String(k)));
        }
      } else if (typeof item === 'boolean') {
        keys.push(item ? 'A' : 'B');
      } else {
        const str = String(item).trim();
        try {
          const parsed = JSON.parse(str);
          if (Array.isArray(parsed) || typeof parsed === 'object') {
            keys.push(...this.extractCorrectKeys(parsed, optionsList));
            continue;
          }
        } catch {
          // ignore non-json string
        }

        if (optionsList && optionsList.length > 0) {
          const byKey = optionsList.find((o) => o.key.toUpperCase() === str.toUpperCase());
          if (byKey) {
            keys.push(byKey.key);
            continue;
          }
          const byText = optionsList.find((o) => o.text.trim().toLowerCase() === str.toLowerCase());
          if (byText) {
            keys.push(byText.key);
            continue;
          }
        }

        if (/^[A-Za-z]$/.test(str)) {
          keys.push(str.toUpperCase());
        } else {
          const parts = str
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean);
          for (const p of parts) {
            if (optionsList && optionsList.length > 0) {
              const matched = optionsList.find(
                (o) =>
                  o.key.toUpperCase() === p.toUpperCase() ||
                  o.text.trim().toLowerCase() === p.toLowerCase(),
              );
              if (matched) {
                keys.push(matched.key);
                continue;
              }
            }
            if (/^[A-Za-z]$/.test(p)) {
              keys.push(p.toUpperCase());
            } else {
              keys.push(p);
            }
          }
        }
      }
    }
    return Array.from(new Set(keys));
  }

  formatCorrectAnswer(correctAnswer: unknown): string {
    const keys = this.extractCorrectKeys(correctAnswer);
    if (keys.length > 0) return keys.join(', ');
    if (typeof correctAnswer === 'string') return correctAnswer;
    return JSON.stringify(correctAnswer);
  }

  isOptionCorrect(q: Question, optionKey: string): boolean {
    const opts = this.getQuestionOptionsList(q.options);
    const keys = this.extractCorrectKeys(q.correct_answer, opts);
    return keys.includes(optionKey.toUpperCase());
  }

  openCreateQuestionModal(): void {
    this.editingQuestion.set(null);
    const nextOrder = this.questions().length + 1;
    this.questionForm.reset({
      content: '',
      type: 'SINGLE_CHOICE',
      score: 10,
      order_no: nextOrder,
      text_answer_hint: '',
    });
    this.initDefaultChoiceOptions();
    this.questionViewMode.set('form');
    this.cdr.markForCheck();
  }

  openEditQuestionModal(q: Question): void {
    this.editingQuestion.set(q);
    const type = (q.type || 'SINGLE_CHOICE') as QuestionType;
    this.questionForm.reset({
      content: q.content,
      type: type,
      score: q.score !== null && q.score !== undefined ? Number(q.score) : 10,
      order_no: q.order_no || 1,
      text_answer_hint: type === 'TEXT' ? this.formatCorrectAnswer(q.correct_answer) : '',
    });

    if (type === 'TRUE_FALSE') {
      this.choiceOptions = [
        { key: 'A', text: 'Đúng' },
        { key: 'B', text: 'Sai' },
      ];
      const correctKeys = this.extractCorrectKeys(q.correct_answer, this.choiceOptions);
      this.singleCorrectKey = correctKeys[0] || 'A';
      this.multiCorrectKeys = new Set([this.singleCorrectKey]);
    } else if (type !== 'TEXT') {
      const parsedOptions = this.getQuestionOptionsList(q.options);
      if (parsedOptions.length > 0) {
        this.choiceOptions = parsedOptions.map((o) => ({ ...o }));
      } else {
        this.initDefaultChoiceOptions();
      }

      const correctKeys = this.extractCorrectKeys(q.correct_answer, this.choiceOptions);
      if (type === 'SINGLE_CHOICE') {
        this.singleCorrectKey = correctKeys[0] || (this.choiceOptions[0]?.key ?? 'A');
        this.multiCorrectKeys = new Set([this.singleCorrectKey]);
      } else {
        this.multiCorrectKeys = new Set(
          correctKeys.length > 0 ? correctKeys : [this.choiceOptions[0]?.key ?? 'A'],
        );
        this.singleCorrectKey = correctKeys[0] || (this.choiceOptions[0]?.key ?? 'A');
      }
    } else {
      this.choiceOptions = [];
      this.singleCorrectKey = '';
      this.multiCorrectKeys.clear();
    }

    this.questionViewMode.set('form');
    this.cdr.markForCheck();
  }

  closeQuestionModal(): void {
    this.questionViewMode.set('list');
    this.editingQuestion.set(null);
    this.cdr.markForCheck();
  }

  saveQuestion(): void {
    if (this.questionForm.invalid) {
      this.questionForm.markAllAsTouched();
      this.message.warning('Vui lòng điền đầy đủ các thông tin bắt buộc.');
      return;
    }
    const val = this.questionForm.value;
    const quiz = this.selectedQuiz();
    if (!quiz) {
      this.message.error('Không tìm thấy bài kiểm tra.');
      return;
    }

    let optionsPayload: unknown;
    let correctAnswerPayload: unknown;

    if (val.type === 'TRUE_FALSE') {
      if (!this.singleCorrectKey) {
        this.message.warning('Vui lòng chọn đáp án Đúng hoặc Sai.');
        return;
      }
      optionsPayload = [
        { key: 'A', text: 'Đúng' },
        { key: 'B', text: 'Sai' },
      ];
      correctAnswerPayload = [this.singleCorrectKey];
    } else if (val.type === 'SINGLE_CHOICE' || val.type === 'MULTIPLE_CHOICE') {
      const emptyOpt = this.choiceOptions.find((o) => !o.text.trim());
      if (emptyOpt) {
        this.message.warning(`Vui lòng nhập nội dung cho lựa chọn ${emptyOpt.key}.`);
        return;
      }
      if (this.choiceOptions.length < 2) {
        this.message.warning('Câu hỏi trắc nghiệm cần có ít nhất 2 lựa chọn.');
        return;
      }

      if (val.type === 'SINGLE_CHOICE') {
        if (!this.singleCorrectKey) {
          this.message.warning('Vui lòng chọn 1 đáp án đúng.');
          return;
        }
        correctAnswerPayload = [this.singleCorrectKey];
      } else {
        if (this.multiCorrectKeys.size === 0) {
          this.message.warning('Vui lòng chọn ít nhất 1 đáp án đúng.');
          return;
        }
        correctAnswerPayload = Array.from(this.multiCorrectKeys);
      }

      optionsPayload = this.choiceOptions.map((o) => ({ key: o.key, text: o.text.trim() }));
    } else {
      // TEXT
      optionsPayload = null;
      correctAnswerPayload = val.text_answer_hint?.trim() ? [val.text_answer_hint.trim()] : [''];
    }

    this.isSaving.set(true);
    const editing = this.editingQuestion();
    const op$ = editing
      ? this.trainingService.updateQuestion(editing.id, {
          content: val.content!,
          type: val.type as QuestionType,
          options: optionsPayload,
          correct_answer: correctAnswerPayload,
          score: Number(val.score),
          order_no: Number(val.order_no),
        })
      : this.trainingService.createQuestion({
          quiz_id: quiz.id,
          content: val.content!,
          type: val.type as QuestionType,
          options: optionsPayload,
          correct_answer: correctAnswerPayload,
          score: Number(val.score),
          order_no: Number(val.order_no),
        });

    op$.subscribe({
      next: () => {
        this.message.success(editing ? 'Cập nhật câu hỏi thành công!' : 'Thêm câu hỏi thành công!');
        this.isSaving.set(false);
        this.questionViewMode.set('list');
        this.loadQuestions(quiz.id);
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error saving question:', err);
        const detail = err?.error?.detail;
        const msg = typeof detail === 'string' ? detail : err?.message || 'Vui lòng thử lại.';
        this.message.error(`Thao tác thất bại: ${msg}`);
        this.isSaving.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  deleteQuestion(id: string): void {
    const quiz = this.selectedQuiz();
    if (!quiz) return;
    this.trainingService.deleteQuestion(id).subscribe({
      next: () => {
        this.message.success('Đã xóa câu hỏi.');
        this.loadQuestions(quiz.id);
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error deleting question:', err);
        const detail = err?.error?.detail;
        const msg = typeof detail === 'string' ? detail : err?.message || 'Vui lòng thử lại.';
        this.message.error(`Xóa câu hỏi thất bại: ${msg}`);
        this.cdr.markForCheck();
      },
    });
  }

  // ── Label / Color helpers ──────────────────────────────────────────────────

  getRoadmapStatusLabel(status: RoadmapStatus): string {
    const labels: Record<RoadmapStatus, string> = {
      DRAFT: 'Bản nháp',
      ACTIVE: 'Đang hoạt động',
      ARCHIVED: 'Lưu trữ',
    };
    return labels[status] ?? status;
  }

  getRoadmapStatusColor(status: RoadmapStatus): string {
    const colors: Record<RoadmapStatus, string> = {
      DRAFT: 'warning',
      ACTIVE: 'success',
      ARCHIVED: 'default',
    };
    return colors[status] ?? 'default';
  }

  getContentTypeLabel(type: ContentType): string {
    const labels: Record<ContentType, string> = {
      LESSON: 'Bài học',
      DOCUMENT: 'Tài liệu',
      VIDEO: 'Video',
      LINK: 'Liên kết',
    };
    return labels[type] ?? type;
  }

  getContentTypeColor(type: ContentType): string {
    const colors: Record<ContentType, string> = {
      LESSON: 'blue',
      DOCUMENT: 'purple',
      VIDEO: 'red',
      LINK: 'cyan',
    };
    return colors[type] ?? 'default';
  }

  getQuizStatusLabel(status: QuizStatus): string {
    const labels: Record<QuizStatus, string> = {
      DRAFT: 'Bản nháp',
      PUBLISHED: 'Đã phát hành',
    };
    return labels[status] ?? status;
  }

  getQuizStatusColor(status: QuizStatus): string {
    const colors: Record<QuizStatus, string> = {
      DRAFT: 'warning',
      PUBLISHED: 'success',
    };
    return colors[status] ?? 'default';
  }

  getQuestionTypeLabel(type: QuestionType): string {
    const labels: Record<string, string> = {
      SINGLE_CHOICE: 'Một đáp án',
      MULTIPLE_CHOICE: 'Nhiều đáp án',
      TRUE_FALSE: 'Đúng / Sai',
      TEXT: 'Tự luận',
    };
    return labels[type] ?? type;
  }

  getQuestionTypeColor(type: QuestionType): string {
    const colors: Record<string, string> = {
      SINGLE_CHOICE: 'blue',
      MULTIPLE_CHOICE: 'purple',
      TRUE_FALSE: 'cyan',
      TEXT: 'orange',
    };
    return colors[type] ?? 'default';
  }
}
