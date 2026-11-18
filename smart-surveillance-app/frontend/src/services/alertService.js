import { useContext } from 'react';
import { MessageContext } from '../context/MessageContext';

/**
 * AlertService provides reusable helpers for triggering alerts
 * by wrapping the existing MessageContext to maintain standard architecture.
 */
export default function useAlertService() {
  const { showMessage } = useContext(MessageContext);

  const success = (message) => {
    showMessage('success', message);
  };

  const error = (message) => {
    showMessage('error', message);
  };

  const warning = (message) => {
    showMessage('warning', message);
  };

  const info = (message) => {
    showMessage('info', message);
  };

  return { success, error, warning, info };
}
