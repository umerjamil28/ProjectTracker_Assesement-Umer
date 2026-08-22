from django.urls import path

from api.views import (
    LoginView,
    LogoutView,
    MeView,
    OrganizationListView,
    OrganizationMemberListView,
    ProjectListCreateView,
    TaskDetailView,
    TaskListView,
    TaskMarkDoneView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("organizations/", OrganizationListView.as_view(), name="organization-list"),
    path(
        "organizations/<int:organization_id>/members/",
        OrganizationMemberListView.as_view(),
        name="organization-members",
    ),
    path(
        "organizations/<int:organization_id>/projects/",
        ProjectListCreateView.as_view(),
        name="project-list-create",
    ),
    path(
        "projects/<int:project_id>/tasks/",
        TaskListView.as_view(),
        name="task-list",
    ),
    path("tasks/<int:task_id>/", TaskDetailView.as_view(), name="task-detail"),
    path(
        "tasks/<int:task_id>/done/",
        TaskMarkDoneView.as_view(),
        name="task-mark-done",
    ),
]
