<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../api";

const props = defineProps({
  user: { type: Object, required: true },
});
const emit = defineEmits(["logout"]);

const organizations = ref([]);
const orgId = ref(null);
const projects = ref([]);
const members = ref([]);
const tasks = ref([]);
const projectId = ref(null);
const statusFilter = ref("");
const assigneeFilter = ref("");
const error = ref("");
const loadingProjects = ref(false);
const refreshingProjects = ref(false);
const loadingTasks = ref(false);
const markingId = ref(null);
const newTitle = ref("");
const newDescription = ref("");
const newAssignee = ref("");
const creating = ref(false);
const newProjectName = ref("");
const creatingProject = ref(false);
const taskPage = ref(1);
const taskCount = ref(0);
const deletingId = ref(null);
const editingId = ref(null);
const editTitle = ref("");
const editDescription = ref("");
const editAssignee = ref("");
const editStatus = ref("open");
const savingEdit = ref(false);
const profileOpen = ref(false);
const profile = ref(null);
const profileLoading = ref(false);
const profileError = ref("");
const cache = new Map();
const taskCache = new Map();

let workspaceController = null;
let taskController = null;
let workspaceSeq = 0;
let taskSeq = 0;

const currentOrg = computed(() =>
  organizations.value.find((org) => org.id === orgId.value),
);
const currentProject = computed(() =>
  projects.value.find((project) => project.id === projectId.value),
);
const canWrite = computed(() =>
  ["admin", "member"].includes(currentOrg.value?.role),
);
const canAdmin = computed(() => currentOrg.value?.role === "admin");
const taskPageCount = computed(() =>
  Math.max(1, Math.ceil(taskCount.value / 5)),
);

function isAbort(err) {
  return err?.name === "AbortError";
}

function taskKey(projectId, status = statusFilter.value, assignee = assigneeFilter.value, page = taskPage.value) {
  return `${projectId}:${status}:${assignee}:${page}`;
}

function rememberTasks(projectId, payload) {
  taskCache.set(taskKey(projectId), payload);
}

function invalidateProjectTasks(id) {
  for (const key of [...taskCache.keys()]) {
    if (key.startsWith(`${id}:`)) {
      taskCache.delete(key);
    }
  }
}

function cachedTasks(projectId) {
  return taskCache.get(taskKey(projectId));
}

function rememberOrg() {
  if (!orgId.value) {
    return;
  }
  cache.set(orgId.value, {
    projects: projects.value,
    members: members.value,
    projectId: projectId.value,
  });
}

function showCachedOrg(id) {
  const cached = cache.get(id);
  if (!cached) {
    projects.value = [];
    members.value = [];
    tasks.value = [];
    projectId.value = null;
    return false;
  }
  projects.value = cached.projects;
  members.value = cached.members;
  projectId.value = cached.projectId;
  const cachedTasksPage = cachedTasks(cached.projectId);
  tasks.value = cachedTasksPage?.results ?? [];
  taskCount.value = cachedTasksPage?.count ?? 0;
  newAssignee.value = defaultAssignee();
  return true;
}

function abortWorkspace() {
  workspaceController?.abort();
  workspaceController = new AbortController();
  return workspaceController.signal;
}

function abortTasks() {
  taskController?.abort();
  taskController = new AbortController();
  return taskController.signal;
}

async function loadOrganizations() {
  organizations.value = await api.organizations();
  orgId.value = organizations.value[0]?.id ?? null;
}

async function loadWorkspace(id = orgId.value) {
  if (!id) {
    projects.value = [];
    members.value = [];
    tasks.value = [];
    projectId.value = null;
    return;
  }

  const seq = ++workspaceSeq;
  const signal = abortWorkspace();
  abortTasks();
  const hadCache = showCachedOrg(id);
  loadingProjects.value = !hadCache;
  refreshingProjects.value = true;
  error.value = "";

  try {
    const [projectList, memberList] = await Promise.all([
      api.projects(id, signal),
      api.members(id, signal),
    ]);
    if (seq !== workspaceSeq || orgId.value !== id) {
      return;
    }

    projects.value = projectList;
    members.value = memberList;
    newAssignee.value = defaultAssignee();
    const selected = projectList.some((project) => project.id === projectId.value)
      ? projectId.value
      : projectList[0]?.id ?? null;
    projectId.value = selected;
    rememberOrg();
    await loadTasks(selected);
  } catch (err) {
    if (isAbort(err) || seq !== workspaceSeq) {
      return;
    }
    error.value = err.message;
  } finally {
    if (seq === workspaceSeq) {
      loadingProjects.value = false;
      refreshingProjects.value = false;
    }
  }
}

async function loadTasks(explicitProjectId) {
  const id = explicitProjectId ?? projectId.value;
  if (!id) {
    tasks.value = [];
    return;
  }

  const seq = ++taskSeq;
  const signal = abortTasks();
  const hit = cachedTasks(id);
  if (hit) {
    tasks.value = hit.results;
    taskCount.value = hit.count;
    loadingTasks.value = false;
  } else {
    tasks.value = [];
    loadingTasks.value = true;
  }
  error.value = "";

  try {
    const payload = await api.tasks(id, {
      status: statusFilter.value,
      assignee: assigneeFilter.value,
      page: taskPage.value,
      signal,
    });
    if (seq !== taskSeq || projectId.value !== id) {
      return;
    }
    tasks.value = payload.results;
    taskCount.value = payload.count;
    rememberTasks(id, {
      results: payload.results,
      count: payload.count,
    });
    rememberOrg();
  } catch (err) {
    if (isAbort(err) || seq !== taskSeq) {
      return;
    }
    error.value = err.message;
  } finally {
    if (seq === taskSeq) {
      loadingTasks.value = false;
    }
  }
}

function defaultAssignee() {
  const self = members.value.find((member) => member.username === props.user.username);
  return String(self?.id ?? members.value[0]?.id ?? "");
}

async function createTask() {
  if (!projectId.value || !newTitle.value.trim() || !newAssignee.value) {
    error.value = "Title and assignee are required.";
    return;
  }

  creating.value = true;
  error.value = "";
  try {
    await api.createTask(projectId.value, {
      title: newTitle.value.trim(),
      description: newDescription.value.trim(),
      assigned_to: Number(newAssignee.value),
    });
    newTitle.value = "";
    newDescription.value = "";
    taskPage.value = 1;
    invalidateProjectTasks(projectId.value);
    await loadWorkspace();
  } catch (err) {
    error.value = err.message;
  } finally {
    creating.value = false;
  }
}

async function createProject() {
  if (!orgId.value || !newProjectName.value.trim()) {
    error.value = "Project name is required.";
    return;
  }

  creatingProject.value = true;
  error.value = "";
  try {
    const project = await api.createProject(orgId.value, {
      name: newProjectName.value.trim(),
    });
    newProjectName.value = "";
    projectId.value = project.id;
    taskPage.value = 1;
    cache.delete(orgId.value);
    await loadWorkspace();
  } catch (err) {
    error.value = err.message;
  } finally {
    creatingProject.value = false;
  }
}

async function deleteTask(task) {
  deletingId.value = task.id;
  error.value = "";
  try {
    await api.deleteTask(task.id);
    invalidateProjectTasks(projectId.value);
    if (tasks.value.length === 1 && taskPage.value > 1) {
      taskPage.value -= 1;
    }
    await loadWorkspace();
  } catch (err) {
    error.value = err.message;
  } finally {
    deletingId.value = null;
  }
}

function changeFilters() {
  taskPage.value = 1;
  loadTasks();
}

function goToPage(page) {
  if (page < 1 || page > taskPageCount.value) {
    return;
  }
  taskPage.value = page;
  loadTasks();
}

async function markDone(task) {
  markingId.value = task.id;
  error.value = "";
  try {
    await api.markDone(task.id);
    invalidateProjectTasks(projectId.value);
    await loadWorkspace();
  } catch (err) {
    if (!isAbort(err)) {
      error.value = err.message;
    }
  } finally {
    markingId.value = null;
  }
}

function startEdit(task) {
  editingId.value = task.id;
  editTitle.value = task.title;
  editDescription.value = task.description || "";
  editAssignee.value = String(task.assigned_to);
  editStatus.value = task.status;
}

function cancelEdit() {
  editingId.value = null;
}

async function saveEdit() {
  if (!editingId.value || !editTitle.value.trim() || !editAssignee.value) {
    error.value = "Title and assignee are required.";
    return;
  }

  savingEdit.value = true;
  error.value = "";
  try {
    await api.updateTask(editingId.value, {
      title: editTitle.value.trim(),
      description: editDescription.value.trim(),
      assigned_to: Number(editAssignee.value),
      status: editStatus.value,
    });
    editingId.value = null;
    invalidateProjectTasks(projectId.value);
    await loadWorkspace();
  } catch (err) {
    error.value = err.message;
  } finally {
    savingEdit.value = false;
  }
}

function selectOrg(id) {
  if (id === orgId.value) {
    return;
  }
  editingId.value = null;
  orgId.value = id;
  statusFilter.value = "";
  assigneeFilter.value = "";
  taskPage.value = 1;
  loadWorkspace(id);
}

function selectProject(id) {
  if (id === projectId.value) {
    return;
  }
  editingId.value = null;
  projectId.value = id;
  statusFilter.value = "";
  assigneeFilter.value = "";
  taskPage.value = 1;
  loadTasks(id);
}

function statusLabel(status) {
  return status.replace("_", " ");
}

async function openProfile() {
  profileOpen.value = true;
  profileLoading.value = true;
  profileError.value = "";
  try {
    profile.value = await api.me();
  } catch (err) {
    profileError.value = err.message;
  } finally {
    profileLoading.value = false;
  }
}

function closeProfile() {
  profileOpen.value = false;
}

onMounted(async () => {
  try {
    await loadOrganizations();
    await loadWorkspace();
  } catch (err) {
    if (!isAbort(err)) {
      error.value = err.message;
    }
  }
});

</script>

<template>
  <div class="shell">
    <header class="top">
      <div>
        <p class="brand-kicker">Workspace</p>
        <h1>Atlas</h1>
      </div>
      <div class="orgs" role="tablist">
        <button
          v-for="org in organizations"
          :key="org.id"
          :class="{ active: org.id === orgId }"
          type="button"
          @click="selectOrg(org.id)"
        >
          {{ org.name }}
          <span>{{ org.role }}</span>
        </button>
      </div>
      <div class="who">
        <button type="button" class="name-btn" @click="openProfile">
          {{ user.first_name || user.username }}
        </button>
        <button type="button" class="ghost" @click="emit('logout')">
          Log out
        </button>
      </div>
    </header>

    <div
      v-if="profileOpen"
      class="overlay"
      @click.self="closeProfile"
    >
      <section class="popup" role="dialog" aria-labelledby="profile-title">
        <div class="popup-head">
          <h2 id="profile-title">Your profile</h2>
          <button type="button" class="ghost" @click="closeProfile">Close</button>
        </div>
        <p v-if="profileLoading" class="empty">Loading profile…</p>
        <p v-else-if="profileError" class="banner">{{ profileError }}</p>
        <div v-else-if="profile" class="profile">
          <p><span>Username</span> {{ profile.username }}</p>
          <p><span>Name</span> {{ [profile.first_name, profile.last_name].filter(Boolean).join(" ") || "—" }}</p>
          <p><span>Email</span> {{ profile.email || "—" }}</p>
          <h3>Organizations</h3>
          <ul>
            <li v-for="item in profile.memberships" :key="item.organization_id">
              {{ item.organization_name }}
              <em>{{ item.role }}</em>
            </li>
          </ul>
        </div>
      </section>
    </div>

    <p v-if="error" class="banner">{{ error }}</p>

    <section class="board">
      <aside>
        <div class="aside-head">
          <h2>Projects</h2>
          <p>{{ loadingProjects ? "Loading…" : `${projects.length} in this org` }}</p>
        </div>
        <form v-if="canAdmin" class="project-composer" @submit.prevent="createProject">
          <input v-model="newProjectName" placeholder="New project name" />
          <button type="submit" :disabled="creatingProject">
            {{ creatingProject ? "Adding…" : "Add" }}
          </button>
        </form>
        <div v-if="loadingProjects && !projects.length" class="skeletons">
          <div v-for="n in 3" :key="n" class="skeleton" />
        </div>
        <article
          v-for="project in projects"
          :key="project.id"
          :class="{ selected: project.id === projectId, quiet: !project.is_active }"
          @click="selectProject(project.id)"
        >
          <div class="card-top">
            <h3>{{ project.name }}</h3>
            <em class="open-count">{{ refreshingProjects ? "…" : `${project.open_task_count} open` }}</em>
          </div>
          <p class="assignees">
            {{ project.assignees.length ? project.assignees.join(" · ") : "No assignees yet" }}
          </p>
          <small v-if="!project.is_active">Inactive</small>
        </article>
      </aside>

      <main>
        <div class="main-head">
          <div>
            <p class="brand-kicker">{{ currentOrg?.name }}</p>
            <h2>{{ currentProject?.name || "Select a project" }}</h2>
          </div>
          <div class="filters">
            <select v-model="statusFilter" @change="changeFilters">
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In progress</option>
              <option value="done">Done</option>
            </select>
            <select v-model="assigneeFilter" @change="changeFilters">
              <option value="">All people</option>
              <option
                v-for="member in members"
                :key="member.id"
                :value="member.username"
              >
                {{ member.username }}
              </option>
            </select>
          </div>
        </div>

        <form v-if="canWrite && currentProject" class="composer" @submit.prevent="createTask">
          <input v-model="newTitle" placeholder="New task title" />
          <select v-model="newAssignee">
            <option disabled value="">Assignee</option>
            <option
              v-for="member in members"
              :key="member.id"
              :value="String(member.id)"
            >
              {{ member.username }}
            </option>
          </select>
          <input v-model="newDescription" placeholder="Optional description" />
          <button type="submit" :disabled="creating">
            {{ creating ? "Adding…" : "Add task" }}
          </button>
        </form>

        <div v-if="loadingTasks" class="task-loading">
          <p class="empty">Loading tasks{{ currentProject ? ` for ${currentProject.name}` : "" }}…</p>
          <div class="skeletons">
            <div v-for="n in 3" :key="n" class="skeleton task-skeleton" />
          </div>
        </div>
        <p v-else-if="!tasks.length" class="empty">No tasks match these filters.</p>

        <ul v-else class="tasks">
          <li v-for="task in tasks" :key="task.id">
            <form v-if="editingId === task.id" class="edit-form" @submit.prevent="saveEdit">
              <input v-model="editTitle" placeholder="Title" />
              <input v-model="editDescription" placeholder="Description" />
              <select v-model="editAssignee">
                <option
                  v-for="member in members"
                  :key="member.id"
                  :value="String(member.id)"
                >
                  {{ member.username }}
                </option>
              </select>
              <select v-model="editStatus">
                <option value="open">Open</option>
                <option value="in_progress">In progress</option>
                <option value="done">Done</option>
              </select>
              <div class="actions">
                <button type="submit" :disabled="savingEdit">
                  {{ savingEdit ? "Saving…" : "Save" }}
                </button>
                <button type="button" class="ghost" @click="cancelEdit">Cancel</button>
              </div>
            </form>
            <template v-else>
              <div>
                <strong>{{ task.title }}</strong>
                <p>{{ task.description || "No description" }}</p>
                <span :class="['pill', task.status]">{{ statusLabel(task.status) }}</span>
                <span class="owner">{{ task.assigned_to_username }}</span>
              </div>
              <div v-if="canWrite" class="actions">
                <button type="button" class="ghost" @click="startEdit(task)">Edit</button>
                <button
                  v-if="task.status !== 'done'"
                  type="button"
                  :disabled="markingId === task.id"
                  @click="markDone(task)"
                >
                  {{ markingId === task.id ? "Saving…" : "Mark done" }}
                </button>
                <button
                  type="button"
                  class="ghost"
                  :disabled="deletingId === task.id"
                  @click="deleteTask(task)"
                >
                  {{ deletingId === task.id ? "Removing…" : "Delete" }}
                </button>
              </div>
            </template>
          </li>
        </ul>

        <nav v-if="!loadingTasks && taskPageCount > 1" class="pager">
          <button
            type="button"
            class="ghost"
            :disabled="taskPage <= 1"
            @click="goToPage(taskPage - 1)"
          >
            Previous
          </button>
          <span>Page {{ taskPage }} of {{ taskPageCount }}</span>
          <button
            type="button"
            class="ghost"
            :disabled="taskPage >= taskPageCount"
            @click="goToPage(taskPage + 1)"
          >
            Next
          </button>
        </nav>
      </main>
    </section>
  </div>
</template>

<style scoped>
.shell {
  box-sizing: border-box;
  min-height: 100vh;
  width: min(1280px, calc(100% - 48px));
  margin: 0 auto;
  padding: 28px 0 40px;
}

.top {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 24px;
  align-items: center;
  margin-bottom: 24px;
}

.brand-kicker {
  margin: 0 0 4px;
  color: var(--accent);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 0.75rem;
}

h1 {
  font-size: 2.4rem;
}

.orgs {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  justify-self: center;
  gap: 8px;
}

.orgs button,
.ghost,
.tasks button {
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
}

.orgs button span {
  margin-left: 8px;
  color: var(--muted);
  font-size: 0.78rem;
}

.orgs button.active {
  background: var(--ink);
  color: #fff;
  border-color: var(--ink);
}

.orgs button.active span {
  color: #f0d2bf;
}

.who {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  text-align: right;
}

.name-btn {
  border: 0;
  padding: 0;
  background: none;
  font-weight: 650;
  font-family: Fraunces, serif;
  font-size: 1.05rem;
  cursor: pointer;
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.overlay {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(27, 24, 20, 0.35);
}

.popup {
  width: min(420px, 100%);
  padding: 24px;
  border-radius: 24px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

.popup-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.profile p {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 10px;
}

.profile span {
  color: var(--muted);
}

.profile h3 {
  margin: 18px 0 8px;
  font-size: 1.1rem;
}

.profile ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.profile li {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid var(--line);
}

.profile em {
  font-style: normal;
  color: var(--accent-dark);
  text-transform: capitalize;
}

.banner {
  padding: 12px 16px;
  border-radius: 12px;
  background: #fde8e8;
  color: #9f1239;
}

.board {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 20px;
  width: 100%;
  min-height: 70vh;
}

aside,
main {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 24px;
  box-shadow: var(--shadow);
}

aside {
  min-width: 0;
  padding: 18px;
  display: grid;
  align-content: start;
  gap: 10px;
}

.aside-head h2 {
  font-size: 1.7rem;
}

.project-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 4.2rem;
  gap: 8px;
}

.project-composer input {
  min-width: 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
}

.project-composer button {
  width: 4.2rem;
  border: 0;
  border-radius: 12px;
  padding: 10px 0;
  background: var(--accent);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  color: var(--muted);
}

.aside-head p,
.empty,
.assignees,
.tasks p {
  color: var(--muted);
}

.skeletons {
  display: grid;
  gap: 12px;
}

.skeleton {
  height: 84px;
  border-radius: 16px;
  background: linear-gradient(90deg, #efe7d9 25%, #f7f1e6 50%, #efe7d9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.1s ease infinite;
}

.task-loading {
  display: grid;
  gap: 12px;
}

.task-skeleton {
  height: 92px;
}

@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

article {
  width: 100%;
  min-width: 0;
  padding: 13px 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  cursor: pointer;
  background: #fff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

article.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(196, 92, 38, 0.12);
}

article.quiet {
  opacity: 0.7;
}

.card-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: start;
}

.card-top h3 {
  min-width: 0;
  font-size: 1.12rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

.open-count {
  margin: 0;
  font-size: 0.88rem;
  font-style: normal;
  color: var(--forest);
  font-weight: 600;
  white-space: nowrap;
  text-align: right;
}

.assignees,
article small {
  margin: 8px 0 0;
  font-size: 0.88rem;
}

main {
  padding: 24px;
}

.main-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: end;
  margin-bottom: 20px;
}

.filters {
  display: flex;
  gap: 8px;
}

.composer {
  display: grid;
  grid-template-columns: 1.4fr 0.8fr 1.4fr auto;
  gap: 8px;
  margin-bottom: 18px;
}

.composer input,
.composer select {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
}

.composer button {
  border: 0;
  border-radius: 12px;
  padding: 10px 16px;
  background: var(--accent);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.composer button:disabled {
  opacity: 0.65;
  cursor: wait;
}

select {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
}

.tasks {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.tasks li {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 16px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid var(--line);
}

.tasks p {
  margin: 6px 0 10px;
}

.pill {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 0.75rem;
  text-transform: capitalize;
  background: var(--bg-deep);
}

.pill.open {
  background: #f3e0c8;
  color: var(--amber);
}

.pill.in_progress {
  background: #f4d7c6;
  color: var(--accent-dark);
}

.pill.done {
  background: #d9eadf;
  color: var(--forest);
}

.owner {
  margin-left: 8px;
  color: var(--muted);
  font-size: 0.85rem;
}

.actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.edit-form {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.edit-form input,
.edit-form select {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
}

.edit-form .actions {
  grid-column: 1 / -1;
}

.tasks button {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.tasks .ghost {
  background: var(--card);
  color: var(--ink);
}

@media (max-width: 860px) {
  .top,
  .board,
  .main-head,
  .composer,
  .edit-form,
  .tasks li {
    grid-template-columns: 1fr;
    display: grid;
  }

  .who {
    text-align: left;
  }
}
</style>
