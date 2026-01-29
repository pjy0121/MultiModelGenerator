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
    actualKbName?: string; // Actual server folder name of KB (for name change tracking)
    isProtected?: boolean; // Password protection status
  };
}

interface KnowledgeBaseManageModalProps {
  visible: boolean;
  onClose: () => void;
  onRefresh: () => void | Promise<void>;
}

/**
 * Knowledge Base Management Modal - File system style
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

  // Load folder structure
  useEffect(() => {
    if (visible) {
      loadFolderStructure();
    }
  }, [visible]);

  // Load actual directory structure from server
  const loadFolderStructure = async () => {
    try {
      setLoading(true);
      // Load actual file system structure from server (trust server only)
      const { structure: serverStructure } = await workflowAPI.getKnowledgeBaseStructure();

      console.log('Structure loaded from server:', serverStructure);

      setFolderStructure(serverStructure);
    } catch (error) {
      console.error('Failed to load folder structure:', error);
      message.error('Failed to load folder structure.');
      setFolderStructure({});
    } finally {
      setLoading(false);
    }
  };

  // Refresh handler
  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      await loadFolderStructure();
      await onRefresh();
      message.success('Refresh complete');
    } catch (error) {
      console.error('Refresh failed:', error);
      message.error('Failed to refresh.');
    } finally {
      setRefreshing(false);
    }
  };

  // Get items in current path
  const getCurrentItems = () => {
    const items: Array<{ id: string; type: 'folder' | 'kb'; name: string; chunkCount?: number }> = [];

    // Find children of current path in folder structure
    Object.entries(folderStructure).forEach(([id, item]) => {
      if (item.parent === currentPath) {
        items.push({ id, ...item });
      }
    });

    // No additional logic needed as server returns structure with all KBs included
    // knowledgeBases is only used as backup

    return items.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  };

  // Get breadcrumb path
  const getBreadcrumbPath = (): Array<{ id: string; name: string }> => {
    const path: Array<{ id: string; name: string }> = [{ id: 'root', name: 'knowledge_bases' }];
    let current = currentPath;

    while (current !== 'root' && folderStructure[current]) {
      path.unshift({ id: current, name: folderStructure[current].name });
      current = folderStructure[current].parent || 'root';
    }

    return path.reverse();
  };

  // Add folder
  const handleAddFolder = async () => {
    if (!newFolderName.trim()) {
      message.warning('Please enter folder name.');
      return;
    }

    // Check for duplicates - check if same name exists among children of current path
    const hasDuplicate = Object.values(folderStructure).some(
      (item) => item.parent === currentPath && item.name === newFolderName.trim()
    );

    if (hasDuplicate) {
      message.error('A folder or knowledge base with the same name already exists.');
      return;
    }

    try {
      // Calculate server path
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

      // Create folder on server
      await workflowAPI.createFolder(fullServerPath);

      // Reload server structure (reflect changes by other users)
      await loadFolderStructure();

      setNewFolderName('');
      setNewFolderModalVisible(false);
      message.success('Folder added.');
    } catch (error: any) {
      console.error('Folder creation error:', error);
      message.error(error.response?.data?.detail || 'Failed to create folder.');
    }
  };

  // Rename
  const handleRename = async () => {
    if (!renameTarget || !renameName.trim()) {
      message.warning('Please enter a name.');
      return;
    }

    const item = folderStructure[renameTarget.id];

    try {
      if (item.type === 'folder') {
        // Rename folder (server API call)
        const buildServerPath = (folderId: string): string => {
          if (folderId === 'root') return '';
          const folder = folderStructure[folderId];
          if (!folder) return '';
          const parentPath = buildServerPath(folder.parent || 'root');
          return parentPath ? `${parentPath}/${folder.name}` : folder.name;
        };

        const oldServerPath = buildServerPath(renameTarget.id);

        await workflowAPI.renameFolder(oldServerPath, renameName);

        // Reload server structure
        await loadFolderStructure();

        message.success('Folder renamed.');
      } else {
        // Rename KB (server API call)
        const actualName = item.actualKbName || renameTarget.name;
        await workflowAPI.renameKnowledgeBase(actualName, renameName);

        // Reload server structure
        await loadFolderStructure();

        message.success('Knowledge base renamed.');
      }

      setRenameTarget(null);
      setRenameName('');
      setRenameModalVisible(false);
    } catch (error: any) {
      console.error('Rename error:', error);
      message.error(error.response?.data?.detail || 'Failed to rename.');
    }
  };

  // Delete
  const handleDelete = async (id: string, type: 'folder' | 'kb', name: string) => {
    if (type === 'folder') {
      // Delete folder - server API call
      try {
        // Calculate server path
        const buildServerPath = (folderId: string): string => {
          if (folderId === 'root') return '';
          const folder = folderStructure[folderId];
          if (!folder) return '';
          const parentPath = buildServerPath(folder.parent || 'root');
          return parentPath ? `${parentPath}/${folder.name}` : folder.name;
        };

        const serverPath = buildServerPath(id);

        console.log('Deleting folder:', { id, name, serverPath });

        // Delete folder on server (including internal KBs)
        await workflowAPI.deleteFolder(serverPath);

        // Reload server structure (reflect changes by other users)
        await loadFolderStructure();
        await onRefresh();
        message.success('Folder deleted.');
      } catch (error: any) {
        console.error('Delete folder error:', error);
        message.error(error.response?.data?.detail || 'Failed to delete folder.');
      }
    } else {
      // Delete KB - server API call
      try {
        const item = folderStructure[id];
        // Calculate actual server path
        const actualName = item?.actualKbName || name;

        console.log('Deleting KB:', { id, name, actualName, item });

        await workflowAPI.deleteKnowledgeBase(actualName);

        // Reload server structure
        await loadFolderStructure();
        await onRefresh();
        message.success('Knowledge base deleted.');
      } catch (error: any) {
        console.error('Delete KB error:', error);
        message.error(error.response?.data?.detail || 'Failed to delete knowledge base.');
      }
    }
  };

  // Item double click
  const handleDoubleClick = (id: string, type: 'folder' | 'kb') => {
    if (type === 'folder') {
      setCurrentPath(id);
    }
  };

  // Move item
  const handleMove = async (id: string, type: 'folder' | 'kb', name: string) => {
    // Create list of movable folders
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

    // Show move modal
    Modal.confirm({
      title: `Move ${type === 'folder' ? 'Folder' : 'Knowledge Base'}`,
      content: (
        <div>
          <p>Where would you like to move "{name}"?</p>
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
          // Move KB - server API call
          try {
            const item = folderStructure[id];
            // Calculate actual server path
            const actualName = item?.actualKbName || name;

            console.log('Moving KB:', { id, name, actualName, targetFolder: targetFolder?.serverPath });

            await workflowAPI.moveKnowledgeBase(actualName, targetFolder?.serverPath || '');

            // Reload server structure
            await loadFolderStructure();
            await onRefresh();
            message.success('Knowledge base moved.');
          } catch (error: any) {
            console.error('Move KB error:', error);
            message.error(error.response?.data?.detail || 'Failed to move knowledge base.');
          }
        } else {
          // Move folder - server API call
          try {
            // Calculate server path
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

            // Reload server structure
            await loadFolderStructure();
            message.success('Folder moved.');
          } catch (error: any) {
            console.error('Move folder error:', error);
            message.error(error.response?.data?.detail || 'Failed to move folder.');
          }
        }
      }
    });
  };

  // Protection/unprotection handler
  const handleProtection = async () => {
    if (!protectionTarget || !protectionPassword) {
      message.error('Please enter password.');
      return;
    }

    try {
      const item = folderStructure[protectionTarget.id];
      const path = item.type === 'folder'
        ? getRelativePath(protectionTarget.id)
        : item.actualKbName || item.name;

      if (protectionTarget.isProtected) {
        // Remove protection
        if (item.type === 'folder') {
          await workflowAPI.unprotectFolder(path, protectionPassword);
        } else {
          await workflowAPI.unprotectKnowledgeBase(path, protectionPassword);
        }
        message.success(`Protection removed from "${protectionTarget.name}".`);
      } else {
        // Set protection
        if (item.type === 'folder') {
          await workflowAPI.protectFolder(path, protectionPassword);
        } else {
          await workflowAPI.protectKnowledgeBase(path, protectionPassword);
        }
        message.success(`"${protectionTarget.name}" is now protected.`);
      }

      setProtectionModalVisible(false);
      setProtectionPassword('');
      setProtectionTarget(null);
      await loadFolderStructure();
      await onRefresh();
    } catch (error: any) {
      console.error('Protection setting/removal failed:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Operation failed.';
      message.error(errorMsg);
    }
  };

  // Relative path calculation helper
  const getRelativePath = (id: string): string => {
    const path: string[] = [];
    let current = id;

    while (current !== 'root' && folderStructure[current]) {
      path.unshift(folderStructure[current].name);
      current = folderStructure[current].parent || 'root';
    }

    return path.join('/');
  };

  // Context menu
  const getContextMenu = (id: string, type: 'folder' | 'kb', name: string): MenuProps => {
    const item = folderStructure[id];
    const isProtected = item?.isProtected || false;

    return {
      items: [
        {
          key: 'rename',
          icon: <EditOutlined />,
          label: 'Rename',
          onClick: () => {
            setRenameTarget({ id, name });
            setRenameName(name);
            setRenameModalVisible(true);
          }
        },
        {
          key: 'move',
          icon: <DragOutlined />,
          label: 'Move',
          onClick: () => handleMove(id, type, name)
        },
        {
          key: 'protection',
          icon: <LockOutlined />,
          label: isProtected ? 'Unprotect' : 'Protect',
          onClick: () => {
            setProtectionTarget({ id, type, name, isProtected });
            setProtectionPassword('');
            setProtectionModalVisible(true);
          }
        },
        {
          key: 'delete',
          icon: <DeleteOutlined />,
          label: 'Delete',
          danger: true,
          onClick: () => {
            Modal.confirm({
              title: `Delete ${type === 'folder' ? 'Folder' : 'Knowledge Base'}`,
              content: `Are you sure you want to delete "${name}"?`,
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
        title={<Title level={4} style={{ margin: 0 }}>Manage Knowledge Bases</Title>}
        open={visible}
        onCancel={onClose}
        width={800}
        footer={
          <Button onClick={onClose}>Close</Button>
        }
        destroyOnClose
      >
        {/* Navigation */}
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
                Back
              </Button>
              <Button
                icon={<ReloadOutlined spin={refreshing || loading} />}
                onClick={handleRefresh}
                loading={refreshing || loading}
              >
                Refresh
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

          {/* Action buttons */}
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateKbModalVisible(true)}
            >
              Add Knowledge Base
            </Button>
            <Button
              icon={<FolderAddOutlined />}
              onClick={() => setNewFolderModalVisible(true)}
            >
              Add Folder
            </Button>
          </Space>
        </Space>

        {/* Item list */}
        <List
          bordered
          style={{ minHeight: 400, maxHeight: 500, overflow: 'auto' }}
          dataSource={items}
          locale={{ emptyText: 'No items.' }}
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
                      <LockOutlined style={{ color: '#52c41a', fontSize: 16 }} title="Protected" />
                    )}
                  </Space>
                  {item.chunkCount !== undefined && (
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                      ({item.chunkCount} chunks)
                    </Text>
                  )}
                </div>
              </Space>
            </List.Item>
          )}
        />
      </Modal>

      {/* Add folder modal */}
      <Modal
        title="Add Folder"
        open={newFolderModalVisible}
        onOk={handleAddFolder}
        onCancel={() => {
          setNewFolderModalVisible(false);
          setNewFolderName('');
        }}
        okText="Add"
        cancelText="Cancel"
        zIndex={2000}
      >
        <Input
          placeholder="Enter folder name"
          value={newFolderName}
          onChange={(e) => setNewFolderName(e.target.value)}
          onPressEnter={handleAddFolder}
          autoFocus
        />
      </Modal>

      {/* Rename modal */}
      <Modal
        title="Rename"
        open={renameModalVisible}
        onOk={handleRename}
        onCancel={() => {
          setRenameModalVisible(false);
          setRenameTarget(null);
          setRenameName('');
        }}
        okText="Rename"
        cancelText="Cancel"
        zIndex={2000}
      >
        <Input
          placeholder="Enter new name"
          value={renameName}
          onChange={(e) => setRenameName(e.target.value)}
          onPressEnter={handleRename}
          autoFocus
        />
      </Modal>

      {/* Protection/unprotection modal */}
      <Modal
        title={
          <Space>
            <LockOutlined />
            {protectionTarget?.isProtected ? 'Remove Protection' : 'Set Protection'}
          </Space>
        }
        open={protectionModalVisible}
        onOk={handleProtection}
        onCancel={() => {
          setProtectionModalVisible(false);
          setProtectionPassword('');
          setProtectionTarget(null);
        }}
        okText={protectionTarget?.isProtected ? 'Remove' : 'Set'}
        cancelText="Cancel"
        zIndex={2000}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>
            {protectionTarget?.isProtected
              ? `Enter password to remove protection from "${protectionTarget.name}".`
              : `Set a password to protect "${protectionTarget?.name}".`
            }
          </Text>
          <Input.Password
            placeholder="Password"
            value={protectionPassword}
            onChange={(e) => setProtectionPassword(e.target.value)}
            onPressEnter={handleProtection}
            autoFocus
            autoComplete="off"
          />
          {!protectionTarget?.isProtected && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              * Protected items cannot be moved, renamed, or deleted.
            </Text>
          )}
        </Space>
      </Modal>

      {/* Knowledge base creation modal */}
      <CreateKnowledgeBaseModal
        visible={createKbModalVisible}
        onClose={() => setCreateKbModalVisible(false)}
        onSuccess={async () => {
          await loadFolderStructure();
          await onRefresh();
        }}
        currentFolder={currentPath === 'root' ? '' : (() => {
          // Calculate server path for current path
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
