import { message } from 'antd';
import { UI_CONFIG } from '../config/constants';

/**
 * 성공 메시지 표시
 */
export const showSuccessMessage = (content: string): void => {
  message.success({
    content,
    duration: UI_CONFIG.MESSAGE_DURATION,
  });
};

/**
 * 에러 메시지 표시
 */
export const showErrorMessage = (content: string): void => {
  message.error({
    content,
    duration: UI_CONFIG.MESSAGE_DURATION,
  });
};

/**
 * 정보 메시지 표시
 */
export const showInfoMessage = (content: string): void => {
  message.info({
    content,
    duration: UI_CONFIG.MESSAGE_DURATION,
  });
};