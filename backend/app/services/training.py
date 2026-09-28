import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearningContent, Phase, Question, Quiz, Roadmap
from app.schemas.training import (
    LearningContentCreate,
    LearningContentUpdate,
    PhaseCreate,
    PhaseUpdate,
    QuestionCreate,
    QuestionUpdate,
    QuizCreate,
    QuizUpdate,
    RoadmapCreate,
    RoadmapUpdate,
)


class TrainingService:
    # ------------------------------------------------------------------
    # Roadmap
    # ------------------------------------------------------------------

    @staticmethod
    def get_roadmaps(
        db: Session,
        search: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Roadmap]:
        query = select(Roadmap).order_by(Roadmap.created_at.desc())
        if status is not None:
            query = query.where(Roadmap.status == status)
        if search:
            query = query.where(Roadmap.name.ilike(f"%{search.strip()}%"))
        query = query.offset(skip).limit(limit)
        return list(db.scalars(query).all())

    @staticmethod
    def create_roadmap(
        db: Session,
        data: RoadmapCreate,
        creator_id: uuid.UUID | None = None,
    ) -> Roadmap:
        roadmap = Roadmap(
            name=data.name,
            description=data.description,
            status=data.status,
            created_by=creator_id,
        )
        db.add(roadmap)
        db.commit()
        db.refresh(roadmap)
        return roadmap

    @staticmethod
    def get_roadmap_by_id(db: Session, roadmap_id: uuid.UUID) -> Roadmap:
        roadmap = db.scalar(select(Roadmap).where(Roadmap.id == roadmap_id))
        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Roadmap not found",
            )
        return roadmap

    @staticmethod
    def update_roadmap(
        db: Session,
        roadmap_id: uuid.UUID,
        data: RoadmapUpdate,
    ) -> Roadmap:
        roadmap = TrainingService.get_roadmap_by_id(db, roadmap_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(roadmap, field, value)
        roadmap.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(roadmap)
        return roadmap

    @staticmethod
    def delete_roadmap(db: Session, roadmap_id: uuid.UUID) -> None:
        roadmap = TrainingService.get_roadmap_by_id(db, roadmap_id)
        db.delete(roadmap)
        db.commit()

    # ------------------------------------------------------------------
    # Phase
    # ------------------------------------------------------------------

    @staticmethod
    def get_phases(db: Session, roadmap_id: uuid.UUID) -> list[Phase]:
        query = (
            select(Phase)
            .where(Phase.roadmap_id == roadmap_id)
            .order_by(Phase.order_no.asc())
        )
        return list(db.scalars(query).all())

    @staticmethod
    def get_phase_count(db: Session, roadmap_id: uuid.UUID) -> int:
        from sqlalchemy import func
        count = db.scalar(
            select(func.count(Phase.id)).where(Phase.roadmap_id == roadmap_id)
        )
        return count or 0

    @staticmethod
    def create_phase(db: Session, data: PhaseCreate) -> Phase:
        phase = Phase(
            roadmap_id=data.roadmap_id,
            name=data.name,
            description=data.description,
            order_no=data.order_no,
        )
        db.add(phase)
        db.commit()
        db.refresh(phase)
        return phase

    @staticmethod
    def get_phase_by_id(db: Session, phase_id: uuid.UUID) -> Phase:
        phase = db.scalar(select(Phase).where(Phase.id == phase_id))
        if not phase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phase not found",
            )
        return phase

    @staticmethod
    def update_phase(
        db: Session,
        phase_id: uuid.UUID,
        data: PhaseUpdate,
    ) -> Phase:
        phase = TrainingService.get_phase_by_id(db, phase_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(phase, field, value)
        phase.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(phase)
        return phase

    @staticmethod
    def delete_phase(db: Session, phase_id: uuid.UUID) -> None:
        phase = TrainingService.get_phase_by_id(db, phase_id)
        db.delete(phase)
        db.commit()

    # ------------------------------------------------------------------
    # LearningContent
    # ------------------------------------------------------------------

    @staticmethod
    def get_contents(db: Session, phase_id: uuid.UUID) -> list[LearningContent]:
        query = (
            select(LearningContent)
            .where(LearningContent.phase_id == phase_id)
            .order_by(LearningContent.order_no.asc())
        )
        return list(db.scalars(query).all())

    @staticmethod
    def create_content(db: Session, data: LearningContentCreate) -> LearningContent:
        content = LearningContent(
            phase_id=data.phase_id,
            title=data.title,
            description=data.description,
            type=data.type,
            content=data.content,
            resource_url=data.resource_url,
            order_no=data.order_no,
        )
        db.add(content)
        db.commit()
        db.refresh(content)
        return content

    @staticmethod
    def get_content_by_id(db: Session, content_id: uuid.UUID) -> LearningContent:
        content = db.scalar(select(LearningContent).where(LearningContent.id == content_id))
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning content not found",
            )
        return content

    @staticmethod
    def update_content(
        db: Session,
        content_id: uuid.UUID,
        data: LearningContentUpdate,
    ) -> LearningContent:
        content = TrainingService.get_content_by_id(db, content_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(content, field, value)
        content.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(content)
        return content

    @staticmethod
    def delete_content(db: Session, content_id: uuid.UUID) -> None:
        content = TrainingService.get_content_by_id(db, content_id)
        db.delete(content)
        db.commit()

    # ------------------------------------------------------------------
    # Quiz  (avoid traversing the broken FK to 'phases' table)
    # ------------------------------------------------------------------

    @staticmethod
    def get_quizzes(db: Session, phase_id: uuid.UUID) -> list[Quiz]:
        query = (
            select(Quiz)
            .where(Quiz.phase_id == phase_id)
            .order_by(Quiz.created_at.asc())
        )
        return list(db.scalars(query).all())

    @staticmethod
    def create_quiz(
        db: Session,
        data: QuizCreate,
        creator_id: uuid.UUID | None = None,
    ) -> Quiz:
        quiz = Quiz(
            phase_id=data.phase_id,
            title=data.title,
            description=data.description,
            duration_minutes=data.duration_minutes,
            pass_score=data.pass_score,
            max_attempts=data.max_attempts,
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        return quiz

    @staticmethod
    def get_quiz_by_id(db: Session, quiz_id: uuid.UUID) -> Quiz:
        quiz = db.scalar(select(Quiz).where(Quiz.id == quiz_id))
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found",
            )
        return quiz

    @staticmethod
    def update_quiz(
        db: Session,
        quiz_id: uuid.UUID,
        data: QuizUpdate,
    ) -> Quiz:
        quiz = TrainingService.get_quiz_by_id(db, quiz_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(quiz, field, value)
        db.commit()
        db.refresh(quiz)
        return quiz

    @staticmethod
    def delete_quiz(db: Session, quiz_id: uuid.UUID) -> None:
        quiz = TrainingService.get_quiz_by_id(db, quiz_id)
        db.delete(quiz)
        db.commit()

    @staticmethod
    def publish_quiz(db: Session, quiz_id: uuid.UUID) -> Quiz:
        quiz = TrainingService.get_quiz_by_id(db, quiz_id)
        quiz.status = "PUBLISHED"
        db.commit()
        db.refresh(quiz)
        return quiz

    # ------------------------------------------------------------------
    # Question
    # ------------------------------------------------------------------

    @staticmethod
    def get_questions(db: Session, quiz_id: uuid.UUID) -> list[Question]:
        query = (
            select(Question)
            .where(Question.quiz_id == quiz_id)
            .order_by(Question.order_no.asc())
        )
        return list(db.scalars(query).all())

    @staticmethod
    def create_question(db: Session, data: QuestionCreate) -> Question:
        question = Question(
            quiz_id=data.quiz_id,
            content=data.content,
            type=data.type,
            options=data.options,
            correct_answer=data.correct_answer,
            score=data.score,
            order_no=data.order_no,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        return question

    @staticmethod
    def get_question_by_id(db: Session, question_id: uuid.UUID) -> Question:
        question = db.scalar(select(Question).where(Question.id == question_id))
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found",
            )
        return question

    @staticmethod
    def update_question(
        db: Session,
        question_id: uuid.UUID,
        data: QuestionUpdate,
    ) -> Question:
        question = TrainingService.get_question_by_id(db, question_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(question, field, value)
        db.commit()
        db.refresh(question)
        return question

    @staticmethod
    def delete_question(db: Session, question_id: uuid.UUID) -> None:
        question = TrainingService.get_question_by_id(db, question_id)
        db.delete(question)
        db.commit()
