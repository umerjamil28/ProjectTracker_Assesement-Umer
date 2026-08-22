const TOKEN_KEY = "atlas_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const token = getToken();
  if (token) {
    headers.Authorization = `Token ${token}`;
  }

  const response = await fetch(`/api/v1${path}`, { ...options, headers });
  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      data.detail ||
      Object.values(data).flat().join(" ") ||
      "Request failed";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

export const api = {
  login(username, password) {
    return request("/auth/login/", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },
  logout() {
    return request("/auth/logout/", { method: "POST" });
  },
  me() {
    return request("/auth/me/");
  },
  organizations(signal) {
    return request("/organizations/", { signal });
  },
  members(organizationId, signal) {
    return request(`/organizations/${organizationId}/members/`, { signal });
  },
  projects(organizationId, signal) {
    return request(`/organizations/${organizationId}/projects/`, { signal });
  },
  tasks(projectId, { status, assignee, signal } = {}) {
    const query = new URLSearchParams();
    if (status) query.set("status", status);
    if (assignee) query.set("assignee", assignee);
    const suffix = query.toString() ? `?${query}` : "";
    return request(`/projects/${projectId}/tasks/${suffix}`, { signal });
  },
  markDone(taskId, signal) {
    return request(`/tasks/${taskId}/done/`, { method: "POST", signal });
  },
  createTask(projectId, payload) {
    return request(`/projects/${projectId}/tasks/`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updateTask(taskId, payload) {
    return request(`/tasks/${taskId}/`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
};
