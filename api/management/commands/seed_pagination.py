from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from api.models import Membership, Project, Task

PROJECT_NAMES = ["Mobile App", "Test Project", "Q3 Marketing"]
MIN_TASKS = 8
STATUSES = [Task.Status.OPEN, Task.Status.IN_PROGRESS, Task.Status.DONE]


class Command(BaseCommand):
    help = "Add sample tasks so pagination appears on selected projects."

    def handle(self, *args, **options):
        for name in PROJECT_NAMES:
            try:
                project = Project.objects.get(name=name)
            except Project.DoesNotExist:
                self.stderr.write(f"Missing project: {name}")
                continue

            assignees = list(
                User.objects.filter(
                    memberships__organization=project.organization,
                ).distinct()
            )
            if not assignees:
                self.stderr.write(f"No members for {name}")
                continue

            current = Task.objects.filter(project=project).count()
            needed = max(0, MIN_TASKS - current)
            for index in range(needed):
                n = current + index + 1
                Task.objects.create(
                    project=project,
                    title=f"Pagination task {n}",
                    description=f"Sample task so {name} has more than one page.",
                    assigned_to=assignees[index % len(assignees)],
                    status=STATUSES[index % len(STATUSES)],
                )

            total = Task.objects.filter(project=project).count()
            self.stdout.write(self.style.SUCCESS(f"{name}: {total} tasks"))
