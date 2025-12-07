import React, { useState, useEffect } from 'react';
import { Modal, Button, Space, Typography, List, Breadcrumb, Input, Dropdown, message } from 'antd';
import { 
  PlusOutlined, 
  FolderOutlined, 
  FileTextOutlined, 
  ArrowLeftOutlined,
  FolderAddOutlined,
  EditOutlined,
  DeleteOutlined,
  MoreOutlined,
  ReloadOutlined,
  LockOutlined,
  DragOutlined
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { workflowAPI } from '../services/api';
import CreateKnowledgeBaseModal from './CreateKnowledgeBaseModal';

const { Title, Text } = Typography;

interface FolderStructure {
  [key: string]: {
    type: 'folder' | 'kb';
    name: string;
    parent: string | null;
    chunkCount?: number;
    actualKbName?: string; // KB의 실제 서버 폴더 이름 (이름 변경 추적용)
    isProtected?: boolean; // 🔒 비밀번호 보호 상태
  };
}

interface KnowledgeBaseManageModalProps {
  visible: boolean;
  onClose: () => void;
  onRefresh: () => void | Promise<void>;
}

/**
 * 지식 베이스 관리 모달 - 파일 시스템 형태
 */
const KnowledgeBaseManageModal: React.FC<KnowledgeBaseManageModalProps> = ({
  visible,
  onClose,
  onRefresh
}) => {
  const [currentPath, setCurrentPath] = useState<string>('root');
  const [folderStructure, setFolderStructure] = useState<FolderStructure>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [newFolderModalVisible, setNewFolderModalVisible] = useState<boolean>(false);
  const [newFolderName, setNewFolderName] = useState<string>('');
  const [renameModalVisible, setRenameModalVisible] = useState<boolean>(false);
  const [renameTarget, setRenameTarget] = useState<{ id: string; name: string } | null>(null);
  const [renameName, setRenameName] = useState<string>('');
  const [createKbModalVisible, setCreateKbModalVisible] = useState<boolean>(false);
  const [protectionModalVisible, setProtectionModalVisible] = useState<boolean>(false);
  const [protectionPassword, setProtectionPassword] = useState<string>('');
  const [protectionTarget, setProtectionTarget] = useState<{ id: string; type: 'folder' | 'kb'; name: string; isProtected: boolean } | null>(null);

  // 폴더 구조 로드
  useEffect(() => {
    if (visible) {
      loadFolderStructure();
    }
  }, [visible]);

  // 서버에서 실제 디렉토리 구조 로드
  const loadFolderStructure = async () => {
    try {
      setLoading(true);
      // 서버에서 실제 파일 시스템 구조 로드 (서버만 신뢰)
      const { structure: serverStructure } = await workflowAPI.getKnowledgeBaseStructure();
      
      console.log('서버에서 로드한 구조:', serverStructure);
      
      setFolderStructure(serverStructure);
    } catch (error) {
      console.error('폴더 구조 로드 실패:', error);
      message.error('폴더 구조를 불러오는데 실패했습니다.');
      setFolderStructure({});
    } finally {
      setLoading(false);
    }
  };

  // 새로고침 핸들러
  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      await loadFolderStructure();
      await onRefresh();
      message.success('새로고침 완료');
    } catch (error) {
      console.error('새로고침 실패:', error);
      message.error('새로고침에 실패했습니다.');
    } finally {
      setRefreshing(false);
    }
  };

  // 현재 경로의 항목들 가져오기
  const getCurrentItems = () => {
    const items: Array<{ id: string; type: 'folder' | 'kb'; name: string; chunkCount?: number }> = [];
    
    // 폴더 구조에서 현재 경로의 자식들 찾기
    Object.entries(folderStructure).forEach(([id, item]) => {
      if (item.parent === currentPath) {
        items.push({ id, ...item });
      }
    });

    // 서버에서 이미 모든 KB를 포함한 구조를 반환하므로 추가 로직 불필요
    // knowledgeBases는 백업용으로만 사용

    return items.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  };

  // Breadcrumb 경로 가져오기
  const getBreadcrumbPath = (): Array<{ id: string; name: string }> => {
    const path: Array<{ id: string; name: string }> = [{ id: 'root', name: 'knowledge_bases' }];
    let current = currentPath;

    while (current !== 'root' && folderStructure[current]) {
      path.unshift({ id: current, name: folderStructure[current].name });
      current = folderStructure[current].parent || 'root';
    }

    return path.reverse();
  };

  // 폴더 추가
  const handleAddFolder = async () => {
    if (!newFolderName.trim()) {
      message.warning('폴더 이름을 입력해주세요.');
      return;
    }

    // 중복 검사 - 현재 경로의 자식들 중에 같은 이름이 있는지 확인
    const hasDuplicate = Object.values(folderStructure).some(
      (item) => item.parent === currentPath && item.name === newFolderName.trim()
    );
    
    if (hasDuplicate) {
      message.error('같은 이름의 폴더나 지식 베이스가 이미 존재합니다.');
      return;
    }

    try {
      // 서버 경로 계산
      const buildServerPath = (folderId: string): string => {
        if (folderId === 'root') return '';
        const folder = folderStructure[folderId];
        if (!folder) return '';
        const parentPath = buildServerPath(folder.parent || 'root');
        return parentPath ? `${parentPath}/${folder.name}` : folder.name;
      };
      
      const parentServerPath = buildServerPath(currentPath);
      const fullServerPath = parentServerPath 
        ? `${parentServerPath}/${newFolderName}` 
        : newFolderName;

      // 서버에 폴더 생성
      await workflowAPI.createFolder(fullServerPath);

      // 서버 구조 재로드 (다른 사용자의 변경 사항 반영)
      await loadFolderStructure();

      setNewFolderName('');
      setNewFolderModalVisible(false);
      message.success('폴더가 추가되었습니다.');
    } catch (error: any) {
      console.error('Folder creation error:', error);
      message.error(error.response?.data?.detail || '폴더 생성에 실패했습니다.');
    }
  };

  // 이름 변경
  const handleRename = async () => {
    if (!renameTarget || !renameName.trim()) {
      message.warning('이름을 입력해주세요.');
      return;
    }

    const item = folderStructure[renameTarget.id];
    
    try {
      if (item.type === 'folder') {
        // 폴더 이름 변경 (서버 API 호출)
        const buildServerPath = (folderId: string): string => {
          if (folderId === 'root') return '';
          const folder = folderStructure[folderId];
          if (!folder) return '';
          const parentPath = buildServerPath(folder.parent || 'root');
          return parentPath ? `${parentPath}/${folder.name}` : folder.name;
        };
        
        const oldServerPath = buildServerPath(renameTarget.id);
        
        await workflowAPI.renameFolder(oldServerPath, renameName);
        
        // 서버 구조 재로드
        await loadFolderStructure();
        
        message.success('폴더 이름이 변경되었습니다.');
      } else {
        // KB 이름 변경 (서버 API 호출)
        const actualName = item.actualKbName || renameTarget.name;
        await workflowAPI.renameKnowledgeBase(actualName, renameName);
        
        // 서버 구조 재로드
        await loadFolderStructure();
        
        message.success('지식 베이스 이름이 변경되었습니다.');
      }
      
      setRenameTarget(null);
      setRenameName('');
      setRenameModalVisible(false);
    } catch (error: any) {
      console.error('Rename error:', error);
      message.error(error.response?.data?.detail || '이름 변경에 실패했습니다.');
    }
  };

  // 삭제
  const handleDelete = async (id: string, type: 'folder' | 'kb', name: string) => {
    if (type === 'folder') {
      // 폴더 삭제 - 서버 API 호출
      try {
        // 서버 경로 계산
        const buildServerPath = (folderId: string): string => {
          if (folderId === 'root') return '';
          const folder = folderStructure[folderId];
          if (!folder) return '';
          const parentPath = buildServerPath(folder.parent || 'root');
          return parentPath ? `${parentPath}/${folder.name}` : folder.name;
        };
        
        const serverPath = buildServerPath(id);
        
        console.log('Deleting folder:', { id, name, serverPath });
        
        // 서버에서 폴더 삭제 (내부 KB들도 함께)
        await workflowAPI.deleteFolder(serverPath);
        
        // 서버 구조 재로드 (다른 사용자의 변경 사항 반영)
        await loadFolderStructure();
        await onRefresh();
        message.success('폴더가 삭제되었습니다.');
      } catch (error: any) {
        console.error('Delete folder error:', error);
        message.error(error.response?.data?.detail || '폴더 삭제에 실패했습니다.');
      }
    } else {
      // KB 삭제 - 서버 API 호출
      try {
        const item = folderStructure[id];
        // 실제 서버 경로 계산
        const actualName = item?.actualKbName || name;
        
        console.log('Deleting KB:', { id, name, actualName, item });
        
        await workflowAPI.deleteKnowledgeBase(actualName);
        
        // 서버 구조 재로드
        await loadFolderStructure();
        await onRefresh();
        message.success('지식 베이스가 삭제되었습니다.');
      } catch (error: any) {
        console.error('Delete KB error:', error);
        message.error(error.response?.data?.detail || '지식 베이스 삭제에 실패했습니다.');
      }
    }
  };

  // 항목 더블클릭
  const handleDoubleClick = (id: string, type: 'folder' | 'kb') => {
    if (type === 'folder') {
      setCurrentPath(id);
    }
  };

  // 항목 이동
  const handleMove = async (id: string, type: 'folder' | 'kb', name: string) => {
    // 이동 가능한 폴더 목록 생성
    const folders: Array<{ id: string; name: string; path: string; serverPath: string }> = [
      { id: 'root', name: 'knowledge_bases', path: 'knowledge_bases', serverPath: '' }
    ];
    
    const buildFolderPath = (folderId: string): string => {
      if (folderId === 'root') return 'knowledge_bases';
      const folder = folderStructure[folderId];
      if (!folder) return '';
      const parentPath = buildFolderPath(folder.parent || 'root');
      return `${parentPath}/${folder.name}`;
    };
    
    const buildServerPath = (folderId: string): string => {
      if (folderId === 'root') return '';
      const folder = folderStructure[folderId];
      if (!folder) return '';
      const parentPath = buildServerPath(folder.parent || 'root');
      return parentPath ? `${parentPath}/${folder.name}` : folder.name;
    };
    
    Object.entries(folderStructure).forEach(([fid, item]) => {
      if (item.type === 'folder' && fid !== id) {
        folders.push({
          id: fid,
          name: item.name,
          path: buildFolderPath(fid),
          serverPath: buildServerPath(fid)
        });
      }
    });
    
    // 이동 모달 표시
    Modal.confirm({
      title: `${type === 'folder' ? '폴더' : '지식 베이스'} 이동`,
      content: (
        <div>
          <p>"{name}"을(를) 어디로 이동하시겠습니까?</p>
          <select id="move-target-select" style={{ width: '100%', padding: '4px' }}>
            {folders.map(f => (
              <option key={f.id} value={f.id}>{f.path}</option>
            ))}
          </select>
        </div>
      ),
      onOk: async () => {
        const select = document.getElementById('move-target-select') as HTMLSelectElement;
        const targetId = select?.value || 'root';
        const targetFolder = folders.find(f => f.id === targetId);
        
        if (type === 'kb') {
          // KB 이동 - 서버 API 호출
          try {
            const item = folderStructure[id];
            // 실제 서버 경로 계산
            const actualName = item?.actualKbName || name;
            
            console.log('Moving KB:', { id, name, actualName, targetFolder: targetFolder?.serverPath });
            
            await workflowAPI.moveKnowledgeBase(actualName, targetFolder?.serverPath || '');
            
            // 서버 구조 재로드
            await loadFolderStructure();
            await onRefresh();
            message.success('지식 베이스가 이동되었습니다.');
          } catch (error: any) {
            console.error('Move KB error:', error);
            message.error(error.response?.data?.detail || '지식 베이스 이동에 실패했습니다.');
          }
        } else {
          // 폴더 이동 - 서버 API 호출
          try {
            // 서버 경로 계산
            const buildServerPath = (folderId: string): string => {
              if (folderId === 'root') return '';
              const folder = folderStructure[folderId];
              if (!folder) return '';
              const parentPath = buildServerPath(folder.parent || 'root');
              return parentPath ? `${parentPath}/${folder.name}` : folder.name;
            };
            
            const oldServerPath = buildServerPath(id);
            
            console.log('Moving folder:', { id, name, oldServerPath, targetFolder: targetFolder?.serverPath });
            
            await workflowAPI.moveFolder(oldServerPath, targetFolder?.serverPath || '');
            
            // 서버 구조 재로드
            await loadFolderStructure();
            message.success('폴더가 이동되었습니다.');
          } catch (error: any) {
            console.error('Move folder error:', error);
            message.error(error.response?.data?.detail || '폴더 이동에 실패했습니다.');
          }
        }
      }
    });
  };

  // 보호/보호 해제 핸들러
  const handleProtection = async () => {
    if (!protectionTarget || !protectionPassword) {
      message.error('비밀번호를 입력하세요.');
      return;
    }

    try {
      const item = folderStructure[protectionTarget.id];
      const path = item.type === 'folder' 
        ? getRelativePath(protectionTarget.id)
        : item.actualKbName || item.name;

      if (protectionTarget.isProtected) {
        // 보호 해제
        if (item.type === 'folder') {
          await workflowAPI.unprotectFolder(path, protectionPassword);
        } else {
          await workflowAPI.unprotectKnowledgeBase(path, protectionPassword);
        }
        message.success(`"${protectionTarget.name}" 보호가 해제되었습니다.`);
      } else {
        // 보호 설정
        if (item.type === 'folder') {
          await workflowAPI.protectFolder(path, protectionPassword);
        } else {
          await workflowAPI.protectKnowledgeBase(path, protectionPassword);
        }
        message.success(`"${protectionTarget.name}"이(가) 보호되었습니다.`);
      }

      setProtectionModalVisible(false);
      setProtectionPassword('');
      setProtectionTarget(null);
      await loadFolderStructure();
      await onRefresh();
    } catch (error: any) {
      console.error('보호 설정/해제 실패:', error);
      const errorMsg = error.response?.data?.detail || error.message || '작업에 실패했습니다.';
      message.error(errorMsg);
    }
  };

  // 상대 경로 계산 헬퍼
  const getRelativePath = (id: string): string => {
    const path: string[] = [];
    let current = id;
    
    while (current !== 'root' && folderStructure[current]) {
      path.unshift(folderStructure[current].name);
      current = folderStructure[current].parent || 'root';
    }
    
    return path.join('/');
  };

  // 컨텍스트 메뉴
  const getContextMenu = (id: string, type: 'folder' | 'kb', name: string): MenuProps => {
    const item = folderStructure[id];
    const isProtected = item?.isProtected || false;

    return {
    items: [
      {
        key: 'rename',
        icon: <EditOutlined />,
        label: '이름 변경',
        onClick: () => {
          setRenameTarget({ id, name });
          setRenameName(name);
          setRenameModalVisible(true);
        }
      },
      {
        key: 'move',
        icon: <DragOutlined />,
        label: '이동',
        onClick: () => handleMove(id, type, name)
      },
      {
        key: 'protection',
        icon: <LockOutlined />,
        label: isProtected ? '보호 해제' : '보호',
        onClick: () => {
          setProtectionTarget({ id, type, name, isProtected });
          setProtectionPassword('');
          setProtectionModalVisible(true);
        }
      },
      {
        key: 'delete',
        icon: <DeleteOutlined />,
        label: '삭제',
        danger: true,
        onClick: () => {
          Modal.confirm({
            title: `${type === 'folder' ? '폴더' : '지식 베이스'} 삭제`,
            content: `"${name}"을(를) 삭제하시겠습니까?`,
            onOk: () => handleDelete(id, type, name)
          });
        }
      }
    ]
  };
  };

  const items = getCurrentItems();
  const breadcrumbPath = getBreadcrumbPath();

  return (
    <>
      <Modal
        title={<Title level={4} style={{ margin: 0 }}>지식 베이스 관리</Title>}
        open={visible}
        onCancel={onClose}
        width={800}
        footer={
          <Button onClick={onClose}>닫기</Button>
        }
        destroyOnClose
      >
        {/* 네비게이션 */}
        <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space>
              <Button
                icon={<ArrowLeftOutlined />}
                disabled={currentPath === 'root'}
                onClick={() => {
                  const parent = folderStructure[currentPath]?.parent || 'root';
                  setCurrentPath(parent);
                }}
              >
                뒤로
              </Button>
              <Button
                icon={<ReloadOutlined spin={refreshing || loading} />}
                onClick={handleRefresh}
                loading={refreshing || loading}
              >
                새로고침
              </Button>
              <Breadcrumb
                items={breadcrumbPath.map((item) => ({
                  title: item.name,
                  onClick: () => setCurrentPath(item.id),
                  style: { cursor: 'pointer' }
                }))}
              />
            </Space>
          </Space>

          {/* 액션 버튼들 */}
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateKbModalVisible(true)}
            >
              지식 베이스 추가
            </Button>
            <Button
              icon={<FolderAddOutlined />}
              onClick={() => setNewFolderModalVisible(true)}
            >
              폴더 추가
            </Button>
          </Space>
        </Space>

        {/* 항목 리스트 */}
        <List
          bordered
          style={{ minHeight: 400, maxHeight: 500, overflow: 'auto' }}
          dataSource={items}
          locale={{ emptyText: '항목이 없습니다.' }}
          renderItem={(item) => (
            <List.Item
              style={{ cursor: 'pointer', padding: '12px 16px' }}
              onDoubleClick={() => handleDoubleClick(item.id, item.type)}
              actions={[
                <Dropdown menu={getContextMenu(item.id, item.type, item.name)} trigger={['click']}>
                  <Button type="text" icon={<MoreOutlined />} />
                </Dropdown>
              ]}
            >
              <Space>
                {item.type === 'folder' ? (
                  <FolderOutlined style={{ fontSize: 20, color: '#faad14' }} />
                ) : (
                  <FileTextOutlined style={{ fontSize: 20, color: '#1890ff' }} />
                )}
                <div>
                  <Space>
                    <Text strong>{item.name}</Text>
                    {folderStructure[item.id]?.isProtected && (
                      <LockOutlined style={{ color: '#52c41a', fontSize: 16 }} title="보호됨" />
                    )}
                  </Space>
                  {item.chunkCount !== undefined && (
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                      ({item.chunkCount}개 청크)
                    </Text>
                  )}
                </div>
              </Space>
            </List.Item>
          )}
        />
      </Modal>

      {/* 폴더 추가 모달 */}
      <Modal
        title="폴더 추가"
        open={newFolderModalVisible}
        onOk={handleAddFolder}
        onCancel={() => {
          setNewFolderModalVisible(false);
          setNewFolderName('');
        }}
        okText="추가"
        cancelText="취소"
        zIndex={2000}
      >
        <Input
          placeholder="폴더 이름을 입력하세요"
          value={newFolderName}
          onChange={(e) => setNewFolderName(e.target.value)}
          onPressEnter={handleAddFolder}
          autoFocus
        />
      </Modal>

      {/* 이름 변경 모달 */}
      <Modal
        title="이름 변경"
        open={renameModalVisible}
        onOk={handleRename}
        onCancel={() => {
          setRenameModalVisible(false);
          setRenameTarget(null);
          setRenameName('');
        }}
        okText="변경"
        cancelText="취소"
        zIndex={2000}
      >
        <Input
          placeholder="새 이름을 입력하세요"
          value={renameName}
          onChange={(e) => setRenameName(e.target.value)}
          onPressEnter={handleRename}
          autoFocus
        />
      </Modal>

      {/* 보호/보호 해제 모달 */}
      <Modal
        title={
          <Space>
            <LockOutlined />
            {protectionTarget?.isProtected ? '보호 해제' : '보호 설정'}
          </Space>
        }
        open={protectionModalVisible}
        onOk={handleProtection}
        onCancel={() => {
          setProtectionModalVisible(false);
          setProtectionPassword('');
          setProtectionTarget(null);
        }}
        okText={protectionTarget?.isProtected ? '해제' : '설정'}
        cancelText="취소"
        zIndex={2000}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>
            {protectionTarget?.isProtected 
              ? `"${protectionTarget.name}"의 보호를 해제하려면 비밀번호를 입력하세요.`
              : `"${protectionTarget?.name}"을(를) 보호하려면 비밀번호를 설정하세요.`
            }
          </Text>
          <Input.Password
            placeholder="비밀번호"
            value={protectionPassword}
            onChange={(e) => setProtectionPassword(e.target.value)}
            onPressEnter={handleProtection}
            autoFocus
            autoComplete="off"
          />
          {!protectionTarget?.isProtected && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              * 보호된 항목은 이동, 이름 변경, 삭제가 불가능합니다.
            </Text>
          )}
        </Space>
      </Modal>

      {/* 지식 베이스 생성 모달 */}
      <CreateKnowledgeBaseModal
        visible={createKbModalVisible}
        onClose={() => setCreateKbModalVisible(false)}
        onSuccess={async () => {
          await loadFolderStructure();
          await onRefresh();
        }}
        currentFolder={currentPath === 'root' ? '' : (() => {
          // 현재 경로의 서버 경로 계산
          const buildServerPath = (folderId: string): string => {
            if (folderId === 'root') return '';
            const folder = folderStructure[folderId];
            if (!folder) return '';
            const parentPath = buildServerPath(folder.parent || 'root');
            return parentPath ? `${parentPath}/${folder.name}` : folder.name;
          };
          return buildServerPath(currentPath);
        })()}
      />
    </>
  );
};

export default KnowledgeBaseManageModal;
