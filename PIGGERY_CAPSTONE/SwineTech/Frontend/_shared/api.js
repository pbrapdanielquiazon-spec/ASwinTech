// ====== Config ======
const isLocalFE = location.hostname === "localhost" && location.port === "5500";
// Frontend on :5500 -> talk to backend on :8000
const API_BASE = isLocalFE ? "http://localhost:8000/api" : "/api";
const TOKEN_KEY = "token";
// If you serve files *inside* the Frontend folder, use a relative page below:
let LOGIN_REDIRECT = "/Zhomepage/login.html";

// ====== Token helpers ======
export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}
export function setToken(t) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}
export function setLoginRedirect(path) {
  LOGIN_REDIRECT = path;
}

// ====== Fetch wrapper with auth + JSON ======
async function _request(path, { method="GET", body=null, params=null, auth=true, form=false } = {}) {
  const url = new URL(API_BASE + path);
  if (params) Object.entries(params).forEach(([k,v])=>{
    if (v==null) return;
    Array.isArray(v) ? v.forEach(x=>url.searchParams.append(k,x)) : url.searchParams.append(k,v);
  });

  const headers = { Accept: "application/json" };
  if (auth && getToken()) headers.Authorization = `Bearer ${getToken()}`;

  let payload = null;
  if (body !== null) {
    if (form && body instanceof URLSearchParams) {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
      payload = body;
    } else {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
  }

  const res = await fetch(url, { method, headers, body: payload });

  // Graceful 401: clear token and bounce to login
  if (res.status === 401) {
    clearToken();
    try {
      const msg = await res.json();
      console.warn("Unauthorized:", msg);
    } catch {}
    if (LOGIN_REDIRECT) window.location.href = LOGIN_REDIRECT;
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      // FastAPI often returns {detail: "..."} or list of errors
      msg = j?.detail
        ? typeof j.detail === "string"
          ? j.detail
          : JSON.stringify(j.detail)
        : JSON.stringify(j);
    } catch {
      // ignore parse error
    }
    throw new Error(msg);
  }

  if (res.status === 204) return null; // allow empty OK
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

/* -------------------------------------------------------
 *                AUTH
 * -----------------------------------------------------*/
export const authApi = {
  login: (username, password) =>
    _request("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username, password }),
      auth: false,
      form: true // <-- add a hint flag (see next)
    }),
  me: () => _request("/auth/me"),
  updateMe: (data) => _request("/auth/me", { method: "PUT", body: data }),
};
/* -------------------------------------------------------
 *                BOOKINGS
 * -----------------------------------------------------*/
  // BOOKINGS
  export const bookingsApi = {
    // ⬇️ default "pending", pass "approved" to see approved ones
    list: (status = "pending") =>
      _request(`/bookings?status=${encodeURIComponent(status)}`),

    get: (id) => _request(`/bookings/${id}`),

    // already matches your backend (POST /bookings/{id}/decision {decision})
    decide: (id, decision) =>
      _request(`/bookings/${id}/decision`, {
        method: "POST",
        body: { decision },
      }),
  };


/* -------------------------------------------------------
 *                SALES
 * -----------------------------------------------------*/
export const salesApi = {
  list: (filters) => _request("/sales", { params: filters }),
  get: (id) => _request(`/sales/${id}`),
  create: (data) => _request("/sales", { method: "POST", body: data }),
  update: (id, data) => _request(`/sales/${id}`, { method: "PUT", body: data }),
  remove: (id) => _request(`/sales/${id}`, { method: "DELETE" }),
};

/* -------------------------------------------------------
 *                AVAILABLE PIGS
 * -----------------------------------------------------*/
// ---------------------- AVAILABLE PIGS ----------------------
export const availApi = {
  create: (data) => _request("/available-pigs", { method: "POST", body: data }),
  list:   (filters) => _request("/available-pigs", { params: filters }), 
  update: (id, data) => _request(`/available-pigs/${id}`, { method: "PUT", body: data }),
  remove: (id) => _request(`/available-pigs/${id}`, { method: "DELETE" }),
};



/* -------------------------------------------------------
 *                SUPPLIES
 * -----------------------------------------------------*/
export const suppliesApi = {
  list: (filters) => _request("/supplies", { params: filters }),
  get: (id) => _request(`/supplies/${id}`),
  create: (data) => _request("/supplies", { method: "POST", body: data }),
  update: (id, data) => _request(`/supplies/${id}`, { method: "PUT", body: data }),
  adjustQty: (id, quantity, updated_by = null) =>
    _request(`/supplies/${id}/adjust-qty`, {
      method: "PATCH",
      body: { quantity, updated_by },
    }),
};

/* -------------------------------------------------------
 *                FEEDING LOGS
 * -----------------------------------------------------*/
export const feedingApi = {
  list: (filters) => _request("/feeding-logs", { params: filters }),
  get: (id) => _request(`/feeding-logs/${id}`),
  create: (data) => _request("/feeding-logs", { method: "POST", body: data }),
  update: (id, data) => _request(`/feeding-logs/${id}`, { method: "PUT", body: data }),
  remove: (id) => _request(`/feeding-logs/${id}`, { method: "DELETE" }),
};

/* -------------------------------------------------------
 *                PIG HEALTH
 * -----------------------------------------------------*/
export const healthApi = {
  listPigRecords: (filters) => _request("/pig-health", { params: filters }),
  createPigRecord: (data) =>
    _request("/pig-health", { method: "POST", body: data }),
  updatePigRecord: (id, data) =>
    _request(`/pig-health/${id}`, { method: "PUT", body: data }),
  removePigRecord: (id) => api(`/pig-health/${id}`, { method:'DELETE' }),
};

/* -------------------------------------------------------
 *                INQUIRIES
 * -----------------------------------------------------*/
export const inquiriesApi = {
  list: (params = {}) => _request("/inquiries", { params }),
  get:  (id)          => _request(`/inquiries/${id}`),
  create: (data)      => _request("/inquiries", { method: "POST", body: data }),
  // PATCH /inquiries/{inquiry_id}/respond { response_message, status = responded (backend sets), responded_by from token }
  respond: (id, response_message) =>
    _request(`/inquiries/${id}/respond`, { method: "PATCH", body: { response_message } }),
};
/* -------------------------------------------------------
 *                REPORTS (fill to match reports.py)
 * -----------------------------------------------------*/
/* ----------------------------- REPORTS ----------------------------- */
export const reportsApi = {
  generate: (payload) =>
    _request("/reports/generate", { method: "POST", body: payload }),
  list: () => _request("/reports"),
  get: (id) => _request(`/reports/${id}`),
};


/* =======================================================
 *               ADDED SECTIONS (requested)
 * =====================================================*/

/* -------------------------------------------------------
 *                EXPENSES
 * -----------------------------------------------------*/
export const expensesApi = {
  list: (filters) => _request("/expenses", { params: filters }),
  get: (id) => _request(`/expenses/${id}`),
  create: (data) => _request("/expenses", { method: "POST", body: data }),
  update: (id, data) => _request(`/expenses/${id}`, { method: "PUT", body: data }),
  remove: (id) => _request(`/expenses/${id}`, { method: "DELETE" }),
};

/* -------------------------------------------------------
 *                PIGS
 * -----------------------------------------------------*/
export const pigsApi = {
  list: (filters) => _request("/pigs", { params: filters }),
  get: (id) => _request(`/pigs/${id}`),
  create: (data) => _request("/pigs", { method: "POST", body: data }),
  update: (id, data) => _request(`/pigs/${id}`, { method: "PUT", body: data }),
  remove: (id) => _request(`/pigs/${id}`, { method: "DELETE" }),
};

/* -------------------------------------------------------
 *                LITTERS
 * -----------------------------------------------------*/
export const littersApi = {
  list: (filters) => _request("/litters", { params: filters }),
  get: (id) => _request(`/litters/${id}`),
  create: (data) => _request("/litters", { method: "POST", body: data }),
  update: (id, data) => _request(`/litters/${id}`, { method: "PUT", body: data }),
  remove: (id) => _request(`/litters/${id}`, { method: "DELETE" }),
};

/* -------------------------------------------------------
 *                FEEDBACK
 * -----------------------------------------------------*/
export const feedbackApi = {
  list: (filters) => _request("/feedback", { params: filters }), // adjust to /feedbacks if needed
  get: (id) => _request(`/feedback/${id}`),
  create: (data) => _request("/feedback", { method: "POST", body: data }),
  update: (id, data) => _request(`/feedback/${id}`, { method: "PUT", body: data }),
  remove: (id) => _request(`/feedback/${id}`, { method: "DELETE" }),
};


/* -------------------------------------------------------
 *                ADMIN (utility endpoints)
 * -----------------------------------------------------*/
export const adminApi = {
  /**
   * Get total users (optionally only active).
   * Returns { total, by_role: {...} }
   */
  usersCount: async (activeOnly = true) => {
    // Try the admin path first…
    try {
      return await _request("/api/admin/users/count", {
        params: { active_only: activeOnly },
      });
    } catch (e) {
      // …and ALWAYS fall back to the non-admin path.
      return await _request("/users/count", {
        params: { active_only: activeOnly },
      });
    }
  },

  /**
   * Convenience: just the number.
   */
  usersTotal: async (activeOnly = true) => {
    const data = await adminApi.usersCount(activeOnly);
    return Number(data?.total ?? 0);
  },
};

/* ------------------ RECEIPTS ------------------ */
export const receiptsApi = {
  list: (params = {}) => _request("/receipts", { params }),
  get:  (id)          => _request(`/receipts/${id}`),
  create: (data)      => _request("/receipts", { method: "POST", body: data }),
  update: (id, data)  => _request(`/receipts/${id}`, { method: "PUT", body: data }),
  remove: (id)        => _request(`/receipts/${id}`, { method: "DELETE" }),
};