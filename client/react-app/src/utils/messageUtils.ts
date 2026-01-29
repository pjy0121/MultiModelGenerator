import { message, notification } from 'antd';
import { UI_CONFIG } from '../config/constants';

/**
 * Display success message
 */
export const showSuccessMessage = (content: string): void => {
  message.success({
    content,
    duration: UI_CONFIG.MESSAGE_DURATION,
  });
};

/**
 * Display error message (shown until user manually closes)
 * Uses notification for persistent error message with close button
 */
export const showErrorMessage = (content: string): void => {
  const key = `error-${Date.now()}`;

  notification.error({
    message: 'Error',
    description: content,
    key,
    duration: 0, // Does not auto-dismiss
    placement: 'topRight',
    closable: true, // Show close button
    style: {
      cursor: 'pointer'
    },
    onClick: () => {
      notification.destroy(key);
    }
  });
};

/**
 * Display info message
 */
export const showInfoMessage = (content: string): void => {
  message.info({
    content,
    duration: UI_CONFIG.MESSAGE_DURATION,
  });
};
