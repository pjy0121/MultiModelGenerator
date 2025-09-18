import React, { useCallback, useEffect, useState, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
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
  Typography 
} from 'antd';
import {
  FileTextOutlined,
  RobotOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  SaveOutlined,
  ReloadOutlined,
  ClearOutlined,
  DownloadOutlined,
  UploadOutlined
} from '@ant-design/icons';import { NodeWorkflowComponent } from './NodeWorkflowComponent';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';
import { WorkflowEdge, NodeType } from '../types';
import { isConnectionAllowed } from '../utils/nodeWorkflowValidation';



// 노드 타입 정의
const nodeTypes: NodeTypes = {
  workflowNode: NodeWorkflowComponent,
};

export const NodeWorkflowCanvas: React.FC = () => {
  const { 
    nodes: storeNodes, 
    edges: storeEdges, 
    viewport, // 스토어의 뷰포트 상태
    isRestoring, // 복원 상태
    addEdge: addStoreEdge,
    removeEdge,
    removeNode,
    currentViewport, // 실시간 뷰포트 상태
    
    // 노드 추가와 워크플로우 관리 함수들
    addNode,
    saveCurrentWorkflow,
    restoreWorkflow,
    resetToInitialState,
    exportToJSON,
    importFromJSON,
    setViewport,
    updateNodePositions
  } = useNodeWorkflowStore();
  
  // 워크플로우 관리 상태
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [jsonText, setJsonText] = useState('');

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
  const [edges, setEdges, onEdgesChange] = useEdgesState(storeEdges);

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

  // 뷰포트 변화 감지 및 상태 업데이트 (더 민감한 감지)
  const onViewportChange = useCallback((newViewport: any) => {
    // currentViewport와 비교하여 변경 감지
    if (Math.abs(newViewport.zoom - currentViewport.zoom) > 0.005 ||  // 줌 변경을 더 민감하게
        Math.abs(newViewport.x - currentViewport.x) > 2 ||          // x 변경을 더 민감하게
        Math.abs(newViewport.y - currentViewport.y) > 2) {          // y 변경을 더 민감하게
      setViewport(newViewport);
    }
  }, [setViewport, currentViewport]);

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

  React.useEffect(() => {
    setEdges(storeEdges);
  }, [storeEdges, setEdges]);

  // 앱 시작시 자동으로 저장된 워크플로우 복원 (마운트시 한 번만)
  React.useEffect(() => {
    if (!hasAutoRestored) {
      restoreWorkflow();
      setHasAutoRestored(true);
    }
  }, [hasAutoRestored, restoreWorkflow]);



  // 연결 유효성 검사
  const isValidConnectionCheck = useCallback((connection: Connection) => {
    if (!connection.source || !connection.target) return false;
    
    const sourceNode = storeNodes.find(node => node.id === connection.source);
    const targetNode = storeNodes.find(node => node.id === connection.target);
    
    if (!sourceNode || !targetNode) return false;
    
    const validation = isConnectionAllowed(sourceNode, targetNode, storeNodes, storeEdges);
    
    if (!validation.allowed && validation.reason) {
      message.error(validation.reason);
    }
    
    return validation.allowed;
  }, [storeNodes, storeEdges]);

  // 뷰포트 변경 핸들러 - 디바운싱으로 성능 최적화
  const viewportTimeoutRef = React.useRef<number | null>(null);
  const onMoveEnd = useCallback((_event: any, viewport: any) => {
    // 기존 타이머 클리어
    if (viewportTimeoutRef.current) {
      clearTimeout(viewportTimeoutRef.current);
    }
    
    // 300ms 후에 뷰포트 업데이트 (디바운싱)
    viewportTimeoutRef.current = setTimeout(() => {
      setViewport(viewport);
    }, 300);
  }, [setViewport]);

  // 뷰포트 타이머 정리
  React.useEffect(() => {
    return () => {
      if (viewportTimeoutRef.current) {
        clearTimeout(viewportTimeoutRef.current);
      }
    };
  }, []);

  // 연결 생성 핸들러
  const onConnect = useCallback((params: Connection) => {
    if (params.source && params.target && isValidConnectionCheck(params)) {
      const newEdge: WorkflowEdge = {
        id: `edge_${params.source}_${params.target}_${Date.now()}`,
        source: params.source,
        target: params.target,
      };
      
      // 스토어에 엣지 추가
      addStoreEdge(newEdge);
      
      // 로컬 상태에도 추가
      setEdges((eds) => addEdge(params, eds));
    }
  }, [addStoreEdge, setEdges, isValidConnectionCheck]);

  // 노드 삭제 핸들러
  const onNodesDelete = useCallback((nodesToDelete: any[]) => {
    nodesToDelete.forEach(node => {
      try {
        removeNode(node.id);
      } catch (error: any) {
        // 에러는 이미 store에서 message로 표시됨
      }
    });
  }, [removeNode]);

  // 엣지 삭제 핸들러
  const onEdgesDelete = useCallback((edgesToDelete: Edge[]) => {
    for (const edge of edgesToDelete) {
      // 초기 연결(input → output)은 삭제할 수 없음
      if (edge.source === 'initial-input' && edge.target === 'initial-output') {
        message.error('초기 연결(input-node → output-node)은 삭제할 수 없습니다.');
        continue;
      }
      
      removeEdge(edge.id);
    }
  }, [removeEdge]);

  // 키보드 삭제 기능
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key === 'Delete') {
      // 입력 요소에 포커스가 있는지 확인 (모달 수정 중일 때 방지)
      const activeElement = document.activeElement;
      if (activeElement && (
        activeElement.tagName === 'INPUT' ||
        activeElement.tagName === 'TEXTAREA' ||
        activeElement.tagName === 'SELECT' ||
        activeElement.getAttribute('contenteditable') === 'true' ||
        activeElement.closest('.ant-modal') !== null // Ant Design 모달 내부인지 확인
      )) {
        return; // 입력 중이거나 모달 내부에서는 삭제 방지
      }

      const selectedNodes = reactFlowInstance?.getNodes().filter((node: any) => node.selected) || [];
      const selectedEdges = reactFlowInstance?.getEdges().filter((edge: any) => edge.selected) || [];
      
      // 선택된 엣지 삭제
      if (selectedEdges.length > 0) {
        onEdgesDelete(selectedEdges);
      }
      
      // 선택된 노드 삭제 (기존 로직 유지)
      if (selectedNodes.length > 0) {
        onNodesDelete(selectedNodes);
      }
    }
  }, [reactFlowInstance, onEdgesDelete, onNodesDelete]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // 연결 재배치 핸들러 (엣지를 드래그하여 다른 노드로 연결 변경 또는 제거)
  const onReconnectHandler = useCallback((oldEdge: Edge, newConnection: Connection) => {
    // 허공에 놓인 경우 (target이 null이거나 undefined)
    if (!newConnection.target || !newConnection.source) {
      removeEdge(oldEdge.id);
      message.info('연결이 제거되었습니다.');
      return;
    }
    
    const sourceNode = storeNodes.find(node => node.id === newConnection.source);
    const targetNode = storeNodes.find(node => node.id === newConnection.target);
    
    if (!sourceNode || !targetNode) {
      removeEdge(oldEdge.id);
      message.info('연결이 제거되었습니다.');
      return;
    }
    
    // 기존 엣지를 제외한 엣지 목록에서 검증
    const otherEdges = storeEdges.filter(edge => edge.id !== oldEdge.id);
    const validation = isConnectionAllowed(sourceNode, targetNode, storeNodes, otherEdges);
    
    if (!validation.allowed && validation.reason) {
      message.error(validation.reason);
      removeEdge(oldEdge.id);
      return;
    }
    
    // 기존 엣지 제거 후 새 엣지 추가
    removeEdge(oldEdge.id);
    
    const newEdge: WorkflowEdge = {
      id: `edge_${newConnection.source}_${newConnection.target}_${Date.now()}`,
      source: newConnection.source,
      target: newConnection.target,
    };
    
    addStoreEdge(newEdge);
    
    // 로컬 상태도 업데이트
    setEdges((edges) => {
      const filteredEdges = edges.filter(edge => edge.id !== oldEdge.id);
      return [...filteredEdges, newEdge];
    });
    
    message.success('연결이 성공적으로 변경되었습니다.');
  }, [storeNodes, storeEdges, removeEdge, addStoreEdge, setEdges]);

  // 연결이 끊어지는 경우 처리 (Edge를 허공으로 드래그할 때)
  const onReconnectStart = useCallback((_event: any, edge: Edge) => {
    // 연결 시작 시 기존 엣지를 임시로 선택 상태로 만듦
    setEdges(edges => edges.map(e => 
      e.id === edge.id ? { ...e, selected: true } : { ...e, selected: false }
    ));
  }, [setEdges]);

  const onReconnectEnd = useCallback((event: any, edge: Edge) => {
    // 마우스 이벤트에서 대상 요소 확인
    const target = event.target;
    const isNodeHandle = target?.classList?.contains('react-flow__handle') || 
                        target?.closest('.react-flow__handle');
    const isNode = target?.classList?.contains('react-flow__node') || 
                   target?.closest('.react-flow__node');
    
    // 노드나 핸들이 아닌 곳에 놓인 경우 (허공에 놓인 경우)
    if (!isNodeHandle && !isNode) {
      removeEdge(edge.id);
      message.info('연결이 제거되었습니다.');
    }
    
    // 선택 상태 해제
    setEdges(edges => edges.map(e => ({ ...e, selected: false })));
  }, [removeEdge, setEdges]);

  // 노드 추가 핸들러 - 현재 뷰포트 중심에 생성
  const handleAddNode = (nodeType: string) => {
    // 현재 뷰포트 중심 근처에 새 노드 배치
    const viewport = reactFlowInstance?.getViewport() || { x: 0, y: 0, zoom: 1 };
    const centerX = (-viewport.x + 400) / viewport.zoom;  // 화면 중심 X
    const centerY = (-viewport.y + 300) / viewport.zoom;  // 화면 중심 Y
    
    // 중심 근처에 약간의 랜덤 오프셋 추가
    const position = { 
      x: centerX + (Math.random() - 0.5) * 200, 
      y: centerY + (Math.random() - 0.5) * 200 
    };
    
    // 문자열을 올바른 NodeType enum으로 변환
    const nodeTypeMap: { [key: string]: NodeType } = {
      'input': NodeType.INPUT,
      'generation': NodeType.GENERATION,
      'ensemble': NodeType.ENSEMBLE,
      'validation': NodeType.VALIDATION,
      'output': NodeType.OUTPUT
    };
    
    const actualNodeType = nodeTypeMap[nodeType] || NodeType.INPUT;
    
    addNode(actualNodeType, position);
  };

  // 워크플로우 관리 핸들러
  const handleSaveWorkflow = useCallback(() => {
    // 현재 뷰포트와 노드 위치를 store에 업데이트하고 저장
    if (reactFlowInstance) {
      const currentViewportState = reactFlowInstance.getViewport();
      const currentReactFlowNodes = reactFlowInstance.getNodes();
      
      // store 상태 즉시 업데이트
      setViewport(currentViewportState);
      const nodePositions = currentReactFlowNodes.map((rfNode: any) => ({
        id: rfNode.id,
        position: rfNode.position
      }));
      updateNodePositions(nodePositions);
    }
    
    // 저장 실행
    saveCurrentWorkflow();
    message.success('워크플로우가 저장되었습니다.');
  }, [reactFlowInstance, setViewport, updateNodePositions, saveCurrentWorkflow]);

  const handleRestoreWorkflow = useCallback(() => {
    const success = restoreWorkflow();
    if (success) {
      message.success('워크플로우가 복원되었습니다.');
      
      // ReactFlow 상태를 store와 동기화 (뷰포트 복원)
      if (reactFlowInstance) {
        // 복원된 뷰포트를 가져와서 적용
        const { viewport } = useNodeWorkflowStore.getState();
        if (viewport) {
          // 여러 번 시도하여 확실히 적용되도록 함
          setTimeout(() => {
            reactFlowInstance.setViewport(viewport);
          }, 50);
          setTimeout(() => {
            reactFlowInstance.setViewport(viewport);
          }, 150);
          setTimeout(() => {
            reactFlowInstance.setViewport(viewport);
          }, 300);
        }
      }
    } else {
      message.error('저장된 워크플로우가 없습니다.');
    }
  }, [restoreWorkflow, reactFlowInstance]);

  const handleResetWorkflow = useCallback(() => {
    Modal.confirm({
      title: '워크플로우 초기화',
      content: '모든 노드와 연결을 삭제하고 초기 상태로 되돌립니다. 계속하시겠습니까?',
      okText: '초기화',
      cancelText: '취소',
      okType: 'danger',
      onOk() {
        resetToInitialState();
        
        // 초기화 후 뷰포트를 즉시 적용
        if (reactFlowInstance) {
          setTimeout(() => {
            const { viewport } = useNodeWorkflowStore.getState();
            if (viewport) {
              reactFlowInstance.setViewport(viewport);
            }
          }, 100);
        }
        
        message.success('워크플로우가 초기 상태로 리셋되었습니다.');
      },
    });
  }, [resetToInitialState, reactFlowInstance]);

  const handleExportWorkflow = useCallback(() => {
    exportToJSON();
    message.success('워크플로우가 내보내기되었습니다.');
  }, [exportToJSON]);

  const handleImportWorkflow = useCallback(() => {
    try {
      const success = importFromJSON(jsonText);
      if (success) {
        message.success('워크플로우가 가져오기되었습니다.');
        setImportModalVisible(false);
        setJsonText('');
      } else {
        message.error('유효하지 않은 워크플로우 데이터입니다.');
      }
    } catch (error) {
      message.error('JSON 형식이 올바르지 않습니다.');
    }
  }, [importFromJSON, jsonText]);

  // 반응형 캔버스 래퍼
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  // 초기 노드를 Canvas 중앙에 배치
  useEffect(() => {
    if (reactFlowWrapper.current && storeNodes.length > 0) {
      const { width } = reactFlowWrapper.current.getBoundingClientRect();
      const centerX = width / 2 - 75; // 노드 너비(150px)의 절반을 빼서 중앙 정렬

      const initialNodes = storeNodes.filter(
        (n) => n.data.nodeType === NodeType.INPUT || n.data.nodeType === NodeType.OUTPUT
      );

      if (initialNodes.length > 0) {
        const nodePositions = initialNodes.map(node => ({
          id: node.id,
          position: {
            x: centerX,
            y: node.data.nodeType === NodeType.INPUT ? 100 : 550,
          },
        }));
        updateNodePositions(nodePositions);
      }
    }
  }, []); // 컴포넌트 마운트 시 한 번만 실행

  return (
    <div style={{ width: '100%', height: '700px', border: '1px solid #d9d9d9', borderRadius: '6px', position: 'relative' }} ref={reactFlowWrapper}>
      {/* 상단 오버레이 - 노드 추가 */}
      <div style={{
        position: 'absolute',
        top: '10px',
        left: '10px',
        zIndex: 1000,
        display: 'flex',
        gap: '8px',
        background: 'rgba(255, 255, 255, 0.9)',
        padding: '8px',
        borderRadius: '6px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
      }}>
        <Button 
          size="small" 
          icon={<FileTextOutlined />}
          onClick={() => handleAddNode('input')}
        >
          입력 노드
        </Button>
        <Button 
          size="small" 
          icon={<RobotOutlined />}
          onClick={() => handleAddNode('generation')}
        >
          생성 노드
        </Button>
        <Button 
          size="small" 
          icon={<BranchesOutlined />}
          onClick={() => handleAddNode('ensemble')}
        >
          앙상블 노드
        </Button>
        <Button 
          size="small" 
          icon={<CheckCircleOutlined />}
          onClick={() => handleAddNode('validation')}
        >
          검증 노드
        </Button>
      </div>

      {/* 상단 오른쪽 오버레이 - 워크플로우 관리 */}
      <div style={{
        position: 'absolute',
        top: '10px',
        right: '10px',
        zIndex: 1000,
        display: 'flex',
        gap: '8px',
        background: 'rgba(255, 255, 255, 0.9)',
        padding: '8px',
        borderRadius: '6px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
      }}>
        <Button 
          size="small" 
          icon={<SaveOutlined />}
          onClick={handleSaveWorkflow}
        >
          저장
        </Button>
        <Button 
          size="small" 
          icon={<ReloadOutlined />}
          onClick={handleRestoreWorkflow}
        >
          복원
        </Button>
        <Button 
          size="small" 
          icon={<ClearOutlined />}
          onClick={handleResetWorkflow}
          danger
        >
          초기화
        </Button>
        <Button 
          size="small" 
          icon={<DownloadOutlined />}
          onClick={handleExportWorkflow}
        >
          내보내기
        </Button>
        <Button 
          size="small" 
          icon={<UploadOutlined />}
          onClick={() => setImportModalVisible(true)}
        >
          가져오기
        </Button>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChangeWithFixed}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onReconnect={onReconnectHandler}
        onReconnectStart={onReconnectStart}
        onReconnectEnd={onReconnectEnd}
        onEdgesDelete={onEdgesDelete}
        onNodesDelete={onNodesDelete}
        onInit={onInit}
        onViewportChange={onViewportChange}
        onMoveEnd={onMoveEnd}
        nodeTypes={memoizedNodeTypes}
        fitView={false}
        snapToGrid={false}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        minZoom={0.5}
        maxZoom={2 }
        deleteKeyCode={['Delete']}
        multiSelectionKeyCode={['Meta', 'Ctrl']}
        panOnDrag={true}
        zoomOnScroll={true}
        zoomOnPinch={true}
        zoomOnDoubleClick={false}
        preventScrolling={true}
        nodesDraggable={true}
        nodesConnectable={true}
        elementsSelectable={true}
        autoPanOnConnect={false}
        autoPanOnNodeDrag={false}
        selectNodesOnDrag={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#f0f2f5" gap={15} />
        <Controls />
        <MiniMap 
          style={{
            height: 80,
            width: 120,
            background: '#f9f9f9',
          }}
          zoomable
          pannable
        />
        
        {/* 도움말 텍스트 */}
        <div style={{
          position: 'absolute',
          top: 10,
          right: 10,
          background: 'rgba(255, 255, 255, 0.9)',
          padding: '8px 12px',
          borderRadius: '4px',
          fontSize: '12px',
          color: '#666',
          maxWidth: '350px'
        }}>
          💡 <strong>사용법:</strong><br/>
          • 노드 우상단의 편집 버튼으로 설정<br/>
          • 연결선을 선택 후 Delete키로 삭제<br/>
          • 연결선을 드래그해서 다른 노드로 이동<br/>
          • 연결선을 허공에 놓으면 연결 제거<br/>
          • 모든 노드 드래그로 위치 조정 가능 (Output 노드 제외)<br/>
          • Output 노드는 화면 중앙 하단 고정<br/>
          • 노드 Handle에서 드래그로 새 연결 생성<br/>
          • 마우스 휠로 줌 인/아웃 가능
        </div>
      </ReactFlow>

      {/* JSON 가져오기 모달 */}
      <Modal
        title="워크플로우 가져오기"
        open={importModalVisible}
        onOk={handleImportWorkflow}
        onCancel={() => {
          setImportModalVisible(false);
          setJsonText('');
        }}
        okText="가져오기"
        cancelText="취소"
      >
        <div style={{ marginBottom: '16px' }}>
          <Typography.Text type="secondary">
            워크플로우 JSON 데이터를 붙여넣으세요:
          </Typography.Text>
        </div>
        <Input.TextArea
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          placeholder="JSON 데이터를 여기에 붙여넣으세요..."
          rows={10}
        />
      </Modal>
    </div>
  );
};