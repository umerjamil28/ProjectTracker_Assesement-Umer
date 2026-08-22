from django.contrib.auth.models import User
from rest_framework import serializers

from api.models import Membership, Organization, Project, Task


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class MembershipSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Membership
        fields = ("organization_id", "organization_name", "role")


class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)

    class Meta:
        model = Organization
        fields = ("id", "name", "created_at", "role")


class ProjectSerializer(serializers.ModelSerializer):
    open_task_count = serializers.IntegerField(read_only=True, default=0)
    assignees = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "is_active",
            "created_at",
            "open_task_count",
            "assignees",
        )
        read_only_fields = ("id", "created_at", "open_task_count", "assignees")

    def get_assignees(self, project):
        usernames = []
        seen = set()
        for task in project.tasks.all():
            username = task.assigned_to.username
            if username not in seen:
                seen.add(username)
                usernames.append(username)
        return usernames


class TaskFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False)
    assignee = serializers.CharField(required=False, allow_blank=False)


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_username = serializers.CharField(
        source="assigned_to.username",
        read_only=True,
    )

    class Meta:
        model = Task
        fields = (
            "id",
            "project",
            "title",
            "description",
            "assigned_to",
            "assigned_to_username",
            "status",
            "due_date",
            "created_at",
        )
        read_only_fields = ("id", "project", "assigned_to_username", "created_at")
        extra_kwargs = {
            "description": {"required": False, "allow_blank": True},
            "status": {"required": False},
            "due_date": {"required": False, "allow_null": True},
        }

    def validate_assigned_to(self, user):
        project = self.context.get("project")
        if project is None and self.instance is not None:
            project = self.instance.project
        if project is None:
            return user

        is_org_member = Membership.objects.filter(
            user=user,
            organization_id=project.organization_id,
        ).exists()
        if not is_org_member:
            raise serializers.ValidationError(
                "Assignee must belong to the same organization as the project."
            )
        return user


class OrganizationMemberSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "username", "first_name", "last_name", "role")


class UserSerializer(serializers.ModelSerializer):
    memberships = MembershipSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "memberships",
        )
