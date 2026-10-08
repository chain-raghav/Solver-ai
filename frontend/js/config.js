// Backend base URL. Override without editing code by setting
// window.SOLVER_API_URL before this script loads, or localStorage "solver_api_url".
export const API_BASE_URL =
  window.SOLVER_API_URL || localStorage.getItem("solver_api_url") || "https://solver-ai-w7ko.onrender.com/api";

// Exact values from contracts/api_contract.json -> admin_update_status.allowed_statuses
export const ALLOWED_STATUSES = ["Pending", "Submitted", "Under Review", "In Progress", "Resolved", "Rejected", "Closed"];
