import React, { useCallback, useState, useRef } from 'react';
import {
  ReactFlow,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  NodeTypes,
  Edge,
  MarkerType,
  ReactFlowProvider,
  ReactFlowInstance,
  OnInit,
  Viewport
} from '@xyflow/react';
import { Space, Typography, Divider } from 'antd';
import CustomNode from './CustomNode';
import PlaceholderNode from './PlaceholderNode';
import NodeEditModal from './NodeEditModal';
import { useWorkflowStore } from '../store/workflowStore';
import { LayerType, WorkflowNodeData, AnyWorkflowNode, WorkflowNode } from '../types';

const { Title } = Typography;

const nodeTypes = {
  customNode: CustomNode as unknown as React.ComponentType<any>,
  placeholderNode: PlaceholderNode as unknown as React.ComponentType<any>,
} as NodeTypes;

const MiniMapNode = (props: any) => {
  const { x, y, width, height, color, strokeColor, strokeWidth, selected } = props;
  
  if (props.type === 'placeholderNode') {
    return <g />;
  }

  return (
    <rect
      x={x}
      y={y}
      width={width}
      height={height}
      fill={color}
      stroke={strokeColor}
      strokeWidth={strokeWidth}
      rx={4}
      opacity={selected ? 1 : 0.8}
    />
  );
};

const WorkflowCanvasContent: React.FC = () => {
  const { 
    nodes, 
    updateNode,
    currentViewport,
    setCurrentViewport
  } = useWorkflowStore();

  const [reactFlowNodes, setReactFlowNodes, onNodesChange] = useNodesState<AnyWorkflowNode>(nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [editingNode, setEditingNode] = useState<WorkflowNodeData | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  
  const reactFlowInstance = useRef<ReactFlowInstance<AnyWorkflowNode, Edge> | null>(null);
  const isRestoringViewport = useRef(false);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: AnyWorkflowNode) => {
    console.log('노드 클릭 이벤트:', node.type, node.id);
    
    if (node.type === 'placeholderNode') {
      console.log('PlaceholderNode 클릭됨:', node.data.layer);
      node.data.onAddNode(node.data.layer);
    }
  }, []);

  const handleNodeDoubleClick = useCallback((event: React.MouseEvent, node: AnyWorkflowNode) => {
    if (node.type === 'placeholderNode') return;
    
    const target = event.target as HTMLElement;
    if (target.closest('button')) return;
    
    event.stopPropagation();
    setEditingNode(node.data);
    setModalVisible(true);
  }, []);

  const handleNodeEdit = useCallback((data: Partial<WorkflowNodeData>) => {
    if (editingNode) {
      updateNode(editingNode.id, data);
      setModalVisible(false);
      setEditingNode(null);
    }
  }, [editingNode, updateNode]);

  const handleViewportChange = useCallback((viewport: Viewport) => {
    if (!isRestoringViewport.current) {
      setCurrentViewport(viewport);
    }
  }, [setCurrentViewport]);

  const handleInit: OnInit<AnyWorkflowNode, Edge> = useCallback((instance) => {
    reactFlowInstance.current = instance;
    
    if (currentViewport) {
      console.log('저장된 뷰포트 복원:', currentViewport);
      isRestoringViewport.current = true;
      instance.setViewport(currentViewport);
      setTimeout(() => {
        isRestoringViewport.current = false;
      }, 100);
    } else {
      const defaultViewport = { x: 20, y: -50, zoom: 0.7 };
      isRestoringViewport.current = true;
      instance.setViewport(defaultViewport);
      setCurrentViewport(defaultViewport);
      setTimeout(() => {
        isRestoringViewport.current = false;
      }, 100);
    }
  }, [currentViewport, setCurrentViewport]);

  // ✅ useImperativeHandle 타입 에러 해결 - 제거
  // React.useImperativeHandle을 제거하고 뷰포트 복원은 store에서 직접 처리

  // ✅ 뷰포트 복원을 위한 useEffect 추가
  React.useEffect(() => {
    if (currentViewport && reactFlowInstance.current) {
      console.log('뷰포트 변경 감지, 복원 중:', currentViewport);
      isRestoringViewport.current = true;
      reactFlowInstance.current.setViewport(currentViewport);
      setTimeout(() => {
        isRestoringViewport.current = false;
      }, 150);
    }
  }, [currentViewport]);

  // Sync with store
  React.useEffect(() => {
    setReactFlowNodes(nodes);
  }, [nodes, setReactFlowNodes]);

  // ✅ Create edges automatically - Property 'id' 에러 완전 해결
  React.useEffect(() => {
    const newEdges: Edge[] = [];
    
    // 안전한 배열 확인 및 타입 가드
    if (!Array.isArray(nodes) || nodes.length === 0) {
      setEdges([]);
      return;
    }

    const realNodes = nodes.filter((n): n is WorkflowNode => {
      return n !== null && 
             n !== undefined && 
             typeof n === 'object' && 
             'type' in n && 
             'id' in n && 
             'data' in n &&
             n.type === 'customNode';
    });

    if (realNodes.length === 0) {
      setEdges([]);
      return;
    }
    
    const generationNodes = realNodes
      .filter(n => n.data && n.data.layer === LayerType.GENERATION)
      .sort((a, b) => (a.position?.x || 0) - (b.position?.x || 0));
    
    const ensembleNodes = realNodes
      .filter(n => n.data && n.data.layer === LayerType.ENSEMBLE);
    
    const validationNodes = realNodes
      .filter(n => n.data && n.data.layer === LayerType.VALIDATION)
      .sort((a, b) => (a.position?.x || 0) - (b.position?.x || 0));

    // Generation -> Ensemble (안전한 접근)
    if (generationNodes.length > 0 && ensembleNodes.length > 0) {
      const ensembleNode = ensembleNodes[0];
      generationNodes.forEach(genNode => {
        if (genNode.id && ensembleNode.id) {
          newEdges.push({
            id: `${genNode.id}-${ensembleNode.id}`,
            source: genNode.id,
            target: ensembleNode.id,
            type: 'default',
            animated: true,
            style: { stroke: '#52c41a', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#52c41a' }
          });
        }
      });
    }

    // Ensemble -> First Validation (안전한 접근)
    if (ensembleNodes.length > 0 && validationNodes.length > 0) {
      const ensembleNode = ensembleNodes[0];
      const firstValidationNode = validationNodes[0];
      
      if (ensembleNode.id && firstValidationNode.id) {
        newEdges.push({
          id: `${ensembleNode.id}-${firstValidationNode.id}`,
          source: ensembleNode.id,
          target: firstValidationNode.id,
          type: 'default',
          animated: true,
          style: { stroke: '#1890ff', strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#1890ff' }
        });
      }
    }

    // Validation chain (안전한 배열 접근)
    if (validationNodes.length > 1) {
      for (let i = 0; i < validationNodes.length - 1; i++) {
        const currentNode = validationNodes[i];
        const nextNode = validationNodes[i + 1];
        
        if (currentNode && nextNode && currentNode.id && nextNode.id) {
          newEdges.push({
            id: `${currentNode.id}-${nextNode.id}`,
            source: currentNode.id,
            target: nextNode.id,
            type: 'default',
            animated: true,
            style: { stroke: '#faad14', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#faad14' }
          });
        }
      }
    }

    setEdges(newEdges);
  }, [nodes, setEdges]);

  // ✅ 안전한 노드 카운트 계산
  const realNodes = Array.isArray(nodes) ? nodes.filter((n): n is WorkflowNode => 
    n && typeof n === 'object' && 'type' in n && n.type === 'customNode'
  ) : [];
  
  const generationCount = realNodes.filter(n => n.data && n.data.layer === LayerType.GENERATION).length;
  const validationCount = realNodes.filter(n => n.data && n.data.layer === LayerType.VALIDATION).length;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 헤더 영역 */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #d9d9d9', background: '#fafafa', flexShrink: 0 }}>
        <Space split={<Divider type="vertical" />}>
          <div>
            <Title level={5} style={{ margin: 0, color: '#52c41a', fontSize: '14px' }}>
              Generation Layer ({generationCount})
            </Title>
          </div>
          <div>
            <Title level={5} style={{ margin: 0, color: '#1890ff', fontSize: '14px' }}>
              Ensemble Layer (1)
            </Title>
          </div>
          <div>
            <Title level={5} style={{ margin: 0, color: '#faad14', fontSize: '14px' }}>
              Validation Layer ({validationCount})
            </Title>
          </div>
        </Space>
      </div>
      
      {/* React Flow 영역 */}
      <div style={{ flex: 1, position: 'relative', minHeight: '500px' }}>
        <ReactFlow<AnyWorkflowNode, Edge>
          nodes={reactFlowNodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={handleNodeClick}
          onNodeDoubleClick={handleNodeDoubleClick}
          nodeTypes={nodeTypes}
          onInit={handleInit}
          onViewportChange={handleViewportChange}
          fitView={false}
          defaultViewport={{ x: 20, y: -50, zoom: 0.7 }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={true}
          selectNodesOnDrag={false}
          panOnDrag={true}
          zoomOnScroll={true}
          zoomOnPinch={true}
          zoomOnDoubleClick={true}
          preventScrolling={true}
          minZoom={0.3}
          maxZoom={1.5}
          style={{ width: '100%', height: '100%' }}
        >
          <Background />
          
          <MiniMap 
            position="top-right"
            nodeComponent={MiniMapNode}
            nodeStrokeWidth={2}
            nodeColor={(node) => {
              const nodeData = node.data as any;
              switch (nodeData.layer) {
                case LayerType.GENERATION: return '#52c41a';
                case LayerType.ENSEMBLE: return '#1890ff';
                case LayerType.VALIDATION: return '#faad14';
                default: return '#e0e0e0';
              }
            }}
            style={{
              backgroundColor: '#f8f9fa',
              border: '1px solid #e0e0e0',
              borderRadius: '8px',
              marginTop: '8px',
              marginRight: '8px'
            }}
            pannable
            zoomable
          />
        </ReactFlow>
      </div>

      <NodeEditModal
        visible={modalVisible}
        nodeData={editingNode}
        onSave={handleNodeEdit}
        onCancel={() => {
          setModalVisible(false);
          setEditingNode(null);
        }}
      />
    </div>
  );
};

const WorkflowCanvas: React.FC = () => {
  return (
    <ReactFlowProvider>
      <WorkflowCanvasContent />
    </ReactFlowProvider>
  );
};

export default WorkflowCanvas;
