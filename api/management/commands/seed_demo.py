from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Membership, Organization, Project, Task

DEMO_PASSWORD = "DemoPass123!"


class Command(BaseCommand):
    help = "Load demo organizations, users, projects, and tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo rows before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            Task.objects.all().delete()
            Project.objects.all().delete()
            Membership.objects.all().delete()
            Organization.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write("Cleared existing demo data.")

        acme = self._org("Acme Corp")
        globex = self._org("Globex Inc")

        alice = self._user("alice", "Alice", "Nguyen", "alice@example.com")
        bob = self._user("bob", "Bob", "Martinez", "bob@example.com")
        carol = self._user("carol", "Carol", "Singh", "carol@example.com")
        dave = self._user("dave", "Dave", "Okafor", "dave@example.com")
        eve = self._user("eve", "Eve", "Chen", "eve@example.com")

        self._membership(alice, acme, Membership.Role.ADMIN)
        self._membership(bob, acme, Membership.Role.MEMBER)
        self._membership(carol, acme, Membership.Role.VIEWER)
        self._membership(alice, globex, Membership.Role.MEMBER)
        self._membership(dave, globex, Membership.Role.ADMIN)
        self._membership(eve, globex, Membership.Role.MEMBER)

        website = self._project(acme, "Website Redesign", is_active=True)
        mobile = self._project(acme, "Mobile App", is_active=True)
        legacy = self._project(acme, "Legacy Migration", is_active=False)
        platform = self._project(globex, "Data Platform", is_active=True)
        marketing = self._project(globex, "Q3 Marketing", is_active=True)

        today = date.today()

        self._task(
            website,
            "Draft homepage wireframes",
            alice,
            Task.Status.IN_PROGRESS,
            today + timedelta(days=3),
            "First pass for marketing review.",
        )
        self._task(
            website,
            "Set up staging environment",
            bob,
            Task.Status.OPEN,
            today + timedelta(days=7),
        )
        self._task(
            website,
            "Write launch checklist",
            bob,
            Task.Status.DONE,
            today - timedelta(days=2),
        )
        self._task(
            mobile,
            "Define MVP user stories",
            alice,
            Task.Status.OPEN,
            today + timedelta(days=5),
        )
        self._task(
            mobile,
            "Prototype onboarding flow",
            bob,
            Task.Status.IN_PROGRESS,
            today + timedelta(days=10),
        )
        self._task(
            legacy,
            "Inventory current reports",
            carol,
            Task.Status.OPEN,
            None,
            "Viewer-owned read of the old warehouse.",
        )
        self._task(
            platform,
            "Design event schema",
            dave,
            Task.Status.IN_PROGRESS,
            today + timedelta(days=4),
        )
        self._task(
            platform,
            "Load sample customer data",
            eve,
            Task.Status.OPEN,
            today + timedelta(days=8),
        )
        self._task(
            platform,
            "Document SLA dashboard",
            alice,
            Task.Status.DONE,
            today - timedelta(days=1),
            "Alice is a member at Globex, so she can own this task.",
        )
        self._task(
            marketing,
            "Draft campaign brief",
            eve,
            Task.Status.OPEN,
            today + timedelta(days=2),
        )

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write(f"Login with any seeded user, password: {DEMO_PASSWORD}")
        self.stdout.write("Users: alice, bob, carol, dave, eve")
        self.stdout.write("Alice belongs to both Acme (admin) and Globex (member).")

    def _org(self, name):
        organization, _ = Organization.objects.get_or_create(name=name)
        return organization

    def _user(self, username, first_name, last_name, email):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def _membership(self, user, organization, role):
        Membership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={"role": role},
        )

    def _project(self, organization, name, is_active):
        project, _ = Project.objects.get_or_create(
            organization=organization,
            name=name,
            defaults={"is_active": is_active},
        )
        return project

    def _task(self, project, title, assigned_to, status, due_date, description=""):
        Task.objects.get_or_create(
            project=project,
            title=title,
            defaults={
                "assigned_to": assigned_to,
                "status": status,
                "due_date": due_date,
                "description": description,
            },
        )
