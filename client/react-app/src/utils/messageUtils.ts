import { message, notification } from 'antd';
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
 * notification을 사용하여 닫기 버튼이 있는 지속적인 에러 메시지 표시
 */
export const showErrorMessage = (content: string): void => {
  const key = `error-${Date.now()}`;
  
  notification.error({
    message: '오류',
    description: content,
    key,
    duration: 0, // 자동으로 사라지지 않음
    placement: 'topRight',
    closable: true, // 닫기 버튼 표시
    style: {
      cursor: 'pointer'
    },
    onClick: () => {
      notification.destroy(key);
    }
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