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
  template: `
    <div class="training-page">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-titles">
          <h2>Quản lý Đào tạo (LMS)</h2>
          <p>Tạo và quản lý Roadmap, Phase, nội dung học tập và bài kiểm tra.</p>
        </div>
        <button nz-button nzType="primary" (click)="openCreateRoadmapModal()">
          <span nz-icon nzType="plus"></span>
          Tạo Roadmap
        </button>
      </div>

      <!-- Roadmap List -->
      <nz-card [nzBordered]="false" class="main-card">
        <!-- Toolbar -->
        <div class="table-toolbar">
          <div class="search-box">
            <input
              type="text"
              nz-input
              placeholder="🔎 Tìm kiếm tên roadmap..."
              [ngModel]="searchQuery()"
              (ngModelChange)="onSearchChange($event)"
            />
          </div>
          <div class="filter-box">
            <span class="filter-label">Trạng thái:</span>
            <nz-select
              [ngModel]="statusFilter()"
              (ngModelChange)="onStatusFilterChange($event)"
              nzPlaceHolder="Tất cả"
              class="status-filter-select"
            >
              <nz-option nzValue="" nzLabel="Tất cả trạng thái"></nz-option>
              <nz-option nzValue="DRAFT" nzLabel="Bản nháp"></nz-option>
              <nz-option nzValue="ACTIVE" nzLabel="Đang hoạt động"></nz-option>
              <nz-option nzValue="ARCHIVED" nzLabel="Lưu trữ"></nz-option>
            </nz-select>
          </div>
        </div>

        <!-- Roadmap Content (Desktop Table + Mobile Cards) -->
        <nz-spin [nzSpinning]="isLoading()">
          <!-- 1. BẢNG DỮ LIỆU DESKTOP (> 768px) -->
          <div class="desktop-view">
            <nz-table
              #roadmapTable
              [nzData]="filteredRoadmaps()"
              [nzShowPagination]="true"
              [nzPageSize]="10"
            >
              <thead>
                <tr>
                  <th nzWidth="220px">Tên Roadmap</th>
                  <th class="col-desc">Mô tả</th>
                  <th nzWidth="130px">Trạng thái</th>
                  <th nzAlign="center" nzWidth="100px">Số Phase</th>
                  <th nzAlign="center" nzWidth="170px">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                @for (rm of roadmapTable.data; track rm.id) {
                  <tr [class.selected-row]="selectedRoadmap()?.id === rm.id">
                    <td>
                      <strong>{{ rm.name }}</strong>
                    </td>
                    <td class="col-desc">
                      <span class="desc-text">{{ rm.description || '—' }}</span>
                    </td>
                    <td>
                      <nz-tag [nzColor]="getRoadmapStatusColor(rm.status)">
                        {{ getRoadmapStatusLabel(rm.status) }}
                      </nz-tag>
                    </td>
                    <td nzAlign="center">
                      <span class="count-number">{{ getRoadmapPhaseCount(rm.id) }}</span>
                    </td>
                    <td nzAlign="center">
                      <div class="table-actions">
                        <!-- Dòng trên: Nút Quản lý / Chỉnh sửa Phase -->
                        <button
                          nz-button
                          nzType="default"
                          nzSize="small"
                          class="btn-manage-phase"
                          (click)="selectRoadmap(rm)"
                          [class.btn-active]="selectedRoadmap()?.id === rm.id"
                        >
                          <span nz-icon nzType="partition"></span>
                          <span>Quản lý Phase</span>
                        </button>
                        <!-- Dòng dưới: 2 nút Sửa và Xóa cùng một dòng -->
                        <div class="action-btn-pair">
                          <button
                            nz-button
                            nzType="text"
                            nzSize="small"
                            class="action-btn-edit"
                            (click)="openEditRoadmapModal(rm)"
                          >
                            <span nz-icon nzType="edit"></span>
                            Sửa
                          </button>
                          <button
                            nz-button
                            nzType="text"
                            nzSize="small"
                            nzDanger
                            class="action-btn-delete"
                            nz-popconfirm
                            nzPopconfirmTitle="Bạn có chắc muốn xóa roadmap này?"
                            nzOkText="Xóa"
                            nzCancelText="Hủy"
                            (nzOnConfirm)="deleteRoadmap(rm.id)"
                          >
                            <span nz-icon nzType="delete"></span>
                            Xóa
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                }
                @if (filteredRoadmaps().length === 0 && !isLoading()) {
                  <tr>
                    <td colspan="5" class="empty-cell">
                      <nz-empty
                        nzNotFoundContent="Chưa có Roadmap nào. Hãy tạo Roadmap đầu tiên!"
                      ></nz-empty>
                    </td>
                  </tr>
                }
              </tbody>
            </nz-table>
          </div>

          <!-- 2. DẠNG THẺ (CARD VIEW) TRÊN ĐIỆN THOẠI (<= 768px): HIỂN THỊ ĐẦY ĐỦ TRONG 1 KHUNG MÀN HÌNH -->
          <div class="mobile-view">
            @for (rm of filteredRoadmaps(); track rm.id) {
              <div
                class="roadmap-mobile-card"
                [class.roadmap-mobile-card--selected]="selectedRoadmap()?.id === rm.id"
                (click)="selectRoadmap(rm)"
              >
                <!-- Tiêu đề + Trạng thái -->
                <div class="card-top-row">
                  <div class="roadmap-title-area">
                    <span nz-icon nzType="read" class="roadmap-badge-icon"></span>
                    <strong class="roadmap-name">{{ rm.name }}</strong>
                  </div>
                  <nz-tag [nzColor]="getRoadmapStatusColor(rm.status)" class="status-tag">
                    {{ getRoadmapStatusLabel(rm.status) }}
                  </nz-tag>
                </div>

                <!-- Mô tả đầy đủ -->
                <div class="roadmap-desc-full">
                  {{ rm.description || 'Chưa có mô tả cho lộ trình đào tạo này.' }}
                </div>

                <!-- Thông số chi tiết: Số Phase + Ngày cập nhật -->
                <div class="roadmap-meta-grid">
                  <div class="meta-box">
                    <span class="meta-label">Số giai đoạn</span>
                    <span class="meta-value highlight">
                      <span nz-icon nzType="partition"></span>
                      {{ getRoadmapPhaseCount(rm.id) }} Phase
                    </span>
                  </div>
                  <div class="meta-box">
                    <span class="meta-label">Cập nhật</span>
                    <span class="meta-value">
                      {{ rm.updated_at || rm.created_at | date: 'dd/MM/yyyy' }}
                    </span>
                  </div>
                </div>

                <!-- Thao tác: Quản lý phase ở dòng trên + Sửa, Xóa ở dòng dưới -->
                <div class="roadmap-mobile-actions" (click)="$event.stopPropagation()">
                  <button
                    nz-button
                    [nzType]="selectedRoadmap()?.id === rm.id ? 'primary' : 'default'"
                    nzSize="small"
                    class="action-btn-main"
                    (click)="selectRoadmap(rm)"
                  >
                    <span nz-icon nzType="partition"></span>
                    <span>{{
                      selectedRoadmap()?.id === rm.id ? 'Đang chọn Phase' : 'Quản lý Phase'
                    }}</span>
                  </button>
                  <div class="action-btn-pair">
                    <button
                      nz-button
                      nzType="default"
                      nzSize="small"
                      class="action-btn-sub"
                      (click)="openEditRoadmapModal(rm)"
                    >
                      <span nz-icon nzType="edit"></span> Sửa
                    </button>
                    <button
                      nz-button
                      nzType="default"
                      nzDanger
                      nzSize="small"
                      class="action-btn-sub"
                      nz-popconfirm
                      nzPopconfirmTitle="Bạn có chắc muốn xóa roadmap này?"
                      nzOkText="Xóa"
                      nzCancelText="Hủy"
                      (nzOnConfirm)="deleteRoadmap(rm.id)"
                    >
                      <span nz-icon nzType="delete"></span> Xóa
                    </button>
                  </div>
                </div>
              </div>
            }
            @if (filteredRoadmaps().length === 0 && !isLoading()) {
              <div class="mobile-empty-state">
                <nz-empty
                  nzNotFoundContent="Chưa có Roadmap nào. Hãy tạo Roadmap đầu tiên!"
                ></nz-empty>
              </div>
            }
          </div>
        </nz-spin>
      </nz-card>

      <!-- Phase / Content / Quiz Panel -->
      @if (selectedRoadmapDetail(); as detail) {
        <nz-card
          [nzBordered]="false"
          class="phase-card"
          [nzTitle]="phaseCardTitle"
          [nzExtra]="phaseCardExtra"
        >
          <ng-template #phaseCardTitle>
            <div class="panel-header">
              <span nz-icon nzType="partition" class="panel-icon"></span>
              <span
                >Các Phase của Roadmap: <strong>{{ detail.name }}</strong></span
              >
              <nz-tag [nzColor]="getRoadmapStatusColor(detail.status)" style="margin-left: 8px;">
                {{ getRoadmapStatusLabel(detail.status) }}
              </nz-tag>
            </div>
          </ng-template>
          <ng-template #phaseCardExtra>
            <button nz-button nzType="primary" nzSize="small" (click)="openCreatePhaseModal()">
              <span nz-icon nzType="plus"></span>
              Thêm Phase
            </button>
          </ng-template>

          <!-- Roadmap Summary Banner -->
          <div class="roadmap-summary-banner">
            <div class="banner-desc">
              {{ detail.description || 'Chưa có mô tả cho lộ trình đào tạo này.' }}
            </div>
            <div class="banner-meta">
              <span>
                <span nz-icon nzType="partition"></span>
                <strong>{{ detail.phases.length }}</strong> giai đoạn (Phase)
              </span>
              <span>
                <span nz-icon nzType="clock-circle"></span>
                Cập nhật: {{ detail.updated_at || detail.created_at | date: 'dd/MM/yyyy' }}
              </span>
            </div>
          </div>

          <nz-spin [nzSpinning]="isDetailLoading()">
            @if (detail.phases.length === 0) {
              <nz-empty
                nzNotFoundContent="Roadmap này chưa có Phase nào. Hãy thêm Phase mới!"
              ></nz-empty>
            }
            <nz-collapse>
              @for (phase of detail.phases; track phase.id) {
                <nz-collapse-panel
                  [nzHeader]="phaseHeader"
                  [nzExtra]="phaseExtra"
                  [nzActive]="expandedPhaseId() === phase.id"
                  (nzActiveChange)="onPhaseExpand($event, phase.id)"
                >
                  <ng-template #phaseHeader>
                    <div class="phase-header-content">
                      <span class="phase-order-badge">Phase {{ phase.order_no }}</span>
                      <strong>{{ phase.name }}</strong>
                      @if (phase.description) {
                        <span class="phase-desc">— {{ phase.description }}</span>
                      }
                    </div>
                  </ng-template>
                  <ng-template #phaseExtra>
                    <div class="phase-actions" (click)="$event.stopPropagation()">
                      <button
                        nz-button
                        nzType="default"
                        nzSize="small"
                        (click)="openCreateContentModal(phase.id)"
                      >
                        <span nz-icon nzType="file-add"></span>
                        Thêm nội dung
                      </button>
                      <button
                        nz-button
                        nzType="default"
                        nzSize="small"
                        (click)="openCreateQuizModal(phase.id)"
                      >
                        <span nz-icon nzType="form"></span>
                        Thêm Quiz
                      </button>
                      <div class="action-btn-pair">
                        <button
                          nz-button
                          nzType="text"
                          nzSize="small"
                          (click)="openEditPhaseModal(phase)"
                        >
                          <span nz-icon nzType="edit"></span>
                        </button>
                        <button
                          nz-button
                          nzType="text"
                          nzSize="small"
                          nzDanger
                          nz-popconfirm
                          nzPopconfirmTitle="Bạn có chắc muốn xóa phase này?"
                          nzOkText="Xóa"
                          nzCancelText="Hủy"
                          (nzOnConfirm)="deletePhase(phase.id)"
                        >
                          <span nz-icon nzType="delete"></span>
                          Xóa phase
                        </button>
                      </div>
                    </div>
                  </ng-template>

                  <!-- Learning Contents -->
                  <div class="content-section">
                    <div class="section-subtitle">
                      <span nz-icon nzType="read"></span>
                      <strong>Nội dung học tập</strong>
                      <span class="section-count">({{ phase.contents.length }})</span>
                    </div>
                    @if (phase.contents.length === 0) {
                      <p class="empty-hint">Chưa có nội dung. Nhấn "Thêm nội dung" để bắt đầu.</p>
                    }
                    <nz-table
                      [nzData]="phase.contents"
                      [nzShowPagination]="false"
                      nzSize="small"
                      class="inner-table"
                      [nzScroll]="{ x: '580px' }"
                    >
                      <thead>
                        <tr>
                          <th nzWidth="60px">STT</th>
                          <th>Tiêu đề</th>
                          <th nzWidth="120px">Loại</th>
                          <th nzAlign="center" nzWidth="120px">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (content of phase.contents; track content.id) {
                          <tr>
                            <td>{{ content.order_no }}</td>
                            <td>
                              <strong>{{ content.title }}</strong>
                              @if (content.description) {
                                <br /><small class="desc-hint">{{ content.description }}</small>
                              }
                            </td>
                            <td>
                              <nz-tag [nzColor]="getContentTypeColor(content.type)">
                                {{ getContentTypeLabel(content.type) }}
                              </nz-tag>
                            </td>
                            <td nzAlign="center">
                              <div class="inner-actions">
                                <button
                                  nz-button
                                  nzType="text"
                                  nzSize="small"
                                  (click)="openEditContentModal(content)"
                                >
                                  <span nz-icon nzType="edit"></span>
                                </button>
                                <button
                                  nz-button
                                  nzType="text"
                                  nzSize="small"
                                  nzDanger
                                  nz-popconfirm
                                  nzPopconfirmTitle="Xóa nội dung này?"
                                  nzOkText="Xóa"
                                  nzCancelText="Hủy"
                                  (nzOnConfirm)="deleteContent(content.id, phase.id)"
                                >
                                  <span nz-icon nzType="delete"></span>
                                </button>
                              </div>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </nz-table>
                  </div>

                  <nz-divider></nz-divider>

                  <!-- Quizzes -->
                  <div class="quiz-section">
                    <div class="section-subtitle">
                      <span nz-icon nzType="form"></span>
                      <strong>Bài kiểm tra (Quiz)</strong>
                      <span class="section-count">({{ getPhaseQuizzes(phase.id).length }})</span>
                    </div>
                    @if (getPhaseQuizzes(phase.id).length === 0) {
                      <p class="empty-hint">Chưa có Quiz. Nhấn "Thêm Quiz" để tạo bài kiểm tra.</p>
                    }
                    <nz-table
                      [nzData]="getPhaseQuizzes(phase.id)"
                      [nzShowPagination]="false"
                      nzSize="small"
                      class="inner-table"
                      [nzScroll]="{ x: '680px' }"
                    >
                      <thead>
                        <tr>
                          <th>Tiêu đề Quiz</th>
                          <th nzWidth="100px">Thời gian</th>
                          <th nzWidth="100px">Điểm đạt</th>
                          <th nzWidth="120px">Trạng thái</th>
                          <th nzAlign="center" nzWidth="220px">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (quiz of getPhaseQuizzes(phase.id); track quiz.id) {
                          <tr [class.selected-row]="selectedQuiz()?.id === quiz.id">
                            <td>
                              <strong>{{ quiz.title }}</strong>
                            </td>
                            <td>{{ quiz.duration_minutes }} phút</td>
                            <td>{{ quiz.pass_score }}/100</td>
                            <td>
                              <nz-tag [nzColor]="getQuizStatusColor(quiz.status)">
                                {{ getQuizStatusLabel(quiz.status) }}
                              </nz-tag>
                            </td>
                            <td nzAlign="center">
                              <div class="inner-actions">
                                <button
                                  nz-button
                                  nzType="default"
                                  nzSize="small"
                                  (click)="selectQuizForQuestions(quiz)"
                                  [class.btn-active]="selectedQuiz()?.id === quiz.id"
                                >
                                  <span nz-icon nzType="unordered-list"></span>
                                  Câu hỏi
                                </button>
                                @if (quiz.status === 'DRAFT') {
                                  <button
                                    nz-button
                                    nzType="default"
                                    nzSize="small"
                                    nz-popconfirm
                                    nzPopconfirmTitle="Phát hành Quiz này? Sau khi phát hành sẽ không thể chỉnh sửa."
                                    nzOkText="Phát hành"
                                    nzCancelText="Hủy"
                                    (nzOnConfirm)="publishQuiz(quiz.id)"
                                  >
                                    <span nz-icon nzType="rocket"></span>
                                    Phát hành
                                  </button>
                                }
                                <div class="action-btn-pair">
                                  <button
                                    nz-button
                                    nzType="text"
                                    nzSize="small"
                                    (click)="openEditQuizModal(quiz)"
                                  >
                                    <span nz-icon nzType="edit"></span>
                                  </button>
                                  <button
                                    nz-button
                                    nzType="text"
                                    nzSize="small"
                                    nzDanger
                                    nz-popconfirm
                                    nzPopconfirmTitle="Xóa Quiz này?"
                                    nzOkText="Xóa"
                                    nzCancelText="Hủy"
                                    (nzOnConfirm)="deleteQuiz(quiz.id, phase.id)"
                                  >
                                    <span nz-icon nzType="delete"></span>
                                  </button>
                                </div>
                              </div>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </nz-table>
                  </div>
                </nz-collapse-panel>
              }
            </nz-collapse>
          </nz-spin>
        </nz-card>
      }

      <!-- Question Management Panel -->
      @if (selectedQuiz(); as quiz) {
        <nz-card
          [nzBordered]="false"
          class="question-card"
          [nzTitle]="questionCardTitle"
          [nzExtra]="questionCardExtra"
        >
          <ng-template #questionCardTitle>
            <div class="panel-header">
              <span nz-icon nzType="question-circle" class="panel-icon"></span>
              <span
                >Câu hỏi của Quiz: <strong>{{ quiz.title }}</strong></span
              >
              <nz-tag [nzColor]="getQuizStatusColor(quiz.status)" style="margin-left: 8px;">
                {{ getQuizStatusLabel(quiz.status) }}
              </nz-tag>
            </div>
          </ng-template>
          <ng-template #questionCardExtra>
            <div class="card-extra-actions">
              <button nz-button nzType="default" nzSize="small" (click)="closeQuestionPanel()">
                <span nz-icon nzType="close"></span>
                Đóng
              </button>
              <button nz-button nzType="primary" nzSize="small" (click)="openCreateQuestionModal()">
                <span nz-icon nzType="plus"></span>
                Thêm câu hỏi
              </button>
            </div>
          </ng-template>

          <nz-spin [nzSpinning]="isQuestionsLoading()">
            @if (questions().length === 0 && !isQuestionsLoading()) {
              <nz-empty nzNotFoundContent="Quiz này chưa có câu hỏi nào."></nz-empty>
            }
            <nz-table
              [nzData]="questions()"
              [nzShowPagination]="false"
              nzSize="small"
              [nzScroll]="{ x: '600px' }"
            >
              <thead>
                <tr>
                  <th nzWidth="60px">STT</th>
                  <th>Nội dung câu hỏi</th>
                  <th nzWidth="160px">Loại câu hỏi</th>
                  <th nzWidth="80px">Điểm</th>
                  <th nzAlign="center" nzWidth="120px">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                @for (q of questions(); track q.id) {
                  <tr>
                    <td>{{ q.order_no }}</td>
                    <td>
                      <strong>{{ q.content }}</strong>
                      @if (q.options) {
                        <br /><small class="desc-hint">Đáp án: {{ q.correct_answer }}</small>
                      }
                    </td>
                    <td>
                      <nz-tag [nzColor]="getQuestionTypeColor(q.type)">
                        {{ getQuestionTypeLabel(q.type) }}
                      </nz-tag>
                    </td>
                    <td>{{ q.score }}</td>
                    <td nzAlign="center">
                      <div class="inner-actions">
                        <button
                          nz-button
                          nzType="text"
                          nzSize="small"
                          (click)="openEditQuestionModal(q)"
                        >
                          <span nz-icon nzType="edit"></span>
                        </button>
                        <button
                          nz-button
                          nzType="text"
                          nzSize="small"
                          nzDanger
                          nz-popconfirm
                          nzPopconfirmTitle="Xóa câu hỏi này?"
                          nzOkText="Xóa"
                          nzCancelText="Hủy"
                          (nzOnConfirm)="deleteQuestion(q.id)"
                        >
                          <span nz-icon nzType="delete"></span>
                        </button>
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </nz-table>
          </nz-spin>
        </nz-card>
      }

      <!-- Modal: Tạo / Chỉnh sửa Roadmap -->
      <nz-modal
        [(nzVisible)]="isRoadmapModalVisible"
        [nzTitle]="editingRoadmap() ? 'Chỉnh sửa Roadmap' : 'Tạo Roadmap mới'"
        (nzOnCancel)="closeRoadmapModal()"
        (nzOnOk)="saveRoadmap()"
        [nzOkLoading]="isSaving()"
        nzOkText="Lưu"
        nzCancelText="Hủy"
        [nzWidth]="'min(540px, 94vw)'"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="roadmapForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Tên Roadmap</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng nhập tên Roadmap (tối thiểu 3 ký tự)">
                <input
                  nz-input
                  formControlName="name"
                  placeholder="Ví dụ: Lộ trình Frontend Developer"
                />
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label>Mô tả</nz-form-label>
              <nz-form-control>
                <textarea
                  nz-input
                  rows="3"
                  formControlName="description"
                  placeholder="Mô tả mục tiêu và nội dung của Roadmap..."
                ></textarea>
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label nzRequired>Trạng thái</nz-form-label>
              <nz-form-control>
                <nz-select formControlName="status">
                  <nz-option nzValue="DRAFT" nzLabel="Bản nháp (DRAFT)"></nz-option>
                  <nz-option nzValue="ACTIVE" nzLabel="Đang hoạt động (ACTIVE)"></nz-option>
                  <nz-option nzValue="ARCHIVED" nzLabel="Lưu trữ (ARCHIVED)"></nz-option>
                </nz-select>
              </nz-form-control>
            </nz-form-item>
          </form>
        </ng-container>
      </nz-modal>

      <!-- Modal: Tạo / Chỉnh sửa Phase -->
      <nz-modal
        [(nzVisible)]="isPhaseModalVisible"
        [nzTitle]="editingPhase() ? 'Chỉnh sửa Phase' : 'Thêm Phase mới'"
        (nzOnCancel)="closePhaseModal()"
        (nzOnOk)="savePhase()"
        [nzOkLoading]="isSaving()"
        nzOkText="Lưu"
        nzCancelText="Hủy"
        [nzWidth]="'min(540px, 94vw)'"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="phaseForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Tên Phase</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng nhập tên Phase">
                <input
                  nz-input
                  formControlName="name"
                  placeholder="Ví dụ: Phase 1: Kiến thức nền tảng"
                />
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label>Mô tả</nz-form-label>
              <nz-form-control>
                <textarea
                  nz-input
                  rows="2"
                  formControlName="description"
                  placeholder="Mô tả nội dung của Phase này..."
                ></textarea>
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label nzRequired>Thứ tự (Order)</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng nhập thứ tự phase (số nguyên dương)">
                <input nz-input type="number" formControlName="order_no" placeholder="1" min="1" />
              </nz-form-control>
            </nz-form-item>
          </form>
        </ng-container>
      </nz-modal>

      <!-- Modal: Tạo / Chỉnh sửa Nội dung -->
      <nz-modal
        [(nzVisible)]="isContentModalVisible"
        [nzTitle]="editingContent() ? 'Chỉnh sửa Nội dung' : 'Thêm Nội dung mới'"
        (nzOnCancel)="closeContentModal()"
        (nzOnOk)="saveContent()"
        [nzOkLoading]="isSaving()"
        nzOkText="Lưu"
        nzCancelText="Hủy"
        [nzWidth]="'min(600px, 94vw)'"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="contentForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Tiêu đề nội dung</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng nhập tiêu đề">
                <input
                  nz-input
                  formControlName="title"
                  placeholder="Ví dụ: Bài 1: Giới thiệu Angular"
                />
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label nzRequired>Loại nội dung</nz-form-label>
              <nz-form-control>
                <nz-select formControlName="type">
                  <nz-option nzValue="LESSON" nzLabel="Bài học (LESSON)"></nz-option>
                  <nz-option nzValue="DOCUMENT" nzLabel="Tài liệu (DOCUMENT)"></nz-option>
                  <nz-option nzValue="VIDEO" nzLabel="Video (VIDEO)"></nz-option>
                  <nz-option nzValue="LINK" nzLabel="Liên kết (LINK)"></nz-option>
                </nz-select>
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label>Mô tả</nz-form-label>
              <nz-form-control>
                <textarea
                  nz-input
                  rows="2"
                  formControlName="description"
                  placeholder="Mô tả ngắn về nội dung này..."
                ></textarea>
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label>Nội dung</nz-form-label>
              <nz-form-control>
                <textarea
                  nz-input
                  rows="4"
                  formControlName="content"
                  placeholder="Nhập nội dung chi tiết (Markdown hoặc HTML)..."
                ></textarea>
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label>URL tài nguyên</nz-form-label>
              <nz-form-control>
                <input nz-input formControlName="resource_url" placeholder="https://..." />
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label nzRequired>Thứ tự hiển thị</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng nhập thứ tự">
                <input nz-input type="number" formControlName="order_no" placeholder="1" min="1" />
              </nz-form-control>
            </nz-form-item>
          </form>
        </ng-container>
      </nz-modal>

      <!-- Modal: Tạo / Chỉnh sửa Quiz -->
      <nz-modal
        [(nzVisible)]="isQuizModalVisible"
        [nzTitle]="editingQuiz() ? 'Chỉnh sửa Quiz' : 'Thêm Quiz mới'"
        (nzOnCancel)="closeQuizModal()"
        (nzOnOk)="saveQuiz()"
        [nzOkLoading]="isSaving()"
        nzOkText="Lưu"
        nzCancelText="Hủy"
        [nzWidth]="'min(540px, 94vw)'"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="quizForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Tiêu đề Quiz</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng nhập tiêu đề Quiz">
                <input
                  nz-input
                  formControlName="title"
                  placeholder="Ví dụ: Kiểm tra cuối Phase 1"
                />
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label>Mô tả</nz-form-label>
              <nz-form-control>
                <textarea
                  nz-input
                  rows="2"
                  formControlName="description"
                  placeholder="Mô tả nội dung bài kiểm tra..."
                ></textarea>
              </nz-form-control>
            </nz-form-item>
            <div class="form-row">
              <nz-form-item class="form-col">
                <nz-form-label nzRequired>Thời gian (phút)</nz-form-label>
                <nz-form-control nzErrorTip="Nhập số phút (> 0)">
                  <input
                    nz-input
                    type="number"
                    formControlName="duration_minutes"
                    placeholder="30"
                    min="1"
                  />
                </nz-form-control>
              </nz-form-item>
              <nz-form-item class="form-col">
                <nz-form-label nzRequired>Điểm đạt (0-100)</nz-form-label>
                <nz-form-control nzErrorTip="Nhập điểm từ 0 đến 100">
                  <input
                    nz-input
                    type="number"
                    formControlName="pass_score"
                    placeholder="60"
                    min="0"
                    max="100"
                  />
                </nz-form-control>
              </nz-form-item>
              <nz-form-item class="form-col">
                <nz-form-label nzRequired>Số lần thử tối đa</nz-form-label>
                <nz-form-control nzErrorTip="Nhập số lần thử (≥ 1)">
                  <input
                    nz-input
                    type="number"
                    formControlName="max_attempts"
                    placeholder="3"
                    min="1"
                  />
                </nz-form-control>
              </nz-form-item>
            </div>
          </form>
        </ng-container>
      </nz-modal>

      <!-- Modal: Tạo / Chỉnh sửa Câu hỏi -->
      <nz-modal
        [(nzVisible)]="isQuestionModalVisible"
        [nzTitle]="editingQuestion() ? 'Chỉnh sửa Câu hỏi' : 'Thêm Câu hỏi mới'"
        (nzOnCancel)="closeQuestionModal()"
        (nzOnOk)="saveQuestion()"
        [nzOkLoading]="isSaving()"
        nzOkText="Lưu"
        nzCancelText="Hủy"
        [nzWidth]="'min(600px, 94vw)'"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="questionForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Nội dung câu hỏi</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng nhập nội dung câu hỏi">
                <textarea
                  nz-input
                  rows="3"
                  formControlName="content"
                  placeholder="Nhập câu hỏi tại đây..."
                ></textarea>
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label nzRequired>Loại câu hỏi</nz-form-label>
              <nz-form-control>
                <nz-select formControlName="type">
                  <nz-option
                    nzValue="SINGLE_CHOICE"
                    nzLabel="Một đáp án (SINGLE_CHOICE)"
                  ></nz-option>
                  <nz-option
                    nzValue="MULTIPLE_CHOICE"
                    nzLabel="Nhiều đáp án (MULTIPLE_CHOICE)"
                  ></nz-option>
                  <nz-option nzValue="TEXT" nzLabel="Tự luận (TEXT)"></nz-option>
                </nz-select>
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label>Các lựa chọn (phân cách bằng dấu phẩy hoặc JSON)</nz-form-label>
              <nz-form-control>
                <textarea
                  nz-input
                  rows="2"
                  formControlName="options"
                  placeholder='Ví dụ: "A. Option 1, B. Option 2, C. Option 3" hoặc JSON array'
                ></textarea>
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label>Đáp án đúng</nz-form-label>
              <nz-form-control>
                <input nz-input formControlName="correct_answer" placeholder="Ví dụ: A hoặc A,C" />
              </nz-form-control>
            </nz-form-item>
            <div class="form-row">
              <nz-form-item class="form-col">
                <nz-form-label nzRequired>Điểm</nz-form-label>
                <nz-form-control nzErrorTip="Nhập điểm (≥ 0)">
                  <input nz-input type="number" formControlName="score" placeholder="10" min="0" />
                </nz-form-control>
              </nz-form-item>
              <nz-form-item class="form-col">
                <nz-form-label nzRequired>Thứ tự</nz-form-label>
                <nz-form-control nzErrorTip="Nhập thứ tự (≥ 1)">
                  <input
                    nz-input
                    type="number"
                    formControlName="order_no"
                    placeholder="1"
                    min="1"
                  />
                </nz-form-control>
              </nz-form-item>
            </div>
          </form>
        </ng-container>
      </nz-modal>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        width: 100%;
        box-sizing: border-box;
      }

      .training-page {
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
        box-sizing: border-box;
      }

      .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #fff;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);

        .header-titles {
          h2 {
            margin: 0 0 2px;
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
          }
          p {
            margin: 0;
            font-size: 12.5px;
            color: #64748b;
          }
        }
      }

      .main-card,
      .phase-card,
      .question-card {
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        width: 100%;

        :ng-deep .ant-card-body {
          padding: 12px 16px !important;
        }

        :ng-deep .ant-card-head {
          padding: 0 16px !important;
          min-height: 46px !important;
        }
      }

      .table-toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
        flex-wrap: wrap;

        .search-box {
          flex: 1;
          min-width: 260px;
          max-width: 380px;
        }

        .filter-box {
          display: flex;
          align-items: center;
          gap: 8px;

          .filter-label {
            font-size: 14px;
            color: #555;
            white-space: nowrap;
          }

          .status-filter-select {
            width: 180px;
          }
        }
      }

      .selected-row {
        background-color: #f0f7ff !important;
      }

      /* Views Switcher */
      .desktop-view {
        display: block;
      }
      .mobile-view {
        display: none;
      }

      /* ── Mobile Roadmap Card Styles ─────────────────────────────────── */
      .roadmap-mobile-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .roadmap-mobile-card:active {
        transform: scale(0.99);
      }

      .roadmap-mobile-card--selected {
        border-color: #1890ff;
        background: #f8fbff;
        box-shadow: 0 4px 14px rgba(24, 144, 255, 0.12);
        border-left: 5px solid #1890ff;
      }

      .card-top-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 8px;
      }

      .roadmap-title-area {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
        min-width: 0;
      }

      .roadmap-badge-icon {
        color: #1890ff;
        font-size: 18px;
        flex-shrink: 0;
      }

      .roadmap-name {
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.35;
        word-break: break-word;
      }

      .status-tag {
        margin: 0;
        flex-shrink: 0;
        font-size: 11.5px;
        font-weight: 600;
        border-radius: 6px;
        padding: 2px 8px;
      }

      .roadmap-desc-full {
        font-size: 13px;
        color: #475569;
        line-height: 1.55;
        margin-bottom: 10px;
        background: #f8fafc;
        padding: 9px 12px;
        border-radius: 8px;
        border-left: 3px solid #cbd5e1;
        word-break: break-word;
      }

      .roadmap-meta-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-bottom: 12px;
        padding: 8px 12px;
        background: #ffffff;
        border: 1px dashed #e2e8f0;
        border-radius: 8px;
      }

      .meta-box {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .meta-label {
        font-size: 11px;
        color: #94a3b8;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.03em;
      }

      .meta-value {
        font-size: 12.5px;
        font-weight: 600;
        color: #334155;
      }

      .meta-value.highlight {
        color: #0284c7;
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .roadmap-mobile-actions {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding-top: 10px;
        border-top: 1px solid #f1f5f9;

        .action-btn-main {
          width: 100%;
          font-weight: 600;
          height: 32px;
          display: inline-flex !important;
          align-items: center !important;
          justify-content: center !important;
          text-align: center !important;
          margin: 0 auto !important;
          gap: 6px;
          white-space: nowrap;

          ::ng-deep .anticon + span {
            margin-left: 0 !important;
          }
        }

        .action-btn-pair {
          width: 100%;
          display: flex;
          gap: 8px;
          align-items: center;
          justify-content: center;
          flex-wrap: nowrap !important;
          white-space: nowrap !important;

          .action-btn-sub {
            flex: 1;
            height: 32px;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            white-space: nowrap;
          }
        }
      }

      .mobile-empty-state {
        text-align: center;
        padding: 24px;
        background: #ffffff;
        border-radius: 12px;
        border: 1px dashed #e2e8f0;
      }

      .roadmap-summary-banner {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #1890ff;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 16px;

        .banner-desc {
          font-size: 13.5px;
          color: #334155;
          line-height: 1.5;
          margin-bottom: 8px;
        }

        .banner-meta {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
          font-size: 12px;
          color: #64748b;

          strong {
            color: #0284c7;
          }
        }
      }

      .col-desc {
        min-width: 200px;
      }

      .desc-text {
        color: #475569;
        font-size: 13px;
        line-height: 1.5;
        white-space: normal;
        word-break: break-word;
        display: block;
      }

      /* Compact table paddings to reduce empty vertical space */
      :host ::ng-deep {
        .desktop-view table {
          table-layout: auto !important;
          width: 100% !important;
        }

        .ant-table-thead > tr > th {
          padding: 10px 12px !important;
          font-weight: 600 !important;
          font-size: 13px !important;
        }

        .ant-table-tbody > tr > td {
          padding: 10px 12px !important;
          font-size: 13px !important;
        }

        .ant-collapse > .ant-collapse-item > .ant-collapse-header {
          padding: 10px 14px !important;
          align-items: center !important;
        }

        .ant-collapse-content > .ant-collapse-content-box {
          padding: 12px 14px !important;
        }
      }

      .count-number {
        font-size: 15px;
        font-weight: 600;
        color: #1890ff;
      }

      .table-actions {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
        width: 100%;
        text-align: center;
        gap: 6px;
        white-space: nowrap;

        .btn-manage-phase {
          font-size: 12px;
          height: 28px;
          padding: 0 12px;
          display: inline-flex !important;
          align-items: center !important;
          justify-content: center !important;
          text-align: center !important;
          margin: 0 auto !important;
          gap: 6px;
          min-width: 124px;

          ::ng-deep .anticon + span {
            margin-left: 0 !important;
          }
        }

        .btn-active {
          border-color: #1890ff;
          color: #1890ff;
          font-weight: 600;
          background: #e6f7ff;
        }
      }

      .action-btn-pair {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
        gap: 4px;
        white-space: nowrap;
        flex-wrap: nowrap !important;
        flex-shrink: 0;
        text-align: center;
      }

      .empty-cell {
        text-align: center;
        padding: 30px;
      }

      /* Phase panel */
      .panel-header {
        display: flex;
        align-items: center;
        font-size: 16px;
        gap: 8px;

        .panel-icon {
          color: #1890ff;
        }
      }

      .phase-header-content {
        display: flex;
        align-items: center;
        gap: 8px;

        .phase-order-badge {
          background: #e6f7ff;
          color: #1890ff;
          font-size: 12px;
          font-weight: 600;
          padding: 2px 8px;
          border-radius: 10px;
          border: 1px solid #91d5ff;
        }

        .phase-desc {
          color: #888;
          font-size: 13px;
          font-weight: 400;
        }
      }

      .phase-actions {
        display: flex;
        align-items: center;
        gap: 4px;
      }

      /* Content & Quiz sections */
      .content-section,
      .quiz-section {
        margin-bottom: 12px;
      }

      .section-subtitle {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 10px;
        font-size: 14px;
        color: #333;

        .section-count {
          color: #888;
          font-size: 13px;
          font-weight: 400;
        }
      }

      .empty-hint {
        color: #aaa;
        font-style: italic;
        font-size: 13px;
        margin: 8px 0 12px;
        padding-left: 8px;
      }

      .inner-table {
        border-radius: 6px;
        overflow: hidden;
      }

      .inner-actions {
        display: inline-flex;
        gap: 4px;
        justify-content: center;
        align-items: center;
        flex-wrap: nowrap !important;
        white-space: nowrap !important;

        .btn-active {
          border-color: #1890ff;
          color: #1890ff;
          font-weight: 600;
        }
      }

      .desc-hint {
        color: #888;
        font-size: 12px;
      }

      /* Question card */
      .card-extra-actions {
        display: flex;
        gap: 8px;
        align-items: center;
      }

      /* Modal forms */
      .form-row {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;

        .form-col {
          flex: 1;
          min-width: 120px;
        }
      }

      /* ── Responsive breakpoints ─────────────────────────────────────── */
      @media (max-width: 900px) {
        .phase-header-content {
          flex-wrap: wrap;
        }
        .phase-actions {
          flex-wrap: wrap;
        }
      }

      @media (max-width: 768px) {
        .desktop-view {
          display: none !important;
        }

        .mobile-view {
          display: flex !important;
          flex-direction: column;
          gap: 12px;
        }

        .training-page {
          gap: 14px;
        }

        .page-header {
          flex-direction: column;
          align-items: stretch;
          gap: 14px;
          padding: 14px 16px;

          .header-titles {
            h2 {
              font-size: 18px;
            }
            p {
              font-size: 12px;
            }
          }

          button {
            width: 100%;
            justify-content: center;
          }
        }

        .table-toolbar {
          flex-direction: column;
          align-items: stretch;
          gap: 12px;

          .search-box {
            min-width: 100%;
            max-width: 100%;
          }

          .filter-box {
            width: 100%;
            display: flex;
            align-items: center;
            gap: 10px;

            .filter-label {
              font-size: 13px;
              white-space: nowrap;
            }

            .status-filter-select {
              flex: 1;
              width: auto;
            }
          }
        }

        .panel-header {
          flex-wrap: wrap;
          font-size: 14px;
          line-height: 1.4;
        }

        .phase-header-content {
          font-size: 13px;
          gap: 6px;

          .phase-desc {
            display: block;
            width: 100%;
            margin-top: 2px;
          }
        }

        .phase-actions {
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 8px;

          button {
            font-size: 12px;
            padding: 0 8px;
          }
        }

        .card-extra-actions {
          flex-wrap: wrap;
          gap: 6px;
        }

        .form-row {
          flex-direction: column;
          gap: 0;

          .form-col {
            min-width: 100%;
          }
        }

        .desc-text {
          max-width: 180px;
        }
      }

      @media (max-width: 576px) {
        .page-header {
          padding: 12px 14px;
        }

        .main-card,
        .phase-card,
        .question-card {
          border-radius: 8px;
        }

        .main-card :ng-deep .ant-card-body,
        .phase-card :ng-deep .ant-card-body,
        .question-card :ng-deep .ant-card-body {
          padding: 12px !important;
        }

        .roadmap-mobile-card {
          padding: 12px 14px;
          border-radius: 12px;
        }

        .roadmap-name {
          font-size: 15px;
        }

        .roadmap-desc-full {
          font-size: 12.5px;
          padding: 8px 10px;
          margin-bottom: 8px;
        }

        .roadmap-meta-grid {
          padding: 6px 10px;
          margin-bottom: 10px;
        }

        .meta-label {
          font-size: 10px;
        }

        .meta-value {
          font-size: 12px;
        }

        .roadmap-mobile-actions {
          padding-top: 8px;
          gap: 6px;

          .action-btn-main {
            font-size: 12px;
            height: 30px;
          }

          .action-btn-pair {
            gap: 6px;

            .action-btn-sub {
              font-size: 11.5px;
              height: 30px;
              padding: 0 8px;
            }
          }
        }

        .table-actions {
          button {
            padding: 0 6px;
            font-size: 11px;
          }
        }

        .inner-actions {
          flex-wrap: nowrap !important;
          white-space: nowrap !important;
          button {
            padding: 0 4px;
          }
        }

        .table-toolbar .filter-box {
          flex-direction: column;
          align-items: stretch;
          gap: 6px;

          .status-filter-select {
            width: 100%;
          }
        }
      }

      @media (max-width: 390px) {
        .roadmap-name {
          font-size: 14px;
        }

        .status-tag {
          font-size: 10.5px;
          padding: 1px 6px;
        }

        .roadmap-meta-grid {
          grid-template-columns: 1fr;
          gap: 4px;
        }

        .roadmap-mobile-actions {
          gap: 6px;

          .action-btn-main {
            font-size: 11.5px;
            height: 28px;
          }

          .action-btn-pair {
            gap: 6px;

            .action-btn-sub {
              font-size: 11px;
              height: 28px;
            }
          }
        }
      }
    `,
  ],
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

  protected isQuizModalVisible = false;
  protected readonly editingQuiz = signal<Quiz | null>(null);
  private pendingQuizPhaseId = '';

  protected isQuestionModalVisible = false;
  protected readonly editingQuestion = signal<Question | null>(null);

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
    options: [''],
    correct_answer: [''],
    score: [10, [Validators.required, Validators.min(0)]],
    order_no: [1, [Validators.required, Validators.min(1)]],
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
    this.contentForm.patchValue({
      title: c.title,
      type: c.type,
      description: c.description ?? '',
      content: c.content ?? '',
      resource_url: c.resource_url ?? '',
      order_no: c.order_no,
    });
    this.isContentModalVisible = true;
  }

  closeContentModal(): void {
    this.isContentModalVisible = false;
  }

  saveContent(): void {
    if (this.contentForm.invalid) {
      this.contentForm.markAllAsTouched();
      return;
    }
    const val = this.contentForm.value;
    this.isSaving.set(true);
    const editing = this.editingContent();
    const op$ = editing
      ? this.trainingService.updateContent(editing.id, {
          title: val.title!,
          type: val.type as ContentType,
          description: val.description || null,
          content: val.content || null,
          resource_url: val.resource_url || null,
          order_no: Number(val.order_no),
        })
      : this.trainingService.createContent({
          phase_id: this.pendingContentPhaseId,
          title: val.title!,
          type: val.type as ContentType,
          description: val.description || null,
          content: val.content || null,
          resource_url: val.resource_url || null,
          order_no: Number(val.order_no),
        });

    op$.subscribe({
      next: () => {
        this.message.success(
          editing ? 'Cập nhật nội dung thành công!' : 'Thêm nội dung thành công!',
        );
        this.isSaving.set(false);
        this.isContentModalVisible = false;
        const detail = this.selectedRoadmapDetail();
        if (detail) this.loadRoadmapDetail(detail.id);
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Thao tác thất bại. Vui lòng thử lại.');
        this.isSaving.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  deleteContent(id: string, phaseId: string): void {
    this.trainingService.deleteContent(id).subscribe({
      next: () => {
        this.message.success('Đã xóa nội dung.');
        const detail = this.selectedRoadmapDetail();
        if (detail) this.loadRoadmapDetail(detail.id);
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
    this.isQuizModalVisible = true;
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
    this.isQuizModalVisible = true;
  }

  closeQuizModal(): void {
    this.isQuizModalVisible = false;
  }

  saveQuiz(): void {
    if (this.quizForm.invalid) {
      this.quizForm.markAllAsTouched();
      return;
    }
    const val = this.quizForm.value;
    this.isSaving.set(true);
    const editing = this.editingQuiz();
    const op$ = editing
      ? this.trainingService.updateQuiz(editing.id, {
          title: val.title!,
          description: val.description || null,
          duration_minutes: Number(val.duration_minutes),
          pass_score: Number(val.pass_score),
          max_attempts: Number(val.max_attempts),
        })
      : this.trainingService.createQuiz({
          phase_id: this.pendingQuizPhaseId,
          title: val.title!,
          description: val.description || null,
          duration_minutes: Number(val.duration_minutes),
          pass_score: Number(val.pass_score),
          max_attempts: Number(val.max_attempts),
        });

    op$.subscribe({
      next: (savedQuiz) => {
        this.message.success(editing ? 'Cập nhật Quiz thành công!' : 'Tạo Quiz thành công!');
        this.isSaving.set(false);
        this.isQuizModalVisible = false;
        const phaseId = editing ? editing.phase_id : this.pendingQuizPhaseId;
        this.loadPhaseQuizzes(phaseId);
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Thao tác thất bại. Vui lòng thử lại.');
        this.isSaving.set(false);
        this.cdr.markForCheck();
      },
    });
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
        this.message.success('Đã phát hành Quiz thành công!');
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
      this.questions.set([]);
      return;
    }
    this.selectedQuiz.set(quiz);
    this.loadQuestions(quiz.id);
  }

  closeQuestionPanel(): void {
    this.selectedQuiz.set(null);
    this.questions.set([]);
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

  openCreateQuestionModal(): void {
    this.editingQuestion.set(null);
    const nextOrder = this.questions().length + 1;
    this.questionForm.reset({
      content: '',
      type: 'SINGLE_CHOICE',
      options: '',
      correct_answer: '',
      score: 10,
      order_no: nextOrder,
    });
    this.isQuestionModalVisible = true;
  }

  openEditQuestionModal(q: Question): void {
    this.editingQuestion.set(q);
    this.questionForm.patchValue({
      content: q.content,
      type: q.type,
      options: q.options ?? '',
      correct_answer: q.correct_answer ?? '',
      score: q.score,
      order_no: q.order_no,
    });
    this.isQuestionModalVisible = true;
  }

  closeQuestionModal(): void {
    this.isQuestionModalVisible = false;
  }

  saveQuestion(): void {
    if (this.questionForm.invalid) {
      this.questionForm.markAllAsTouched();
      return;
    }
    const val = this.questionForm.value;
    const quiz = this.selectedQuiz();
    if (!quiz) return;

    this.isSaving.set(true);
    const editing = this.editingQuestion();
    const op$ = editing
      ? this.trainingService.updateQuestion(editing.id, {
          content: val.content!,
          type: val.type as QuestionType,
          options: val.options || null,
          correct_answer: val.correct_answer || null,
          score: Number(val.score),
          order_no: Number(val.order_no),
        })
      : this.trainingService.createQuestion({
          quiz_id: quiz.id,
          content: val.content!,
          type: val.type as QuestionType,
          options: val.options || null,
          correct_answer: val.correct_answer || null,
          score: Number(val.score),
          order_no: Number(val.order_no),
        });

    op$.subscribe({
      next: () => {
        this.message.success(editing ? 'Cập nhật câu hỏi thành công!' : 'Thêm câu hỏi thành công!');
        this.isSaving.set(false);
        this.isQuestionModalVisible = false;
        this.loadQuestions(quiz.id);
        this.cdr.markForCheck();
      },
      error: () => {
        this.message.error('Thao tác thất bại. Vui lòng thử lại.');
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
      error: () => {
        this.message.error('Xóa câu hỏi thất bại.');
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
    const labels: Record<QuestionType, string> = {
      SINGLE_CHOICE: 'Một đáp án',
      MULTIPLE_CHOICE: 'Nhiều đáp án',
      TEXT: 'Tự luận',
    };
    return labels[type] ?? type;
  }

  getQuestionTypeColor(type: QuestionType): string {
    const colors: Record<QuestionType, string> = {
      SINGLE_CHOICE: 'blue',
      MULTIPLE_CHOICE: 'purple',
      TEXT: 'orange',
    };
    return colors[type] ?? 'default';
  }
}
