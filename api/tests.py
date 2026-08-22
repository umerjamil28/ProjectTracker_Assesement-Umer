from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from api.models import Membership, Organization, Project, Task


class AssessmentTestCase(TestCase):
    def setUp(self):
        self._story = []
        self.acme = Organization.objects.create(name="Acme")
        self.globex = Organization.objects.create(name="Globex")

        self.admin = User.objects.create_user("admin", password="pass")
        self.member = User.objects.create_user("member", password="pass")
        self.viewer = User.objects.create_user("viewer", password="pass")
        self.outsider = User.objects.create_user("outsider", password="pass")

        Membership.objects.create(
            user=self.admin,
            organization=self.acme,
            role=Membership.Role.ADMIN,
        )
        Membership.objects.create(
            user=self.member,
            organization=self.acme,
            role=Membership.Role.MEMBER,
        )
        Membership.objects.create(
            user=self.viewer,
            organization=self.acme,
            role=Membership.Role.VIEWER,
        )
        Membership.objects.create(
            user=self.outsider,
            organization=self.globex,
            role=Membership.Role.MEMBER,
        )

        self.project = Project.objects.create(organization=self.acme, name="Mobile")

    def log(self, message):
        self._story.append(message)

    def tearDown(self):
        if self._story:
            print("\n    " + "\n    ".join(self._story) + "\n", flush=True)

    def client_for(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client


class PermissionTests(AssessmentTestCase):
    def test_viewer_cannot_create_project(self):
        self.log("Permission test: viewers are read-only for projects")
        self.log("Setup: viewer is a member of Acme, but not an admin")
        self.log(f"POST /api/v1/organizations/{self.acme.id}/projects/ as viewer")

        response = self.client_for(self.viewer).post(
            f"/api/v1/organizations/{self.acme.id}/projects/",
            {"name": "Secret"},
            format="json",
        )

        self.log(f"Status: {response.status_code} (expected 403)")
        self.log(f"Body: {response.json()}")
        created = Project.objects.filter(name="Secret").exists()
        self.log(f"Project 'Secret' created: {created} (expected False)")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(created)
        self.log("Result: blocked correctly")


class ProjectListAPITests(AssessmentTestCase):
    def test_project_list_includes_open_task_count_and_assignees(self):
        self.log("API test: project list returns open-task count and assignees")
        Task.objects.create(
            project=self.project,
            title="Open one",
            assigned_to=self.member,
            status=Task.Status.OPEN,
        )
        Task.objects.create(
            project=self.project,
            title="Done one",
            assigned_to=self.admin,
            status=Task.Status.DONE,
        )
        self.log("Seeded Mobile with 1 open task (member) and 1 done task (admin)")
        self.log(f"GET /api/v1/organizations/{self.acme.id}/projects/ as admin")

        response = self.client_for(self.admin).get(
            f"/api/v1/organizations/{self.acme.id}/projects/"
        )
        payload = response.json()[0]

        self.log(f"Status: {response.status_code} (expected 200)")
        self.log(f"Project: {payload['name']}")
        self.log(f"open_task_count: {payload['open_task_count']} (expected 1)")
        self.log(f"assignees: {payload['assignees']} (expected member, admin)")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["name"], "Mobile")
        self.assertEqual(payload["open_task_count"], 1)
        self.assertCountEqual(payload["assignees"], ["member", "admin"])
        self.log("Result: payload matches the optimized project-list contract")


class TaskModelValidationTests(AssessmentTestCase):
    def test_assignee_must_belong_to_project_organization(self):
        self.log("Model test: assignee must belong to the project's organization")
        self.log("Setup: outsider is in Globex, project Mobile is in Acme")
        self.log("Trying to save a task assigned to outsider")

        task = Task(
            project=self.project,
            title="Cross-org leak",
            assigned_to=self.outsider,
        )

        with self.assertRaises(ValidationError) as ctx:
            task.save()

        errors = ctx.exception.message_dict
        self.log(f"ValidationError fields: {list(errors.keys())}")
        self.log(f"assigned_to: {errors.get('assigned_to')}")

        self.assertIn("assigned_to", errors)
        self.log("Result: model rejected the cross-org assignee")
