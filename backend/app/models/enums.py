from enum import StrEnum


class UserRole(StrEnum):
    INTERN = "INTERN"
    MENTOR = "MENTOR"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


class InternshipPeriodStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class InternshipStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    EXTENDED = "EXTENDED"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


class RoadmapStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ContentType(StrEnum):
    TEXT = "TEXT"
    LINK = "LINK"
    FILE = "FILE"
    VIDEO = "VIDEO"


class ExamAttemptStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    GRADED = "GRADED"
    EXPIRED = "EXPIRED"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(StrEnum):
    ASSIGNED = "ASSIGNED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EvaluationType(StrEnum):
    PERIODIC = "PERIODIC"
    FINAL = "FINAL"


class EvaluationStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class DocumentStatus(StrEnum):
    PENDING = "PENDING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


# Proposed Enums for unspecified fields in SRS
class LifecycleRequestType(StrEnum):
    EXTEND = "EXTEND"
    TERMINATE = "TERMINATE"
    COMPLETE = "COMPLETE"


class LifecycleRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LifecycleApprovalDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class FeedbackStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    TRUE_FALSE = "TRUE_FALSE"


class QuestionDifficulty(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class LearningProgressStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class ChatMessageSenderType(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"
