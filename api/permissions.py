from rest_framework.exceptions import NotFound, PermissionDenied

from api.models import Membership, Organization, Project, Task


def get_organization_for_user(user, organization_id):
    try:
        organization = Organization.objects.get(pk=organization_id)
    except Organization.DoesNotExist as exc:
        raise NotFound("Organization not found.") from exc

    membership = Membership.objects.filter(
        user=user,
        organization=organization,
    ).first()
    if membership is None:
        raise PermissionDenied("You are not a member of this organization.")
    return organization, membership


def get_project_for_user(user, project_id):
    try:
        project = Project.objects.select_related("organization").get(pk=project_id)
    except Project.DoesNotExist as exc:
        raise NotFound("Project not found.") from exc

    membership = Membership.objects.filter(
        user=user,
        organization=project.organization,
    ).first()
    if membership is None:
        raise PermissionDenied("You are not a member of this organization.")
    return project, membership


def get_task_for_user(user, task_id):
    try:
        task = Task.objects.select_related(
            "project__organization",
            "assigned_to",
        ).get(pk=task_id)
    except Task.DoesNotExist as exc:
        raise NotFound("Task not found.") from exc

    membership = Membership.objects.filter(
        user=user,
        organization=task.project.organization,
    ).first()
    if membership is None:
        raise PermissionDenied("You are not a member of this organization.")
    return task, membership


def require_task_write(membership):
    if membership.role == Membership.Role.VIEWER:
        raise PermissionDenied("Viewers cannot create or update tasks.")
