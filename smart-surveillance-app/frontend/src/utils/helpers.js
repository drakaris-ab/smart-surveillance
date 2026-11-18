import { getConfig } from "../config";

/**
 * Normalizes snapshot image paths and constructs a full, valid web URL.
 * Handles Windows backslashes (\), bare filenames, missing leading slashes,
 * duplicate /snapshots prefixes, and port formatting.
 */
export function getSnapshotUrl(path) {
  if (!path || path === "N/A" || typeof path !== "string") return "";

  let clean = path.trim();
  if (!clean || clean === "N/A") return "";

  // 1. If already a full http:// or https:// URL, return as is
  if (clean.startsWith("http://") || clean.startsWith("https://")) {
    return clean;
  }

  // 2. Convert all backslashes (\) to forward slashes (/)
  clean = clean.replace(/\\/g, "/");

  // 3. Strip leading slashes to normalize
  clean = clean.replace(/^\/+/, "");

  // 4. Intelligently map bare filenames or relative subpaths
  // e.g. "alert_1_123.jpg" -> "snapshots/alerts/alert_1_123.jpg"
  // e.g. "camera_1_123.jpg" -> "snapshots/zone_setup/camera_1_123.jpg"
  // e.g. "alerts/alert_1_123.jpg" -> "snapshots/alerts/alert_1_123.jpg"
  if (!clean.startsWith("snapshots/")) {
    if (clean.startsWith("alerts/")) {
      clean = "snapshots/" + clean;
    } else if (clean.startsWith("zone_setup/")) {
      clean = "snapshots/" + clean;
    } else if (clean.startsWith("alert_")) {
      clean = "snapshots/alerts/" + clean;
    } else if (clean.startsWith("camera_")) {
      clean = "snapshots/zone_setup/" + clean;
    } else {
      clean = "snapshots/" + clean;
    }
  }

  // 5. Combine with API Base URL safely
  const config = getConfig();
  let baseUrl = (config && config.apiBaseUrl) || "http://localhost";

  // Strip trailing slash on baseUrl if present
  baseUrl = baseUrl.replace(/\/+$/, "");

  // If port is specified and baseUrl doesn't already contain a port (:digits)
  if (config && config.port && !baseUrl.match(/:\d+$/)) {
    baseUrl = `${baseUrl}:${config.port}`;
  }

  return `${baseUrl}/${clean}`;
}
