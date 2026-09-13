/**
 * The only module that knows the API exists.
 *
 * Every network call lives here so components stay declarative and so error
 * handling is consistent: the backend returns { detail: "..." } for every
 * failure, and this layer turns that into an Error with a message a person can
 * actually read.
 */

// import.meta.env is Vite's build-time substitution. The fallback keeps local
// dev working with no .env.local file at all.
// .trim() matters: pasting a URL into a hosting dashboard very easily picks
// up a trailing newline or space, which turns a valid address into one fetch
// rejects, with an error that says nothing about whitespace.
const RAW_API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8001").trim();

// Guard against a placeholder being deployed for real.
//
// Vite inlines this value at BUILD time, so a wrong VITE_API_URL produces a
// bundle that looks fine, loads fine, and then fails on every request with an
// opaque network error. Angle brackets are never valid in a URL, so their
// presence means documentation text ("https://<your-app>.onrender.com") was
// pasted into the environment variable instead of a real address. Detecting it
// here turns a mystifying failure into a message that names the actual fix.
const IS_PLACEHOLDER = /[<>]/.test(RAW_API_URL);

const API_URL = RAW_API_URL.replace(/\/$/, "");

/** Thrown for any failed request, carrying the HTTP status for the UI. */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Read a failed response and produce the best message available.
 *
 * @param {Response} response
 * @returns {Promise<ApiError>}
 */
async function toApiError(response) {
  let detail;
  try {
    const body = await response.json();
    // FastAPI validation errors arrive as an array of objects, not a string.
    detail = Array.isArray(body?.detail)
      ? body.detail.map((item) => item.msg).join(", ")
      : body?.detail;
  } catch {
    // Body was not JSON - a proxy error page, or an empty 502.
  }

  if (detail) return new ApiError(detail, response.status);
  if (response.status === 413) return new ApiError("That file is too large.", 413);
  if (response.status >= 500) {
    return new ApiError("The server had a problem. Please try again.", response.status);
  }
  return new ApiError(`Request failed (${response.status}).`, response.status);
}

/**
 * Fetch the roles a resume can be scored against.
 *
 * @param {AbortSignal} [signal]
 * @returns {Promise<Array>} roles with their weighted skill requirements
 */
export async function fetchRoles(signal) {
  assertConfigured();
  const response = await fetch(`${API_URL}/api/roles`, { signal });
  if (!response.ok) throw await toApiError(response);
  return response.json();
}

/**
 * Upload a resume and get the full analysis back.
 *
 * @param {File} file the PDF or DOCX the user chose
 * @param {string} targetRole a role_id from fetchRoles
 * @param {AbortSignal} [signal] lets the UI cancel if the user navigates away
 * @returns {Promise<Object>} the AnalysisResponse payload
 */
export async function analyzeResume(file, targetRole, signal) {
  assertConfigured();

  const form = new FormData();
  form.append("file", file);
  form.append("target_role", targetRole);

  let response;
  try {
    // No Content-Type header: the browser must set it itself so the multipart
    // boundary is included. Setting it manually is the classic 422 bug here.
    response = await fetch(`${API_URL}/api/analyze`, {
      method: "POST",
      body: form,
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    // fetch only rejects on network failure, so this is genuinely "no server".
    throw new ApiError(
      "Could not reach the server. Is the backend running on " + API_URL + "?",
      0,
    );
  }

  if (!response.ok) throw await toApiError(response);
  return response.json();
}

export { API_URL };

/**
 * Turn an analysis into a PDF and hand it to the browser as a download.
 *
 * The analysis is posted back rather than the file being re-uploaded: the
 * server already gave us this exact object, so the report endpoint stays
 * stateless and nothing is parsed twice.
 *
 * @param {Object} analysis the AnalysisResponse payload
 * @param {AbortSignal} [signal]
 * @returns {Promise<string>} the filename that was saved
 */
export async function downloadReport(analysis, signal) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(analysis),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError("Could not reach the server to build the report.", 0);
  }

  if (!response.ok) throw await toApiError(response);

  const blob = await response.blob();
  const filename = filenameFromDisposition(response.headers.get("Content-Disposition"));

  // Anchor-with-object-URL is the only way to name a download from fetched
  // bytes; the alternative, navigating to the URL, cannot send a POST body.
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();

  // Revoking immediately can cancel the download in Safari, so give the
  // browser a moment to start reading the blob first.
  setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000);

  return filename;
}

/**
 * Pull the filename out of a Content-Disposition header.
 *
 * @param {string|null} header
 * @returns {string} the server's filename, or a sensible fallback
 */
function filenameFromDisposition(header) {
  const match = header?.match(/filename="?([^";]+)"?/i);
  // Strip any path the header might carry: the download attribute would
  // otherwise be ignored by some browsers, or write somewhere unexpected.
  const name = match?.[1]?.split(/[\/]/).pop();
  return name || "resume-analysis.pdf";
}

/**
 * Throw a self-explaining error when the build was given a placeholder API URL.
 *
 * Called at the top of every request so the failure surfaces in the UI's normal
 * error card rather than as an unhandled network exception in the console.
 */
function assertConfigured() {
  if (!IS_PLACEHOLDER) return;
  throw new ApiError(
    `The site was built with a placeholder API address (${RAW_API_URL}). ` +
      "Set VITE_API_URL to the real backend URL in the hosting project's " +
      "environment variables, then redeploy - Vite bakes this value in at " +
      "build time, so changing it without rebuilding has no effect.",
    0,
  );
}
