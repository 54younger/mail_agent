"""SQLAlchemy models. Importing this package registers all mappers on
``db.Base.metadata`` so ``db.init_db`` can create the tables."""

from .account import Account
from .email_message import EmailMessage
from .job_application import JobApplication, JobStatus

__all__ = ["Account", "EmailMessage", "JobApplication", "JobStatus"]
