/** Solver AI - the ONLY place that talks to the backend (see contracts/api_contract.json). */
import { API_BASE_URL } from "../config.js";

const KEYS = { student: "solver_student", admin: "solver_admin" }; // {token, name}

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

export const session = {
  get: (role) => { try { return JSON.parse(localStorage.getItem(KEYS[role])); } catch { return null; } },
  set: (role, data) => localStorage.setItem(KEYS[role], JSON.stringify(data)),
  clear: (role) => localStorage.removeItem(KEYS[role]),
};

function errorText(detail, status) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (detail?.message) return detail.message;
  return status >= 500 ? "Server error. Please try again." : "Request failed. Please try again.";
}

async function request(path, { method = "GET", body, role } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (role) headers.Authorization = `Bearer ${session.get(role)?.token || ""}`;
  let res;
  try {
    res = await fetch(API_BASE_URL + path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError("Cannot reach the server. Check that the backend is running.", 0);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && role) {
      session.clear(role);
      throw new ApiError("Your session has expired. Please log in again.", 401);
    }
    throw new ApiError(errorText(data.detail, res.status), res.status);
  }
  return data;
}

export const api = {
  // Student auth / registration (3 steps)
  studentLogin: (username, password) => request("/auth/login", { method: "POST", body: { username, password } }),
  requestOtp: (email) => request("/auth/register", { method: "POST", body: { email } }),
  verifyOtp: (email, otp) => request("/auth/verify-otp", { method: "POST", body: { email, otp } }),
  createAccount: (p) => request("/auth/create-account", { method: "POST", body: p }),
  // Student
  getProfile: () => request("/student/profile", { role: "student" }),
  updateProfile: (name) => request("/student/profile", { method: "PUT", body: { name }, role: "student" }),
  getMetrics: () => request("/student/dashboard/metrics", { role: "student" }),
  createComplaint: (body) => request("/complaints", { method: "POST", body, role: "student" }),
  listComplaints: () => request("/complaints", { role: "student" }),
  getComplaint: (id) => request(`/complaints/${id}`, { role: "student" }),
  // Admin
  adminLogin: (email, password) => request("/auth/admin/login", { method: "POST", body: { email, password } }),
  adminDashboard: () => request("/admin/dashboard", { role: "admin" }),
  adminListComplaints: (limit = 100) => request(`/admin/complaints?limit=${limit}`, { role: "admin" }),
  adminGetComplaint: (id) => request(`/admin/complaints/${id}`, { role: "admin" }),
  adminUpdateStatus: (id, status, remarks) =>
    request(`/admin/complaints/${id}/status`, { method: "PATCH", body: { status, remarks: remarks || null }, role: "admin" }),
};
