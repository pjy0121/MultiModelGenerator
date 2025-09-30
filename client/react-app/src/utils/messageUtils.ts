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
 * 에러 메시지 표시 (사용자가 직접 닫을 때까지 표시)
 */
export const showErrorMessage = (content: string): void => {
  message.error({
    content,
    duration: 0, // 자동으로 사라지지 않음, 사용자가 직접 닫아야 함
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