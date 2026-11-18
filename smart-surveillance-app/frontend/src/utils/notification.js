/**
 * Request permission for browser notifications.
 */
export const requestNotificationPermission = async () => {
  if (!('Notification' in window)) {
    console.warn('This browser does not support notifications.');
    return false;
  }

  const permission = await Notification.requestPermission();
  return permission === 'granted';
};

/**
 * Show a notification with given title and options.
 * @param {string} title - Notification title
 * @param {object} options - Notification options (body, icon, tag, etc.)
 */
export const showNotification = (title, options = {}) => {
  if (!('Notification' in window)) return;

  if (Notification.permission === 'granted') {
    new Notification(title, {
      body: options.body || '',
      icon: options.icon || '/icons/notification.png',
      tag: options.tag || Date.now(),
    });
  }
};

/**
 * Convenience helpers for different notification types.
 */
export const notifySuccess = (message) => {
  showNotification('✅ Success', { body: message });
};

export const notifyError = (message) => {
  showNotification('❌ Error', { body: message });
};

export const notifyWarning = (message) => {
  showNotification('⚠️ Warning', { body: message });
};

export const notifyInfo = (message) => {
  showNotification('ℹ️ Info', { body: message });
};
