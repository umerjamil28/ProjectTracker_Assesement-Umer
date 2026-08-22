from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Prefetch, Q


class Organization(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Membership",
        related_name="organizations",
    )

    class Meta:
        db_table = "organization"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "membership"
        ordering = ["organization", "user"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="unique_membership_user_organization",
            ),
        ]

    def __str__(self):
        return f"{self.user} @ {self.organization} ({self.role})"


class ProjectQuerySet(models.QuerySet):
    def with_task_summary(self):
        return self.annotate(
            open_task_count=Count(
                "tasks",
                filter=Q(tasks__status=Task.Status.OPEN),
            )
        ).prefetch_related(
            Prefetch(
                "tasks",
                queryset=Task.objects.select_related("assigned_to"),
            )
        )


class Project(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    objects = ProjectQuerySet.as_manager()

    def __str__(self):
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_tasks",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "task"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "assigned_to"]),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if not self.assigned_to_id or not self.project_id:
            return

        belongs_to_org = Membership.objects.filter(
            user_id=self.assigned_to_id,
            organization_id=self.project.organization_id,
        ).exists()
        if not belongs_to_org:
            raise ValidationError(
                {
                    "assigned_to": (
                        "Assignee must belong to the same organization as the project."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
