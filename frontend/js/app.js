/** Solver AI - views & routing. All backend calls go through services/api.js */
import { api, session, ApiError } from "./services/api.js";
import { ALLOWED_STATUSES } from "./config.js";

const $app = document.getElementById("app");
const $bar = document.getElementById("topbar");

// ---------- helpers ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const parseDate = (v) => (v ? new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(v) ? v : v + "Z") : null); // backend sends naive UTC
const fmtDate = (v) => { const d = parseDate(v); return d ? d.toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" }) : "-"; };
const fmtShort = (v) => { const d = parseDate(v); return d ? d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit" }) : "-"; };
function ago(v) {
  const d = parseDate(v); if (!d) return "";
  const m = Math.max(0, Math.floor((Date.now() - d) / 60000));
  if (m < 1) return "Registered just now";
  if (m < 60) return `Registered ${m} minute${m > 1 ? "s" : ""} ago`;
  if (m < 1440) { const h = Math.floor(m / 60); return `Registered ${h} hour${h > 1 ? "s" : ""} ago`; }
  const dd = Math.floor(m / 1440); return `Registered ${dd} day${dd > 1 ? "s" : ""} ago`;
}
function badge(status) {
  const cls = { "In Progress": "progress", Resolved: "solved", Closed: "solved", Rejected: "rejected", Pending: "registered", Submitted: "registered", "Under Review": "registered" }[status] || "";
  return `<span class="badge ${cls}">${esc(status)}</span>`;
}
function urgencyBadge(u) {
  if (!u) return "-";
  const cls = { High: "rejected", Medium: "progress", Low: "solved" }[u] || "";
  return `<span class="badge ${cls}">${esc(u)}</span>`;
}
// student endpoints return location:{...}; admin endpoints return flat fields
function loc(c) {
  const l = c.location || c;
  return [l.campus_location, l.building, l.room_number].filter(Boolean).join(", ");
}
const msg = (text, kind = "err") => `<div class="msg ${kind}">${esc(text)}</div>`;
const loading = (t) => `<p class="muted">${t}</p>`;
const go = (hash) => { location.hash = hash; };

// Wrap async view code: auth errors -> login, others -> message
async function guard(role, el, fn, errText) {
  try { await fn(); } catch (e) {
    if (e instanceof ApiError && e.status === 401) { go(role === "admin" ? "#/admin/login" : "#/login"); return; }
    el.innerHTML = msg(e instanceof ApiError && e.status === 0 ? e.message : `${errText} ${e.message || ""}`.trim());
  }
}
function bindForm(id, handler) {
  const f = document.getElementById(id);
  f.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const btn = f.querySelector("button[type=submit]"), out = f.querySelector(".out");
    btn.disabled = true; out.innerHTML = "";
    try { await handler(Object.fromEntries(new FormData(f)), out); }
    catch (e) { out.innerHTML = msg(e.message); }
    finally { btn.disabled = false; }
  });
}

// ---------- layout ----------
function renderBar(role, path) {
  const links = role === "student"
    ? [["#/dashboard", "Dashboard"], ["#/register-complaint", "Register Complaint"], ["#/complaints", "My Complaints"], ["#/profile", "Profile"]]
    : role === "admin" ? [["#/admin", "Dashboard"]] : [];
  $bar.innerHTML = `<a class="brand" href="${role === "admin" ? "#/admin" : role === "student" ? "#/dashboard" : "#/login"}">Solver AI</a><nav>${links.map(([h, t]) =>
    `<a href="${h}" class="${path === h || (h !== "#/admin" && path.startsWith(h + "/")) ? "active" : ""}">${t}</a>`).join("")}
    ${role ? `<button id="logout" style="margin-left:auto">Logout</button>` : ""}</nav>`;
  document.getElementById("logout")?.addEventListener("click", () => { session.clear(role); go(role === "admin" ? "#/admin/login" : "#/login"); });
}

// ---------- auth views ----------
function loginView(role) {
  const admin = role === "admin";
  $app.innerHTML = `<div class="hero"><h1>${admin ? "Review. Resolve.<br>Close the loop." : "Report campus issues.<br>Track them to resolution."}</h1><p>${admin ? "Admin portal for managing student complaints." : "Describe the problem. <b>Solver AI</b> sorts it and keeps you updated."}</p></div><div class="card auth"><h1>${admin ? "Admin Login" : "Student Login"}</h1>
    <form id="f">
      <label>${admin ? "Email" : "Student ID or Email"}</label>
      <input name="u" required autocomplete="username" ${admin ? 'type="email"' : ""}>
      <label>Password</label><input name="p" type="password" required autocomplete="current-password">
      <button class="btn" type="submit">Login</button><div class="out"></div>
    </form>
    <p class="muted">${admin ? '<a href="#/login">Student login</a>' : 'New student? <a href="#/signup">Create an account</a> · <a href="#/admin/login">Admin login</a>'}</p></div>`;
  if (location.hash.includes("registered")) document.querySelector(".out").innerHTML = msg("Account created. Please log in.", "ok");
  bindForm("f", async (v) => {
    if (admin) {
      const r = await api.adminLogin(v.u.trim(), v.p);
      session.set("admin", { token: r.access_token, name: r.name }); go("#/admin");
    } else {
      const r = await api.studentLogin(v.u.trim(), v.p);
      session.set("student", { token: r.access_token, name: r.student?.name }); go("#/dashboard");
    }
  });
}

function signupView() {
  let email = "";
  const step = (n) => {
    const forms = {
      1: `<label>College Email</label><input name="email" type="email" required placeholder="you@vitbhopal.ac.in"><button class="btn" type="submit">Send OTP</button>`,
      2: `<p class="muted">Enter the OTP generated for ${esc(email)}.</p><label>OTP</label><input name="otp" required inputmode="numeric" maxlength="6"><button class="btn" type="submit">Verify OTP</button>`,
      3: `<label>Student ID (10 characters)</label><input name="student_id" required minlength="10" maxlength="10" pattern="[A-Za-z0-9]{10}">
          <label>Full Name</label><input name="name" required><label>Password</label><input name="password" type="password" required minlength="6">
          <button class="btn" type="submit">Create Account</button>`,
    };
    $app.innerHTML = `<div class="hero"><h1>Join Solver AI.</h1><p>Verify your college email to get started.</p></div><div class="card auth"><h1>Create Account</h1><p class="muted">Step ${n} of 3</p>
      <form id="f">${forms[n]}<div class="out"></div></form><p class="muted"><a href="#/login">Back to login</a></p></div>`;
    bindForm("f", async (v) => {
      if (n === 1) { email = v.email.trim(); await api.requestOtp(email); step(2); }
      else if (n === 2) { await api.verifyOtp(email, v.otp.trim()); step(3); }
      else { await api.createAccount({ email, student_id: v.student_id.trim(), name: v.name.trim(), password: v.password }); go("#/login?registered"); }
    });
  };
  step(1);
}

// ---------- student views ----------
function complaintCard(c) {
  return `<a class="card item" href="#/complaints/${c.complaint_id}">
    <div class="top"><b>Complaint #${c.complaint_id}</b>${badge(c.status)}</div>
    <p style="margin:6px 0">${esc(c.complaint_text)}</p>
    <div class="muted">${loc(c) ? `Location: ${esc(loc(c))} · ` : ""}Registered: ${fmtDate(c.created_at)} · ${ago(c.created_at)}</div></a>`;
}

async function studentDashboard() {
  const name = session.get("student")?.name || "Student";
  $app.innerHTML = `<h1>Welcome, ${esc(name)}</h1>
    <div class="actions"><a class="btn" href="#/register-complaint">Register Complaint</a><a class="btn sec" href="#/complaints">My Complaints</a></div>
    <h2>Summary</h2><div id="d">${loading("Loading…")}</div>`;
  const el = document.getElementById("d");
  await guard("student", el, async () => {
    const m = await api.getMetrics();
    el.innerHTML = `<div class="stats"><div class="stat"><b>${m.total}</b><span>Total</span></div><div class="stat"><b>${m.pending}</b><span>Pending</span></div>
      <div class="stat"><b>${m.inProgress}</b><span>In Progress</span></div><div class="stat"><b>${m.resolved}</b><span>Resolved</span></div></div>
      <h2>Recent Complaints</h2>${m.recentComplaints.length ? m.recentComplaints.map(complaintCard).join("") : "<p class='muted'>No complaints registered yet.</p>"}`;
  }, "Unable to load dashboard.");
}

function registerComplaintView() {
  $app.innerHTML = `<h1>Register a Complaint</h1><div class="card"><form id="f">
    <label>Complaint Description *</label><textarea name="text" required minlength="5" placeholder="Describe the problem, e.g. There is water leakage near Block A."></textarea>
    <label>Location (optional)</label><input name="loc" placeholder="e.g. Block A">
    <button class="btn" type="submit">Submit Complaint</button><div class="out"></div></form></div>`;
  bindForm("f", async (v) => {
    const body = { complaint_text: v.text.trim() };
    if (v.loc.trim()) body.location = { campus_location: v.loc.trim() };
    let r;
    try { r = await api.createComplaint(body); }
    catch (e) { if (e.status === 401) { go("#/login"); return; } throw e; }
    $app.innerHTML = `<div class="card center"><h1>Complaint Registered Successfully</h1>
      <p style="font-size:1.2rem"><b>Complaint ID: #${r.complaint_id}</b></p>
      <p class="muted">You can track your complaint from My Complaints.</p>
      <div class="actions" style="justify-content:center"><a class="btn" href="#/complaints">My Complaints</a><a class="btn sec" href="#/register-complaint">Register Another</a></div></div>`;
  });
}

async function myComplaints() {
  $app.innerHTML = `<h1>My Complaints</h1><div id="d">${loading("Loading complaints…")}</div>`;
  const el = document.getElementById("d");
  await guard("student", el, async () => {
    const { complaints } = await api.listComplaints();
    el.innerHTML = complaints.length ? complaints.map(complaintCard).join("") : "<p class='muted'>No complaints registered yet.</p>";
  }, "Unable to load complaints. Please try again.");
}

function timeline(list) {
  if (!list?.length) return "<p class='muted'>No updates yet.</p>";
  return `<ul class="tl">${list.map((u) => `<li><b>${esc(u.new_status)}</b> <span class="muted">· ${fmtDate(u.created_at)}</span>${u.remarks ? `<div>${esc(u.remarks)}</div>` : ""}</li>`).join("")}</ul>`;
}

async function studentDetail(id) {
  $app.innerHTML = `<a class="back" href="#/complaints">← My Complaints</a><div id="d">${loading("Loading…")}</div>`;
  const el = document.getElementById("d");
  await guard("student", el, async () => {
    const c = await api.getComplaint(id);
    el.innerHTML = `<div class="card"><h1>Complaint #${c.complaint_id}</h1><dl>
      <dt>Status</dt><dd>${badge(c.status)}</dd><dt>Description</dt><dd>${esc(c.complaint_text)}</dd>
      <dt>Location</dt><dd>${esc(loc(c)) || "-"}</dd><dt>Registered</dt><dd>${fmtDate(c.created_at)} (${ago(c.created_at)})</dd>
      ${c.assigned_department ? `<dt>Department</dt><dd>${esc(c.assigned_department)}</dd>` : ""}</dl></div>
      <h2>Updates</h2><div class="card">${timeline(c.timeline)}</div>`;
  }, "Unable to load complaint.");
}

async function profileView() {
  $app.innerHTML = `<h1>Profile</h1><div id="d">${loading("Loading…")}</div>`;
  const el = document.getElementById("d");
  await guard("student", el, async () => {
    const p = await api.getProfile();
    el.innerHTML = `<div class="card"><form id="f"><label>Student ID</label><input value="${esc(p.student_id)}" disabled>
      <label>Email</label><input value="${esc(p.email)}" disabled><label>Name</label><input name="name" required value="${esc(p.name)}">
      <button class="btn" type="submit">Save</button><div class="out"></div></form></div>`;
    bindForm("f", async (v, out) => {
      const r = await api.updateProfile(v.name.trim());
      session.set("student", { ...session.get("student"), name: r.name });
      out.innerHTML = msg("Profile updated.", "ok");
    });
  }, "Unable to load profile.");
}

// ---------- admin views ----------
function adminTable(list) {
  if (!list.length) return "<p class='muted'>No complaints found.</p>";
  return `<div class="tablewrap"><table><thead><tr><th>ID</th><th>Complaint</th><th>Location</th><th>Category</th><th>Urgency</th><th>Status</th><th>Date</th></tr></thead><tbody>
    ${list.map((c) => `<tr class="row" data-id="${c.complaint_id}"><td>${c.complaint_id}</td><td>${esc((c.complaint_text || "").slice(0, 70))}</td>
    <td>${esc(loc(c)) || "-"}</td><td>${esc(c.category) || "-"}</td><td>${urgencyBadge(c.urgency)}</td><td>${badge(c.status)}</td><td>${fmtShort(c.created_at)}</td></tr>`).join("")}</tbody></table></div>`;
}
const bindRows = (el) => el.querySelectorAll("tr.row").forEach((r) => r.addEventListener("click", () => go(`#/admin/complaints/${r.dataset.id}`)));

async function adminDashboard() {
  $app.innerHTML = `<h1>Admin Dashboard</h1><div id="d">${loading("Loading complaints…")}</div>`;
  const el = document.getElementById("d");
  await guard("admin", el, async () => {
    const [d, r] = await Promise.all([api.adminDashboard(), api.adminListComplaints()]);
    el.innerHTML = `<div class="stats"><div class="stat"><b>${d.total_complaints}</b><span>Total</span></div><div class="stat"><b>${d.pending}</b><span>Pending</span></div>
      <div class="stat"><b>${d.in_progress}</b><span>In Progress</span></div><div class="stat"><b>${d.resolved}</b><span>Resolved</span></div></div>
      <h2>All Complaints</h2>${adminTable(r.complaints)}${r.total > r.complaints.length ? `<p class="muted">Showing ${r.complaints.length} of ${r.total}.</p>` : ""}`;
    bindRows(el);
  }, "Unable to load complaints. Please try again.");
}

async function adminDetail(id) {
  $app.innerHTML = `<a class="back" href="#/admin">← Dashboard</a><div id="d">${loading("Loading…")}</div>`;
  const el = document.getElementById("d");
  const draw = async (flash) => {
    const c = await api.adminGetComplaint(id);
    el.innerHTML = `${flash || ""}<div class="card"><h1>Complaint #${c.complaint_id}</h1><dl>
      <dt>Description</dt><dd>${esc(c.complaint_text)}</dd><dt>Location</dt><dd>${esc(loc(c)) || "-"}</dd>
      <dt>Registered</dt><dd>${fmtDate(c.created_at)}</dd><dt>Category</dt><dd>${esc(c.category) || "-"}</dd><dt>Urgency</dt><dd>${urgencyBadge(c.urgency)}</dd>${c.assigned_department ? `<dt>Department</dt><dd>${esc(c.assigned_department)}</dd>` : ""}${c.duration ? `<dt>Duration</dt><dd>${esc(c.duration)}</dd>` : ""}${c.affected_count ? `<dt>Affected</dt><dd>${esc(c.affected_count)} people</dd>` : ""}<dt>Current Status</dt><dd>${badge(c.status)}</dd>
      <dt>Student</dt><dd>${esc(c.student?.name)}${c.student?.student_id ? ` (${esc(c.student.student_id)})` : ""}</dd></dl></div>
      <div class="card"><form id="f"><label>Update Status</label>
      <select name="status">${ALLOWED_STATUSES.map((s) => `<option ${s === c.status ? "selected" : ""}>${s}</option>`).join("")}</select>
      <label>Remarks (optional)</label><input name="remarks"><button class="btn" type="submit">Update Status</button><div class="out"></div></form></div>
      <h2>Status History</h2><div class="card">${timeline(c.timeline)}</div>`;
    bindForm("f", async (v) => {
      try { await api.adminUpdateStatus(id, v.status, v.remarks.trim()); }
      catch (e) { if (e.status === 401) { go("#/admin/login"); return; } throw e; }
      await draw(msg("Status updated successfully.", "ok"));
    });
  };
  await guard("admin", el, () => draw(), "Unable to load complaint.");
}

// ---------- router ----------
function route() {
  const path = (location.hash || "#/").split("?")[0];
  const parts = path.split("/"); // ["#", ...]
  const isAdmin = path.startsWith("#/admin");
  const publicPaths = ["#/login", "#/signup", "#/admin/login"];
  if (path === "#/" || path === "#" ) return go(session.get("student") ? "#/dashboard" : "#/login");
  if (!publicPaths.includes(path)) {
    const role = isAdmin ? "admin" : "student";
    if (!session.get(role)) return go(isAdmin ? "#/admin/login" : "#/login");
  }
  const role = publicPaths.includes(path) ? null : isAdmin ? "admin" : "student";
  renderBar(role, path);
  window.scrollTo(0, 0);
  const id = parts[parts.length - 1];
  if (path === "#/login") return loginView("student");
  if (path === "#/signup") return signupView();
  if (path === "#/admin/login") return loginView("admin");
  if (path === "#/dashboard") return studentDashboard();
  if (path === "#/register-complaint") return registerComplaintView();
  if (path === "#/complaints") return myComplaints();
  if (path.startsWith("#/complaints/")) return studentDetail(id);
  if (path === "#/profile") return profileView();
  if (path === "#/admin") return adminDashboard();
  if (path === "#/admin/complaints") return go("#/admin");
  if (path.startsWith("#/admin/complaints/")) return adminDetail(id);
  go("#/");
}
window.addEventListener("hashchange", route);
route();
