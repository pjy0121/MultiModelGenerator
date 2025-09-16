import React, { useCallback, useEffect } from 'react';
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
import { message } from 'antd';

import { NodeWorkflowComponent } from './NodeWorkflowComponent';
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
    addEdge: addStoreEdge,
    removeEdge,
    removeNode
  } = useNodeWorkflowStore();

  // ReactFlow 인스턴스 레퍼런스
  const [reactFlowInstance, setReactFlowInstance] = React.useState<any>(null);
  const [currentViewport, setCurrentViewport] = React.useState({ x: 0, y: 0, zoom: 1 });

  // ReactFlow 초기화 핸들러
  const onInit = useCallback((instance: any) => {
    setReactFlowInstance(instance);
    // 초기 뷰포트 상태 설정
    const viewport = instance.getViewport();
    setCurrentViewport(viewport);
  }, []);

  // ReactFlow용 상태 (스토어와 동기화)
  const [nodes, setNodes, onNodesChange] = useNodesState(storeNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(storeEdges);

  // 출력 노드 고정 위치 (하단 중앙)
  const getFixedOutputPosition = (viewport = { x: 0, y: 0, zoom: 1 }) => {
    // 캔버스 크기 기준 (700px 높이)
    const canvasHeight = 700;
    const canvasWidth = 800; // 추정값
    
    // 뷰포트를 고려한 실제 가시 영역에서의 위치 계산
    const visibleCenterX = (-viewport.x + canvasWidth/2) / viewport.zoom;
    const visibleBottomY = (-viewport.y + canvasHeight - 100) / viewport.zoom; // 하단에서 100px 위
    
    return { x: visibleCenterX - 100, y: visibleBottomY }; // 노드 크기 고려
  };

  // 입력 노드 고정 위치 (상단 중앙)
  const getFixedInputPosition = (viewport = { x: 0, y: 0, zoom: 1 }) => {
    const canvasWidth = 800; // 추정값
    
    // 뷰포트를 고려한 실제 가시 영역에서의 위치 계산
    const visibleCenterX = (-viewport.x + canvasWidth/2) / viewport.zoom;
    const visibleTopY = (-viewport.y + 50) / viewport.zoom; // 상단에서 50px 아래
    
    return { x: visibleCenterX - 100, y: visibleTopY }; // 노드 크기 고려
  };

  // 뷰포트 변화 감지 및 고정 노드 위치 업데이트
  const onViewportChange = useCallback((newViewport: any) => {
    setCurrentViewport(newViewport);
    
    // Input/Output 노드 위치 업데이트
    setNodes(currentNodes => 
      currentNodes.map(node => {
        if (node.data?.nodeType === NodeType.INPUT) {
          return { ...node, position: getFixedInputPosition(newViewport) };
        }
        if (node.data?.nodeType === NodeType.OUTPUT) {
          return { ...node, position: getFixedOutputPosition(newViewport) };
        }
        return node;
      })
    );
  }, [setNodes]);

  // 노드 변경 핸들러 (입력/출력 노드는 이동 불가)
  const onNodesChangeWithFixed = useCallback((changes: any[]) => {
    const filteredChanges = changes.filter(change => {
      // 입력/출력 노드의 위치 변경은 무시 (완전 고정)
      if (change.type === 'position') {
        const node = nodes.find(n => n.id === change.id);
        if (node?.data?.nodeType === NodeType.OUTPUT || 
            node?.data?.nodeType === NodeType.INPUT) {
          return false;
        }
      }
      return true;
    });
    onNodesChange(filteredChanges);
  }, [onNodesChange, nodes]);

  // 스토어 상태가 변경되면 로컬 상태 업데이트 (위치 정보 보존)
  React.useEffect(() => {
    setNodes(currentNodes => {
      // 기존 노드들의 위치 정보를 보존하면서 업데이트
      const updatedNodes = storeNodes.map(storeNode => {
        const existingNode = currentNodes.find(node => node.id === storeNode.id);
        
        // 출력 노드는 현재 뷰포트를 고려한 고정 위치로 설정
        if (storeNode.data?.nodeType === NodeType.OUTPUT) {
          return { ...storeNode, position: getFixedOutputPosition(currentViewport), draggable: false };
        }
        
        // 입력 노드는 현재 뷰포트를 고려한 고정 위치로 설정
        if (storeNode.data?.nodeType === NodeType.INPUT) {
          return { ...storeNode, position: getFixedInputPosition(currentViewport), draggable: false };
        }
        
        return existingNode 
          ? { ...storeNode, position: existingNode.position } // 기존 위치 유지
          : storeNode; // 새 노드는 스토어의 위치 사용
      });
      return updatedNodes;
    });
  }, [storeNodes, setNodes, currentViewport]);

  React.useEffect(() => {
    setEdges(storeEdges);
  }, [storeEdges, setEdges]);

  // 뷰포트 보존을 위한 useEffect
  React.useEffect(() => {
    if (reactFlowInstance && currentViewport) {
      // 노드 추가 후 뷰포트가 변경되지 않도록 명시적으로 설정
      const currentInstanceViewport = reactFlowInstance.getViewport();
      if (
        Math.abs(currentInstanceViewport.x - currentViewport.x) > 1 ||
        Math.abs(currentInstanceViewport.y - currentViewport.y) > 1 ||
        Math.abs(currentInstanceViewport.zoom - currentViewport.zoom) > 0.01
      ) {
        reactFlowInstance.setViewport(currentViewport);
      }
    }
  }, [storeNodes.length, reactFlowInstance, currentViewport]); // 노드 개수 변화 시 실행

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
        console.error('노드 삭제 실패:', error.message);
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
    if (event.key === 'Delete' || event.key === 'Backspace') {
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

  return (
    <div style={{ width: '100%', height: '700px', border: '1px solid #d9d9d9', borderRadius: '6px' }}>
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
        nodeTypes={nodeTypes}
        fitView={false}
        snapToGrid
        snapGrid={[15, 15]}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        minZoom={0.5}
        maxZoom={2}
        deleteKeyCode={['Backspace', 'Delete']}
        multiSelectionKeyCode={['Meta', 'Ctrl']}
        panOnDrag={false}
        zoomOnScroll={true}
        zoomOnPinch={true}
        zoomOnDoubleClick={false}
        preventScrolling={true}
        nodesDraggable={true}
        nodesConnectable={true}
        elementsSelectable={true}
        autoPanOnConnect={false}
        autoPanOnNodeDrag={false}
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
          • 중간 노드들만 드래그로 위치 조정 가능<br/>
          • Input/Output 노드는 화면 중앙 상/하단 고정<br/>
          • 노드 Handle에서 드래그로 새 연결 생성<br/>
          • 마우스 휠로 줌 인/아웃 가능
        </div>
      </ReactFlow>
    </div>
  );
};