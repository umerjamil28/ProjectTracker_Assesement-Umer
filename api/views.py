from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Membership, Project, Task
from api.permissions import (
    get_organization_for_user,
    get_project_for_user,
    get_task_for_user,
    require_task_write,
)
from api.serializers import (
    LoginSerializer,
    OrganizationMemberSerializer,
    OrganizationSerializer,
    ProjectSerializer,
    TaskFilterSerializer,
    TaskSerializer,
    UserSerializer,
)


def serialize_user(user):
    user = (
        User.objects.prefetch_related("memberships__organization").get(pk=user.pk)
    )
    return UserSerializer(user).data


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": serialize_user(user)})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(serialize_user(request.user))


class OrganizationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            Membership.objects.filter(user=request.user)
            .select_related("organization")
            .order_by("organization__name")
        )
        organizations = []
        for membership in memberships:
            organization = membership.organization
            organization.role = membership.role
            organizations.append(organization)
        return Response(OrganizationSerializer(organizations, many=True).data)


class OrganizationMemberListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization, _membership = get_organization_for_user(
            request.user, organization_id
        )
        members = (
            Membership.objects.filter(organization=organization)
            .select_related("user")
            .order_by("user__username")
        )
        return Response(OrganizationMemberSerializer(members, many=True).data)


class ProjectListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization, _membership = get_organization_for_user(
            request.user, organization_id
        )
        projects = (
            Project.objects.filter(organization=organization)
            .with_task_summary()
            .order_by("-created_at")
        )
        return Response(ProjectSerializer(projects, many=True).data)

    def post(self, request, organization_id):
        organization, membership = get_organization_for_user(
            request.user, organization_id
        )
        if membership.role != Membership.Role.ADMIN:
            return Response(
                {"detail": "Only admins can create projects."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(organization=organization)
        project.open_task_count = 0
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


class TaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project, _membership = get_project_for_user(request.user, project_id)

        filters = TaskFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)

        tasks = Task.objects.filter(project=project).select_related("assigned_to")
        if "status" in filters.validated_data:
            tasks = tasks.filter(status=filters.validated_data["status"])
        assignee = filters.validated_data.get("assignee")
        if assignee:
            if assignee.isdigit():
                tasks = tasks.filter(assigned_to_id=int(assignee))
            else:
                tasks = tasks.filter(assigned_to__username__iexact=assignee)

        return Response(TaskSerializer(tasks, many=True).data)

    def post(self, request, project_id):
        project, membership = get_project_for_user(request.user, project_id)
        require_task_write(membership)

        serializer = TaskSerializer(
            data=request.data,
            context={"project": project},
        )
        serializer.is_valid(raise_exception=True)
        task = serializer.save(project=project)
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, task_id):
        task, membership = get_task_for_user(request.user, task_id)
        require_task_write(membership)

        serializer = TaskSerializer(
            task,
            data=request.data,
            partial=True,
            context={"project": task.project},
        )
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return Response(TaskSerializer(task).data)


class TaskMarkDoneView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task, membership = get_task_for_user(request.user, task_id)
        require_task_write(membership)

        task.status = Task.Status.DONE
        task.save(update_fields=["status"])
        return Response(TaskSerializer(task).data)
