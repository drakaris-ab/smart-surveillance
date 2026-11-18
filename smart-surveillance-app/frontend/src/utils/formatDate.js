/**
 * Format a date string or Date object into a readable format.
 * @param {string|Date} input - Date string or Date object
 * @param {object} options - Intl.DateTimeFormat options
 * @returns {string} formatted date string
 */
export const formatDate = (input, options = {}) => {
  if (!input) return '';

  const date = typeof input === 'string' ? new Date(input) : input;

  // Default cinematic format: "02 Dec 2025, 21:20"
  const defaultOptions = {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    ...options,
  };

  return new Intl.DateTimeFormat('en-GB', defaultOptions).format(date);
};

/**
 * Format only the date (no time).
 * Example: "02 Dec 2025"
 */
export const formatDateOnly = (input) => {
  return formatDate(input, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

/**
 * Format only the time.
 * Example: "21:20"
 */
export const formatTimeOnly = (input) => {
  return formatDate(input, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
};
