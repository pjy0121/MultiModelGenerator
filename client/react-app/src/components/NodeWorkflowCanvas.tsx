import React, { useCallback, useEffect, useState, memo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Connection,
  Edge,
  NodeTypes
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { 
  message, 
  Button, 
  Modal, 
  Input, 
  Typography,
  Space 
} from 'antd';
import {
  FileTextOutlined,
  RobotOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  SearchOutlined,
  SaveOutlined,
  ReloadOutlined,
  ClearOutlined,
  DownloadOutlined,
  UploadOutlined,
  PlayCircleOutlined, // 실행 아이콘 추가
  StopOutlined, // 중단 아이콘 추가
} from '@ant-design/icons';
import { NodeWorkflowComponent } from './NodeWorkflowComponent';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';
import { useNodeSelectionStore } from '../store/nodeSelectionStore';
import { useViewportStore } from '../store/viewportStore';
import { WorkflowEdge, NodeType } from '../types';
import { isConnectionAllowed } from '../utils/nodeWorkflowValidation';
import { UI_CONFIG, UI_COLORS } from '../config/constants';



// 노드 타입 정의 - 메모이제이션으로 재생성 방지
const nodeTypes: NodeTypes = {
  workflowNode: NodeWorkflowComponent,
};

// 에지 타입 정의 - 기본값을 명시적으로 정의하여 재생성 방지
const edgeTypes = {};

// fitView 옵션 - 재생성 방지
const fitViewOptions = { padding: UI_CONFIG.REACT_FLOW.FIT_VIEW_PADDING };

// ReactFlow 스타일 - 재생성 방지
const reactFlowStyle = { background: UI_CONFIG.REACT_FLOW.BACKGROUND_COLOR };

export const NodeWorkflowCanvas: React.FC = memo(() => {
  const {
    nodes: storeNodes, 
    edges: storeEdges, 
    isRestoring, // 복원 상태
    addEdge: addStoreEdge,
    removeEdge,
    removeNode,
    
    // 노드 추가와 워크플로우 관리 함수들
    addNode,
    saveCurrentWorkflow,
    restoreWorkflow,
    resetToInitialState,
    exportToJSON,
    importFromJSON,
    updateNodePositions,
    executeWorkflowStream, // 워크플로우 스트리밍 실행 함수
    stopWorkflowExecution, // 워크플로우 중단 함수
    isExecuting, // 실행 상태
    isStopping, // 중단 상태
  } = useNodeWorkflowStore();
  
  const { selectedNodeId, setSelectedNodeId } = useNodeSelectionStore();
  const { viewport, setViewport } = useViewportStore();  // 워크플로우 관리 상태
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [jsonText, setJsonText] = useState('');
  
  // 스트리밍 실행 핸들러
  const handleStreamingExecution = async () => {
    try {
      await executeWorkflowStream(() => {
        // 스트리밍 데이터는 이미 store에서 처리되므로 추가 처리 불필요
      });
    } catch (error) {
      console.error('스트리밍 실행 오류:', error);
      message.error(`스트리밍 실행 실패: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  // 워크플로우 중단 핸들러
  const handleStopExecution = async () => {
    // 이미 중단 중이면 아무것도 하지 않음
    if (isStopping) return;
    await stopWorkflowExecution();
  };

  // ReactFlow 인스턴스 레퍼런스
  const [reactFlowInstance, setReactFlowInstance] = React.useState<any>(null);
  
  // 자동 복원 상태 관리
  const [hasAutoRestored, setHasAutoRestored] = React.useState(false);

  // ReactFlow 초기화 핸들러
  const onInit = useCallback((instance: any) => {
    setReactFlowInstance(instance);
    
    // 앱 시작 시 자동 복원 (인스턴스 생성 후 1회만)
    if (!hasAutoRestored) {
      const success = restoreWorkflow();
      if (success) {
        // 복원된 뷰포트를 잠시 후 적용 (ReactFlow 초기화 보장)
        setTimeout(() => {
          const { viewport } = useNodeWorkflowStore.getState();
          if (viewport) {
            instance.setViewport(viewport);
          }
        }, 50);
      }
      setHasAutoRestored(true);
    }
  }, [restoreWorkflow, hasAutoRestored]);

  // ReactFlow용 상태 (스토어와 동기화)
  const [nodes, setNodes, onNodesChange] = useNodesState(storeNodes);
  const [, setEdges, onEdgesChange] = useEdgesState(storeEdges); // edges는 styledEdges 사용
  
  // 노드에 selected 상태 추가
  const nodesWithSelected = React.useMemo(() => {
    return nodes.map(node => ({
      ...node,
      selected: node.id === selectedNodeId
    }));
  }, [nodes, selectedNodeId]);

  // 스토어의 뷰포트가 변경되면 ReactFlow에 적용 (복원 시에만)
  useEffect(() => {
    if (reactFlowInstance && viewport && isRestoring) {
      const currentReactFlowViewport = reactFlowInstance.getViewport();
      // 뷰포트가 실제로 다를 때만 업데이트하여 무한 루프 방지
      if (
        Math.abs(currentReactFlowViewport.x - viewport.x) > 1 ||
        Math.abs(currentReactFlowViewport.y - viewport.y) > 1 ||
        Math.abs(currentReactFlowViewport.zoom - viewport.zoom) > 0.01
      ) {
        reactFlowInstance.setViewport(viewport);
      }
    }
  }, [viewport, reactFlowInstance, isRestoring]);

  // 메모이제이션으로 불필요한 재계산 방지
  const memoizedNodeTypes = React.useMemo(() => nodeTypes, []);
  const memoizedEdgeTypes = React.useMemo(() => edgeTypes, []);
  
  // 선택된 노드의 edges를 계산
  const selectedNodeEdges = React.useMemo(() => {
    if (!selectedNodeId) return [];
    return storeEdges.filter(edge => 
      edge.source === selectedNodeId || edge.target === selectedNodeId
    );
  }, [selectedNodeId, storeEdges]);

  // 노드 클릭 핸들러
  const onNodeClick = useCallback((_: React.MouseEvent, node: any) => {
    setSelectedNodeId(node.id);
  }, [setSelectedNodeId]);

  // 캔버스 배경 클릭 시 선택 해제
  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, [setSelectedNodeId]);

  // Edge 스타일링 - 선택된 노드와 연관된 edge는 애니메이션 적용
  const styledEdges = React.useMemo(() => {
    return storeEdges.map(edge => ({
      ...edge,
      animated: selectedNodeEdges.some(selectedEdge => selectedEdge.id === edge.id),
      markerEnd: {
        type: 'arrowclosed' as const,
        width: 20,
        height: 20,
        color: selectedNodeEdges.some(selectedEdge => selectedEdge.id === edge.id) 
          ? UI_COLORS.EDGE.SELECTED // 선택된 노드의 edge는 파란색
          : UI_COLORS.EDGE.DEFAULT // 기본 회색
      },
      style: {
        stroke: selectedNodeEdges.some(selectedEdge => selectedEdge.id === edge.id) 
          ? UI_COLORS.EDGE.SELECTED // 선택된 노드의 edge는 파란색
          : UI_COLORS.EDGE.DEFAULT, // 기본 회색
        strokeWidth: selectedNodeEdges.some(selectedEdge => selectedEdge.id === edge.id) 
          ? 2 // 선택된 노드의 edge는 더 굵게
          : 1
      }
    }));
  }, [storeEdges, selectedNodeEdges]);

  // 뷰포트 변화 감지 및 상태 업데이트 (더 민감한 감지)
  const onViewportChange = useCallback((newViewport: any) => {
    // null 체크 추가
    if (!newViewport || !viewport) return;
    
    // viewport와 비교하여 변경 감지
    if (Math.abs((newViewport.zoom || 1) - (viewport.zoom || 1)) > 0.005 ||  // 줌 변경을 더 민감하게
        Math.abs((newViewport.x || 0) - (viewport.x || 0)) > 2 ||          // x 변경을 더 민감하게
        Math.abs((newViewport.y || 0) - (viewport.y || 0)) > 2) {          // y 변경을 더 민감하게
      setViewport(newViewport);
    }
  }, [setViewport, viewport]);

  // 노드 변경 핸들러 (출력 노드만 이동 불가)
  const onNodesChangeWithFixed = useCallback((changes: any[]) => {
    const filteredChanges = changes.filter(change => {
      // 출력 노드의 위치 변경만 무시 (완전 고정)
      if (change.type === 'position') {
        const node = nodes.find(n => n.id === change.id);
        if (node?.data?.nodeType === NodeType.OUTPUT) {
          return false;
        }
      }
      return true;
    });
    
    onNodesChange(filteredChanges);
    
    // 실시간 store 업데이트는 제거 - 저장할 때만 동기화
  }, [onNodesChange, nodes]);



  // 노드 동기화 - 무한 루프 방지를 위한 안전한 로직
  const prevStoreNodesRef = React.useRef(storeNodes);
  
  React.useEffect(() => {
    // store 노드가 실제로 변경되지 않았으면 업데이트하지 않음 (무한 루프 방지)
    if (prevStoreNodesRef.current === storeNodes) {
      return;
    }
    
    if (!hasAutoRestored) {
      // 자동 복원 중에는 store의 노드를 그대로 사용
      setNodes(storeNodes);
      prevStoreNodesRef.current = storeNodes;
      return;
    }
    
    // 노드 변경 사항 감지 (개수, ID, 데이터 변경)
    const currentIds = new Set(prevStoreNodesRef.current.map(n => n.id));
    const newIds = new Set(storeNodes.map(n => n.id));
    
    // 1. 노드 개수나 ID 변경 확인
    const hasStructuralChanges = currentIds.size !== newIds.size || 
                                [...currentIds].some(id => !newIds.has(id)) ||
                                [...newIds].some(id => !currentIds.has(id));
    
    // 2. 기존 노드의 데이터 변경 확인 (label, model 등)
    const hasDataChanges = !hasStructuralChanges && storeNodes.some(storeNode => {
      const prevNode = prevStoreNodesRef.current.find(n => n.id === storeNode.id);
      if (!prevNode) return false;
      
      // 노드 데이터 비교 (data 객체의 내용 비교)
      return JSON.stringify(prevNode.data) !== JSON.stringify(storeNode.data) ||
             prevNode.type !== storeNode.type;
    });
    
    if (hasStructuralChanges || hasDataChanges) {
      // 노드가 추가/삭제되거나 데이터가 변경된 경우 동기화 (기존 위치 보존)
      setNodes(currentReactFlowNodes => {
        const currentPositions = new Map();
        currentReactFlowNodes.forEach(node => {
          currentPositions.set(node.id, node.position);
        });

        return storeNodes.map(storeNode => {
          const existingPosition = currentPositions.get(storeNode.id);
          return {
            ...storeNode,
            position: existingPosition || storeNode.position
          };
        });
      });
    }
    
    prevStoreNodesRef.current = storeNodes;
  }, [storeNodes, setNodes, hasAutoRestored]);

  // 스토어의 엣지가 변경되면 ReactFlow에 적용
  useEffect(() => {
    setEdges(storeEdges);
  }, [storeEdges, setEdges]);

  // 연결 생성 핸들러
  const onConnect = useCallback(
    (params: Connection | Edge) => {
      const sourceNode = storeNodes.find(n => n.id === params.source);
      const targetNode = storeNodes.find(n => n.id === params.target);

      if (!sourceNode || !targetNode) {
        message.error("연결할 소스 또는 타겟 노드를 찾을 수 없습니다.");
        return;
      }

      const validation = isConnectionAllowed(sourceNode, targetNode, storeNodes, storeEdges);

      if (validation.allowed) {
        const newEdge: WorkflowEdge = {
          id: `edge-${params.source}-${params.target}`,
          source: params.source!,
          target: params.target!,
        };
        addStoreEdge(newEdge);
      } else {
        message.error(validation.reason || '연결 규칙에 위배됩니다. 연결할 수 없습니다.');
      }
    },
    [addStoreEdge, storeNodes, storeEdges]
  );

  // 엣지 재연결 핸들러
  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      const sourceNode = storeNodes.find(n => n.id === newConnection.source);
      const targetNode = storeNodes.find(n => n.id === newConnection.target);

      if (!sourceNode || !targetNode) {
        message.error("연결할 소스 또는 타겟 노드를 찾을 수 없습니다.");
        return;
      }

      const validation = isConnectionAllowed(sourceNode, targetNode, storeNodes, storeEdges);

      if (validation.allowed) {
        // 기존 엣지 제거
        removeEdge(oldEdge.id);
        
        // 새 엣지 추가
        const newEdge: WorkflowEdge = {
          id: `edge-${newConnection.source}-${newConnection.target}`,
          source: newConnection.source!,
          target: newConnection.target!,
        };
        addStoreEdge(newEdge);
        message.success('엣지가 성공적으로 재연결되었습니다.');
      } else {
        message.error(validation.reason || '연결 규칙에 위배됩니다. 연결할 수 없습니다.');
      }
    },
    [addStoreEdge, removeEdge, storeNodes, storeEdges]
  );

  // 엣지 재연결 시작 핸들러  
  const onReconnectStart = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      // 엣지 재연결이 시작될 때의 로직 (필요시 추가)
      console.log('Edge reconnect started:', edge.id);
    },
    []
  );

  // 엣지 재연결 종료 핸들러 (허공에 드롭 시 엣지 삭제)
  const onReconnectEnd = useCallback(
    (_: MouseEvent | TouchEvent, edge: Edge) => {
      // 허공에 드롭되면 엣지 삭제
      setTimeout(() => {
        const updatedEdge = storeEdges.find(e => e.id === edge.id);
        if (updatedEdge) {
          // 연결이 그대로 남아있다면 허공에 드롭된 것으로 간주하고 삭제
          removeEdge(edge.id);
          message.info('엣지가 삭제되었습니다.');
        }
      }, 100);
    },
    [removeEdge, storeEdges]
  );

  // 노드 삭제 핸들러
  const onNodesDelete = useCallback(
    (deletedNodes: any[]) => {
      deletedNodes.forEach(node => removeNode(node.id));
    },
    [removeNode]
  );

  // 엣지 삭제 핸들러
  const onEdgesDelete = useCallback(
    (deletedEdges: any[]) => {
      deletedEdges.forEach(edge => removeEdge(edge.id));
    },
    [removeEdge]
  );

  // 워크플로우 저장 핸들러
  const handleSave = () => {
    if (reactFlowInstance) {
      const currentNodes = reactFlowInstance.getNodes();
      updateNodePositions(currentNodes.map((n: any) => ({ id: n.id, position: n.position })));
      saveCurrentWorkflow();
      message.success('워크플로우가 저장되었습니다.');
    }
  };

  // 워크플로우 복원 핸들러
  const handleRestore = () => {
    const success = restoreWorkflow();
    if (success) {
      // 복원 후 뷰포트 적용
      setTimeout(() => {
        if (reactFlowInstance) {
          const { viewport: restoredViewport } = useNodeWorkflowStore.getState();
          if (restoredViewport) {
            reactFlowInstance.setViewport(restoredViewport);
          }
        }
      }, 50);
      message.success('워크플로우가 복원되었습니다.');
    } else {
      message.info('저장된 워크플로우가 없습니다.');
    }
  };

  // 초기화 핸들러
  const handleReset = () => {
    Modal.confirm({
      title: '워크플로우 초기화',
      content: '정말로 모든 노드와 연결을 삭제하고 초기 상태로 되돌리시겠습니까?',
      okText: '초기화',
      cancelText: '취소',
      onOk: () => {
        resetToInitialState();
        message.success('워크플로우가 초기화되었습니다.');
        // 초기화 후 뷰포트 리셋
        setTimeout(() => {
          if (reactFlowInstance) {
            reactFlowInstance.setViewport({ x: 0, y: 0, zoom: 1 });
          }
        }, 50);
      },
    });
  };

  // JSON으로 내보내기 핸들러
  const handleExport = () => {
    if (reactFlowInstance) {
      const currentNodes = reactFlowInstance.getNodes();
      updateNodePositions(currentNodes.map((n: any) => ({ id: n.id, position: n.position })));
      exportToJSON();
    }
  };

  // JSON 가져오기 모달 열기
  const showImportModal = () => {
    setImportModalVisible(true);
  };

  // JSON 가져오기 처리
  const handleImport = () => {
    try {
      importFromJSON(jsonText);
      message.success('워크플로우를 성공적으로 가져왔습니다.');
      setImportModalVisible(false);
      setJsonText('');
      // 가져온 후 뷰포트 적용
      setTimeout(() => {
        if (reactFlowInstance) {
          const { viewport: importedViewport } = useNodeWorkflowStore.getState();
          if (importedViewport) {
            reactFlowInstance.setViewport(importedViewport);
          }
        }
      }, 50);
    } catch (error) {
      message.error('유효하지 않은 JSON 형식입니다. 다시 확인해주세요.');
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>

      {/* 상단 타이틀 바 */}
      <div style={{ padding: '8px 16px', background: UI_COLORS.PANEL.HEADER_BACKGROUND, borderBottom: `1px solid ${UI_COLORS.PANEL.HEADER_BORDER}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>워크플로우 구성</Typography.Title>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {!isExecuting && !isStopping ? (
            <Button 
              icon={<PlayCircleOutlined />} 
              type="primary" 
              onClick={handleStreamingExecution}
            >
              워크플로우 실행
            </Button>
          ) : isExecuting && !isStopping ? (
            <Button 
              icon={<StopOutlined />} 
              type="default" 
              danger 
              onClick={handleStopExecution}
            >
              워크플로우 중단
            </Button>
          ) : (
            <Button 
              icon={<StopOutlined />} 
              type="default" 
              danger 
              disabled={true}
              loading={true}
            >
              중단 중...
            </Button>
          )}
        </div>
      </div>

      <div style={{ flex: 1, position: 'relative' }}>

        <ReactFlow
          nodes={nodesWithSelected}
          edges={styledEdges}
          onNodesChange={onNodesChangeWithFixed}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodesDelete={onNodesDelete}
          onEdgesDelete={onEdgesDelete}
          onReconnect={onReconnect}
          onReconnectStart={onReconnectStart}
          onReconnectEnd={onReconnectEnd}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={memoizedNodeTypes}
          edgeTypes={memoizedEdgeTypes}
          onInit={onInit}
          onMoveEnd={onViewportChange}
          fitView
          fitViewOptions={fitViewOptions}
          style={reactFlowStyle}
          edgesReconnectable={true}
        >
          <Background />
          <Controls />
          <MiniMap />

          <div style={{ position: 'absolute', top: 10, left: 10, zIndex: 10, display: 'flex', gap: '8px' }}>
            <Space.Compact>
              <Button icon={<FileTextOutlined />} onClick={() => addNode(NodeType.INPUT, { x: 250, y: 5 })}>입력</Button>
              <Button icon={<RobotOutlined />} onClick={() => addNode(NodeType.GENERATION, { x: 250, y: 105 })}>생성</Button>
              <Button icon={<BranchesOutlined />} onClick={() => addNode(NodeType.ENSEMBLE, { x: 250, y: 205 })}>앙상블</Button>
              <Button icon={<CheckCircleOutlined />} onClick={() => addNode(NodeType.VALIDATION, { x: 250, y: 305 })}>검증</Button>
              <Button icon={<SearchOutlined />} onClick={() => addNode(NodeType.CONTEXT, { x: 250, y: 405 })}>컨텍스트</Button>
            </Space.Compact>
            
            <Space.Compact>
              <Button icon={<SaveOutlined />} onClick={handleSave}>저장</Button>
              <Button icon={<ReloadOutlined />} onClick={handleRestore}>복원</Button>
              <Button icon={<ClearOutlined />} onClick={handleReset}>초기화</Button>
            </Space.Compact>

            <Space.Compact>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>내보내기</Button>
              <Button icon={<UploadOutlined />} onClick={showImportModal}>가져오기</Button>
            </Space.Compact>
          </div>
        </ReactFlow>
      </div>

      <Modal
        title="워크플로우 JSON 가져오기"
        open={importModalVisible}
        onOk={handleImport}
        onCancel={() => setImportModalVisible(false)}
        okText="가져오기"
        cancelText="취소"
      >
        <Input.TextArea
          rows={10}
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          placeholder='여기에 JSON 데이터를 붙여넣으세요.'
        />
      </Modal>
    </div>
  );
});