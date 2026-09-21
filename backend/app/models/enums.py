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


class InternshipMemberStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXTENDED = "EXTENDED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"


class EvaluationStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
