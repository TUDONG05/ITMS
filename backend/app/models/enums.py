from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    MENTOR = "MENTOR"
    INTERN = "INTERN"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    INACTIVE = "INACTIVE"


class InternshipStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MemberStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXTENDED = "EXTENDED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"


class RoadmapStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ContentType(StrEnum):
    LESSON = "LESSON"
    DOCUMENT = "DOCUMENT"
    VIDEO = "VIDEO"
    LINK = "LINK"


class LearningProgressStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class QuizStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    TRUE_FALSE = "TRUE_FALSE"
    TEXT = "TEXT"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SubmissionStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    ACCEPTED = "ACCEPTED"


class EvaluationType(StrEnum):
    PERIODIC = "PERIODIC"
    FINAL = "FINAL"


class EvaluationStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class CriteriaStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class InternshipRequestType(StrEnum):
    EXTEND = "EXTEND"
    STOP = "STOP"
    COMPLETE = "COMPLETE"


class InternshipRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TargetType(StrEnum):
    ALL = "ALL"
    ROLE = "ROLE"
    USER = "USER"


class AIMessageRole(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
