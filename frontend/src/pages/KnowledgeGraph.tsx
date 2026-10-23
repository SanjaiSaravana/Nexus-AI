import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  Share2,
  Search,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Sparkles,
  Send,
  Code,
  Layers,
  FolderKanban,
  Cpu,
  Brain,
  FileText,
  Target,
  CheckSquare,
  Building,
  Briefcase,
  Hash,
  X,
  Trash2,
  ChevronRight,
  Database
} from 'lucide-react';
import { api } from '../services/api';
import type { GraphData, GraphNode, GraphStats, GraphQueryResponse } from '../types';

// Palette for entity labels
const ENTITY_COLORS: Record<string, { bg: string; border: string; glow: string; text: string }> = {
  User: { bg: '#6366f1', border: '#818cf8', glow: 'rgba(99, 102, 241, 0.4)', text: '#ffffff' },
  Project: { bg: '#10b981', border: '#34d399', glow: 'rgba(16, 185, 129, 0.4)', text: '#ffffff' },
  Skill: { bg: '#f59e0b', border: '#fbbf24', glow: 'rgba(245, 158, 11, 0.4)', text: '#ffffff' },
  Technology: { bg: '#0ea5e9', border: '#38bdf8', glow: 'rgba(14, 165, 233, 0.4)', text: '#ffffff' },
  Document: { bg: '#8b5cf6', border: '#a78bfa', glow: 'rgba(139, 92, 246, 0.4)', text: '#ffffff' },
  Task: { bg: '#f43f5e', border: '#fb7185', glow: 'rgba(244, 63, 94, 0.4)', text: '#ffffff' },
  Goal: { bg: '#14b8a6', border: '#2dd4bf', glow: 'rgba(20, 184, 166, 0.4)', text: '#ffffff' },
  Event: { bg: '#f97316', border: '#fb923c', glow: 'rgba(249, 115, 22, 0.4)', text: '#ffffff' },
  Company: { bg: '#3b82f6', border: '#60a5fa', glow: 'rgba(59, 130, 246, 0.4)', text: '#ffffff' },
  Job: { bg: '#d946ef', border: '#e879f9', glow: 'rgba(217, 70, 239, 0.4)', text: '#ffffff' },
  Topic: { bg: '#84cc16', border: '#a3e635', glow: 'rgba(132, 204, 22, 0.4)', text: '#ffffff' },
};

const DEFAULT_COLOR = { bg: '#64748b', border: '#94a3b8', glow: 'rgba(100, 116, 139, 0.3)', text: '#ffffff' };

const QUICK_PROMPTS = [
  'What projects do I have that use Python?',
  'What skills do I know?',
  'What tasks support my goals?',
  'What technologies does Nexus AI use?',
  'What jobs require skills?'
];

export const KnowledgeGraph: React.FC = () => {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & search
  const [selectedLabel, setSelectedLabel] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Selected node drawer
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // NL Query bar state
  const [nlQuery, setNlQuery] = useState<string>('');
  const [isQuerying, setIsQuerying] = useState<boolean>(false);
  const [queryResult, setQueryResult] = useState<GraphQueryResponse | null>(null);

  // Canvas ref & transform
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [transform, setTransform] = useState<{ x: number; y: number; k: number }>({ x: 0, y: 0, k: 1 });
  const isDraggingCanvas = useRef<boolean>(false);
  const dragStart = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const draggedNode = useRef<GraphNode | null>(null);

  // Physics simulation nodes copy
  const simNodes = useRef<Map<string, { x: number; y: number; vx: number; vy: number; radius: number }>>(new Map());

  // Load Graph & Stats
  const loadGraph = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [data, statsData] = await Promise.all([
        api.knowledgeGraph.getGraph({ limit: 400 }),
        api.knowledgeGraph.getStats(),
      ]);
      setGraphData(data);
      setStats(statsData);

      // Initialize simulation positions
      const width = 1000;
      const height = 650;
      data.nodes.forEach((node, idx) => {
        if (!simNodes.current.has(node.id)) {
          const angle = (idx / Math.max(1, data.nodes.length)) * 2 * Math.PI;
          const radius = 150 + Math.random() * 200;
          simNodes.current.set(node.id, {
            x: width / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 50,
            y: height / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 50,
            vx: 0,
            vy: 0,
            radius: node.label === 'User' ? 32 : (node.label === 'Project' ? 26 : 20),
          });
        }
      });
    } catch (err: any) {
      setError(err?.message || 'Failed to load knowledge graph data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Sync relational database
  const handleSyncDatabase = async () => {
    setIsSyncing(true);
    try {
      await api.knowledgeGraph.sync();
      await loadGraph();
    } catch (err: any) {
      alert(`Sync failed: ${err?.message || 'Unknown error'}`);
    } finally {
      setIsSyncing(false);
    }
  };

  // Run NL Query
  const handleRunQuery = async (queryToRun?: string) => {
    const q = (queryToRun || nlQuery).trim();
    if (!q) return;
    setIsQuerying(true);
    try {
      const res = await api.knowledgeGraph.query(q);
      setQueryResult(res);
      // Select first node if available
      if (res.nodes.length > 0) {
        setSelectedNode(res.nodes[0]);
      }
    } catch (err: any) {
      alert(`Query failed: ${err?.message || 'Unknown error'}`);
    } finally {
      setIsQuerying(false);
    }
  };

  // Node delete handler
  const handleDeleteNode = async (nodeId: string) => {
    if (!window.confirm('Are you sure you want to delete this node from the graph?')) return;
    try {
      await api.knowledgeGraph.deleteNode(nodeId);
      setSelectedNode(null);
      await loadGraph();
    } catch (err: any) {
      alert(`Delete failed: ${err?.message || 'Unknown error'}`);
    }
  };

  // Filtered nodes and edges
  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    if (selectedLabel !== 'All') {
      nodes = nodes.filter((n) => n.label === selectedLabel);
    }
    if (searchQuery.trim()) {
      const s = searchQuery.toLowerCase();
      nodes = nodes.filter((n) => n.name.toLowerCase().includes(s) || n.label.toLowerCase().includes(s));
    }
    const nodeIds = new Set(nodes.map((n) => n.id));
    const edges = graphData.edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
    return { nodes, edges };
  }, [graphData, selectedLabel, searchQuery]);

  // Highlighted IDs from query result
  const highlightedNodeIds = useMemo(() => {
    if (!queryResult) return new Set<string>();
    return new Set(queryResult.nodes.map((n) => n.id));
  }, [queryResult]);

  // Node details relations
  const nodeRelations = useMemo(() => {
    if (!selectedNode) return { incoming: [], outgoing: [] };
    const outgoing = graphData.edges
      .filter((e) => e.source === selectedNode.id)
      .map((e) => ({
        edge: e,
        targetNode: graphData.nodes.find((n) => n.id === e.target),
      }));
    const incoming = graphData.edges
      .filter((e) => e.target === selectedNode.id)
      .map((e) => ({
        edge: e,
        sourceNode: graphData.nodes.find((n) => n.id === e.source),
      }));
    return { incoming, outgoing };
  }, [selectedNode, graphData]);

  // Force simulation tick & canvas render
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;

      // 1. Physics Step
      const nodes = filteredData.nodes;
      const edges = filteredData.edges;

      // Repulsion between all node pairs
      for (let i = 0; i < nodes.length; i++) {
        const uId = nodes[i].id;
        const u = simNodes.current.get(uId);
        if (!u) continue;

        for (let j = i + 1; j < nodes.length; j++) {
          const vId = nodes[j].id;
          const v = simNodes.current.get(vId);
          if (!v) continue;

          const dx = v.x - u.x;
          const dy = v.y - u.y;
          const distSq = dx * dx + dy * dy + 1;
          const dist = Math.sqrt(distSq);
          const force = 1200 / distSq;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          if (draggedNode.current?.id !== uId) {
            u.vx -= fx;
            u.vy -= fy;
          }
          if (draggedNode.current?.id !== vId) {
            v.vx += fx;
            v.vy += fy;
          }
        }

        // Center gravity
        const centerDx = width / 2 - u.x;
        const centerDy = height / 2 - u.y;
        u.vx += centerDx * 0.0006;
        u.vy += centerDy * 0.0006;
      }

      // Spring attraction along edges
      edges.forEach((edge) => {
        const u = simNodes.current.get(edge.source);
        const v = simNodes.current.get(edge.target);
        if (u && v) {
          const dx = v.x - u.x;
          const dy = v.y - u.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const targetDist = 140;
          const springForce = (dist - targetDist) * 0.03;
          const fx = (dx / dist) * springForce;
          const fy = (dy / dist) * springForce;

          if (draggedNode.current?.id !== edge.source) {
            u.vx += fx;
            u.vy += fy;
          }
          if (draggedNode.current?.id !== edge.target) {
            v.vx -= fx;
            v.vy -= fy;
          }
        }
      });

      // Update positions with damping
      nodes.forEach((n) => {
        const pos = simNodes.current.get(n.id);
        if (pos) {
          if (draggedNode.current?.id !== n.id) {
            pos.vx *= 0.85;
            pos.vy *= 0.85;
            pos.x += pos.vx;
            pos.y += pos.vy;
          }
        }
      });

      // 2. Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Grid background
      ctx.save();
      ctx.translate(transform.x, transform.y);
      ctx.scale(transform.k, transform.k);

      // Draw faint grid
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
      ctx.lineWidth = 1;
      const gridSize = 40;
      for (let x = -width * 2; x < width * 3; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, -height * 2);
        ctx.lineTo(x, height * 3);
        ctx.stroke();
      }
      for (let y = -height * 2; y < height * 3; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(-width * 2, y);
        ctx.lineTo(width * 3, y);
        ctx.stroke();
      }

      // 3. Draw Edges
      edges.forEach((edge) => {
        const u = simNodes.current.get(edge.source);
        const v = simNodes.current.get(edge.target);
        if (!u || !v) return;

        const isHighlighted = highlightedNodeIds.has(edge.source) && highlightedNodeIds.has(edge.target);
        const isSelected = selectedNode && (edge.source === selectedNode.id || edge.target === selectedNode.id);

        ctx.strokeStyle = isSelected
          ? '#818cf8'
          : isHighlighted
          ? '#38bdf8'
          : 'rgba(255, 255, 255, 0.15)';
        ctx.lineWidth = isSelected || isHighlighted ? 2.5 : 1.2;

        ctx.beginPath();
        ctx.moveTo(u.x, u.y);
        ctx.lineTo(v.x, v.y);
        ctx.stroke();

        // Edge direction arrow
        const angle = Math.atan2(v.y - u.y, v.x - u.x);
        const arrowDist = 12;
        const arrowX = v.x - Math.cos(angle) * (v.radius + 6);
        const arrowY = v.y - Math.sin(angle) * (v.radius + 6);

        ctx.fillStyle = ctx.strokeStyle;
        ctx.beginPath();
        ctx.moveTo(arrowX, arrowY);
        ctx.lineTo(
          arrowX - arrowDist * Math.cos(angle - Math.PI / 7),
          arrowY - arrowDist * Math.sin(angle - Math.PI / 7)
        );
        ctx.lineTo(
          arrowX - arrowDist * Math.cos(angle + Math.PI / 7),
          arrowY - arrowDist * Math.sin(angle + Math.PI / 7)
        );
        ctx.closePath();
        ctx.fill();

        // Edge label pill
        const midX = (u.x + v.x) / 2;
        const midY = (u.y + v.y) / 2;
        ctx.font = '10px Inter, sans-serif';
        const labelText = edge.type;
        const textWidth = ctx.measureText(labelText).width;

        ctx.fillStyle = 'rgba(7, 9, 14, 0.85)';
        ctx.beginPath();
        ctx.roundRect(midX - textWidth / 2 - 4, midY - 7, textWidth + 8, 14, 3);
        ctx.fill();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.stroke();

        ctx.fillStyle = isSelected || isHighlighted ? '#a5b4fc' : '#94a3b8';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(labelText, midX, midY);
      });

      // 4. Draw Nodes
      nodes.forEach((node) => {
        const pos = simNodes.current.get(node.id);
        if (!pos) return;

        const colors = ENTITY_COLORS[node.label] || DEFAULT_COLOR;
        const isSelected = selectedNode?.id === node.id;
        const isHighlighted = highlightedNodeIds.has(node.id);

        // Glow ring if selected or highlighted
        if (isSelected || isHighlighted) {
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, pos.radius + 8, 0, 2 * Math.PI);
          ctx.fillStyle = colors.glow;
          ctx.fill();
        }

        // Main node circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, pos.radius, 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? colors.border : colors.bg;
        ctx.fill();
        ctx.strokeStyle = isSelected ? '#ffffff' : colors.border;
        ctx.lineWidth = isSelected ? 3 : 1.5;
        ctx.stroke();

        // Node Label Initial / Badge
        ctx.font = `600 ${pos.radius > 24 ? 13 : 10}px Inter, sans-serif`;
        ctx.fillStyle = colors.text;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const shortName = node.name.length > 12 ? node.name.substring(0, 10) + '..' : node.name;
        ctx.fillText(shortName, pos.x, pos.y);

        // Subtitle pill under node
        ctx.font = '10px Inter, sans-serif';
        ctx.fillStyle = colors.border;
        ctx.fillText(node.label, pos.x, pos.y + pos.radius + 12);
      });

      ctx.restore();
      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [filteredData, selectedNode, highlightedNodeIds, transform]);

  // Mouse interaction on canvas
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = (e.clientX - rect.left - transform.x) / transform.k;
    const mouseY = (e.clientY - rect.top - transform.y) / transform.k;

    // Check if clicked on a node
    for (const node of filteredData.nodes) {
      const pos = simNodes.current.get(node.id);
      if (pos) {
        const dx = mouseX - pos.x;
        const dy = mouseY - pos.y;
        if (dx * dx + dy * dy <= pos.radius * pos.radius) {
          draggedNode.current = node;
          setSelectedNode(node);
          return;
        }
      }
    }

    // Otherwise drag canvas
    isDraggingCanvas.current = true;
    dragStart.current = { x: e.clientX - transform.x, y: e.clientY - transform.y };
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    if (draggedNode.current) {
      const rect = canvas.getBoundingClientRect();
      const mouseX = (e.clientX - rect.left - transform.x) / transform.k;
      const mouseY = (e.clientY - rect.top - transform.y) / transform.k;
      const pos = simNodes.current.get(draggedNode.current.id);
      if (pos) {
        pos.x = mouseX;
        pos.y = mouseY;
        pos.vx = 0;
        pos.vy = 0;
      }
      return;
    }

    if (isDraggingCanvas.current) {
      setTransform((prev) => ({
        ...prev,
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y,
      }));
    }
  };

  const handleMouseUp = () => {
    isDraggingCanvas.current = false;
    draggedNode.current = null;
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setTransform((prev) => ({
      ...prev,
      k: Math.max(0.2, Math.min(3.5, prev.k * zoomFactor)),
    }));
  };

  const zoomIn = () => setTransform((prev) => ({ ...prev, k: Math.min(3.5, prev.k * 1.25) }));
  const zoomOut = () => setTransform((prev) => ({ ...prev, k: Math.max(0.2, prev.k * 0.8) }));
  const resetView = () => setTransform({ x: 0, y: 0, k: 1 });

  const labelCategories: { label: string; icon: any; count?: number }[] = [
    { label: 'All', icon: Layers, count: graphData.nodes.length },
    { label: 'Project', icon: FolderKanban, count: stats?.node_counts?.Project || 0 },
    { label: 'Skill', icon: Brain, count: stats?.node_counts?.Skill || 0 },
    { label: 'Technology', icon: Cpu, count: stats?.node_counts?.Technology || 0 },
    { label: 'Document', icon: FileText, count: stats?.node_counts?.Document || 0 },
    { label: 'Goal', icon: Target, count: stats?.node_counts?.Goal || 0 },
    { label: 'Task', icon: CheckSquare, count: stats?.node_counts?.Task || 0 },
    { label: 'Company', icon: Building, count: stats?.node_counts?.Company || 0 },
    { label: 'Job', icon: Briefcase, count: stats?.node_counts?.Job || 0 },
    { label: 'Topic', icon: Hash, count: stats?.node_counts?.Topic || 0 },
  ];

  return (
    <div className="knowledge-graph-page" style={{ padding: '24px', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Top Banner / Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 700, margin: 0 }}>Neo4j Knowledge Graph</h1>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: '20px',
              fontSize: '0.75rem',
              color: '#34d399',
              fontWeight: 600
            }}>
              <Database size={12} />
              Connected & Partitioned
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>
            Semantic relationship intelligence linking Projects, Skills, Technologies, Documents, Goals, and Tasks.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            onClick={handleSyncDatabase}
            disabled={isSyncing}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <RefreshCw size={16} className={isSyncing ? 'animate-spin' : ''} />
            <span>{isSyncing ? 'Syncing...' : 'Sync Graph with DB'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          borderRadius: 'var(--radius-md)',
          color: '#fb7185',
          marginBottom: '20px',
          fontSize: '0.9rem'
        }}>
          {error}
        </div>
      )}

      {/* Metrics Summary Strip */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: '12px',
        marginBottom: '20px'
      }}>
        <div className="stat-card" style={{ padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Entities</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>{stats?.total_nodes || 0}</div>
        </div>
        <div className="stat-card" style={{ padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Relationships</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--primary)' }}>{stats?.total_edges || 0}</div>
        </div>
        <div className="stat-card" style={{ padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Projects</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981' }}>{stats?.node_counts?.Project || 0}</div>
        </div>
        <div className="stat-card" style={{ padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Skills Tracked</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f59e0b' }}>{stats?.node_counts?.Skill || 0}</div>
        </div>
        <div className="stat-card" style={{ padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Technologies</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0ea5e9' }}>{stats?.node_counts?.Technology || 0}</div>
        </div>
        <div className="stat-card" style={{ padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Documents</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#8b5cf6' }}>{stats?.node_counts?.Document || 0}</div>
        </div>
        <div className="stat-card" style={{ padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Goals & Tasks</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#14b8a6' }}>
            {(stats?.node_counts?.Goal || 0) + (stats?.node_counts?.Task || 0)}
          </div>
        </div>
      </div>

      {/* Natural Language Query Bar */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-card)',
        borderRadius: 'var(--radius-lg)',
        padding: '16px',
        marginBottom: '20px',
        boxShadow: 'var(--shadow-md)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          <Sparkles size={18} style={{ color: 'var(--primary)' }} />
          <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Ask Graph Retrieval</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            (Translates natural language questions to graph traversals)
          </span>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder='e.g., "What projects do I have that use Python?" or "What tasks support my goals?"'
              value={nlQuery}
              onChange={(e) => setNlQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleRunQuery()}
              style={{
                width: '100%',
                padding: '10px 14px 10px 38px',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                fontSize: '0.95rem'
              }}
            />
          </div>
          <button
            onClick={() => handleRunQuery()}
            disabled={isQuerying || !nlQuery.trim()}
            className="btn btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Send size={15} />
            <span>{isQuerying ? 'Querying...' : 'Query Graph'}</span>
          </button>
        </div>

        {/* Quick prompt suggestions */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Examples:</span>
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => {
                setNlQuery(prompt);
                handleRunQuery(prompt);
              }}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '16px',
                padding: '3px 10px',
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--primary)')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Query Result Card */}
        {queryResult && (
          <div style={{
            marginTop: '14px',
            padding: '12px 16px',
            background: 'rgba(99, 102, 241, 0.08)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            borderRadius: 'var(--radius-md)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '0.8rem', color: '#818cf8', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Code size={14} />
                  <span>Intent: {queryResult.intent}</span>
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
                  {queryResult.answer}
                </div>
              </div>
              <button
                onClick={() => setQueryResult(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={16} />
              </button>
            </div>

            {queryResult.cypher && (
              <div style={{
                marginTop: '8px',
                padding: '6px 10px',
                background: 'rgba(0, 0, 0, 0.3)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                color: '#94a3b8'
              }}>
                Cypher: {queryResult.cypher}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main Graph Viewer Container */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: selectedNode ? '1fr 340px' : '1fr',
        gap: '20px',
        position: 'relative'
      }}>
        {/* Graph Canvas Panel */}
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-card)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          position: 'relative',
          height: '680px',
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Controls & Filter Bar */}
          <div style={{
            padding: '12px 16px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'rgba(13, 17, 26, 0.75)',
            flexWrap: 'wrap',
            gap: '10px',
            zIndex: 10
          }}>
            {/* Category Filter Pills */}
            <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', maxWidth: '75%', paddingBottom: '4px' }}>
              {labelCategories.map((cat) => {
                const Icon = cat.icon;
                const isActive = selectedLabel === cat.label;
                const color = cat.label === 'All' ? '#6366f1' : (ENTITY_COLORS[cat.label]?.border || '#94a3b8');
                return (
                  <button
                    key={cat.label}
                    onClick={() => setSelectedLabel(cat.label)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 10px',
                      borderRadius: '16px',
                      border: `1px solid ${isActive ? color : 'var(--border-subtle)'}`,
                      background: isActive ? `${color}25` : 'transparent',
                      color: isActive ? '#ffffff' : 'var(--text-secondary)',
                      fontSize: '0.75rem',
                      fontWeight: isActive ? 600 : 400,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    <Icon size={13} style={{ color }} />
                    <span>{cat.label}</span>
                    {cat.count !== undefined && cat.count > 0 && (
                      <span style={{ fontSize: '0.65rem', opacity: 0.75 }}>({cat.count})</span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Canvas Zoom & Pan Tools + Search */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ position: 'relative' }}>
                <Search size={13} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Filter nodes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    padding: '4px 8px 4px 26px',
                    fontSize: '0.75rem',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '14px',
                    color: 'var(--text-primary)',
                    width: '120px'
                  }}
                />
              </div>

              <button
                onClick={zoomIn}
                className="btn-icon"
                title="Zoom In"
                style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '6px', color: 'var(--text-secondary)', cursor: 'pointer' }}
              >
                <ZoomIn size={15} />
              </button>
              <button
                onClick={zoomOut}
                className="btn-icon"
                title="Zoom Out"
                style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '6px', color: 'var(--text-secondary)', cursor: 'pointer' }}
              >
                <ZoomOut size={15} />
              </button>
              <button
                onClick={resetView}
                className="btn-icon"
                title="Fit / Reset View"
                style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '6px', color: 'var(--text-secondary)', cursor: 'pointer' }}
              >
                <Maximize2 size={15} />
              </button>
            </div>
          </div>

          {/* Interactive HTML5 Canvas */}
          <div style={{ flex: 1, position: 'relative', cursor: 'grab' }}>
            {isLoading && (
              <div style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(7, 9, 14, 0.7)',
                zIndex: 20
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)' }}>
                  <RefreshCw size={20} className="animate-spin" />
                  <span>Loading Knowledge Graph...</span>
                </div>
              </div>
            )}

            {filteredData.nodes.length === 0 && !isLoading && (
              <div style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-muted)',
                gap: '12px'
              }}>
                <Share2 size={36} />
                <p>No knowledge graph nodes found for the selected filter.</p>
                <button onClick={handleSyncDatabase} className="btn btn-secondary" style={{ fontSize: '0.85rem' }}>
                  Sync User Records into Graph
                </button>
              </div>
            )}

            <canvas
              ref={canvasRef}
              width={1050}
              height={620}
              style={{ width: '100%', height: '100%', display: 'block' }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onWheel={handleWheel}
            />

            {/* Help Hint Overlay */}
            <div style={{
              position: 'absolute',
              bottom: '12px',
              left: '16px',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              background: 'rgba(7, 9, 14, 0.7)',
              padding: '4px 10px',
              borderRadius: '6px',
              pointerEvents: 'none'
            }}>
              Scroll to zoom • Click & drag nodes or canvas • Click node for details
            </div>
          </div>
        </div>

        {/* Selected Node Details Drawer */}
        {selectedNode && (
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-card)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            maxHeight: '680px',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  background: ENTITY_COLORS[selectedNode.label]?.bg || '#64748b',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff'
                }}>
                  <Share2 size={18} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, wordBreak: 'break-word' }}>
                    {selectedNode.name}
                  </h3>
                  <span style={{
                    fontSize: '0.75rem',
                    color: ENTITY_COLORS[selectedNode.label]?.border || '#818cf8',
                    fontWeight: 600
                  }}>
                    {selectedNode.label}
                  </span>
                </div>
              </div>

              <button
                onClick={() => setSelectedNode(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Properties section */}
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
                Properties
              </div>
              <div style={{ background: 'var(--bg-input)', borderRadius: 'var(--radius-md)', padding: '10px', fontSize: '0.8rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Node ID:</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{selectedNode.id.substring(0, 8)}...</span>
                </div>
                {Object.entries(selectedNode.properties || {}).map(([key, val]) => (
                  <div key={key} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{key}:</span>
                    <span style={{ color: 'var(--text-primary)', wordBreak: 'break-word' }}>
                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Outgoing Relations */}
            {nodeRelations.outgoing.length > 0 && (
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
                  Outgoing Connections ({nodeRelations.outgoing.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {nodeRelations.outgoing.map(({ edge, targetNode }) => (
                    <div
                      key={edge.id}
                      onClick={() => targetNode && setSelectedNode(targetNode)}
                      style={{
                        padding: '8px 10px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)')}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.75rem', color: '#818cf8', fontWeight: 600 }}>
                          --[{edge.type}]-&gt;
                        </span>
                        <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                          {targetNode?.name || 'Unknown'}
                        </span>
                      </div>
                      <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Incoming Relations */}
            {nodeRelations.incoming.length > 0 && (
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
                  Incoming Connections ({nodeRelations.incoming.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {nodeRelations.incoming.map(({ edge, sourceNode }) => (
                    <div
                      key={edge.id}
                      onClick={() => sourceNode && setSelectedNode(sourceNode)}
                      style={{
                        padding: '8px 10px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)')}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                          {sourceNode?.name || 'Unknown'}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600 }}>
                          -[{edge.type}]-&gt;
                        </span>
                      </div>
                      <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Node Actions */}
            <div style={{ marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
              <button
                onClick={() => handleDeleteNode(selectedNode.id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  padding: '8px',
                  background: 'rgba(244, 63, 94, 0.1)',
                  border: '1px solid rgba(244, 63, 94, 0.3)',
                  borderRadius: 'var(--radius-md)',
                  color: '#fb7185',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                <Trash2 size={14} />
                <span>Delete Node</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
