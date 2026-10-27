'use client'

import React, { useState, useMemo } from 'react'
import { GraphBlock as GraphBlockType, GraphNodeData } from '../../types'
import { Network, ZoomIn, ZoomOut, RotateCcw, Info, User, FileText, Shield, Building2, Stethoscope, X } from 'lucide-react'

type Props = {
    block: GraphBlockType
    isDark: boolean
}

const TYPE_CONFIG: Record<
    string,
    { color: string; stroke: string; bgLight: string; bgDark: string; icon: any; label: string }
> = {
    Assure: {
        color: '#10b981', // emerald
        stroke: '#059669',
        bgLight: '#ecfdf5',
        bgDark: '#064e3b',
        icon: User,
        label: 'Assuré',
    },
    BulletinSoin: {
        color: '#f59e0b', // amber
        stroke: '#d97706',
        bgLight: '#fffbeb',
        bgDark: '#78350f',
        icon: FileText,
        label: 'Bulletin de Soin',
    },
    InsuranceContract: {
        color: '#06b6d4', // cyan
        stroke: '#0891b2',
        bgLight: '#ecfeff',
        bgDark: '#164e63',
        icon: Shield,
        label: 'Contrat',
    },
    Company: {
        color: '#3b82f6', // blue
        stroke: '#2563eb',
        bgLight: '#eff6ff',
        bgDark: '#1e3a8a',
        icon: Building2,
        label: 'Compagnie',
    },
    Provider: {
        color: '#8b5cf6', // purple
        stroke: '#7c3aed',
        bgLight: '#f5f3ff',
        bgDark: '#4c1d95',
        icon: Stethoscope,
        label: 'Prestataire',
    },
}

export default function InteractiveGraphBlock({ block, isDark }: Props) {
    const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null)
    const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)
    const [zoom, setZoom] = useState(1)
    const [activeTypeFilter, setActiveTypeFilter] = useState<string>('all')

    // Generate responsive circular / radial coordinates for the nodes
    const nodePositions = useMemo(() => {
        const nodes = block.nodes || []
        const count = nodes.length
        const width = 640
        const height = 360
        const centerX = width / 2
        const centerY = height / 2

        const positions: Record<string, { x: number; y: number }> = {}

        if (count === 0) return positions

        if (count === 1) {
            positions[nodes[0].id] = { x: centerX, y: centerY }
            return positions
        }

        // Two rings: primary entities in center ring, secondary around
        const radius = Math.min(width, height) * 0.36

        nodes.forEach((node, idx) => {
            // Distribute uniformly along an ellipse
            const angle = (2 * Math.PI * idx) / count - Math.PI / 2
            const rx = radius * 1.15
            const ry = radius * 0.85
            positions[node.id] = {
                x: centerX + rx * Math.cos(angle),
                y: centerY + ry * Math.sin(angle),
            }
        })

        return positions
    }, [block.nodes])

    // Find connected nodes and edges for hover highlighting
    const connectedEdges = useMemo(() => {
        if (!hoveredNodeId) return new Set<string>()
        const set = new Set<string>()
        ;(block.edges || []).forEach((e, idx) => {
            if (e.source === hoveredNodeId || e.target === hoveredNodeId) {
                set.add(`${e.source}-${e.target}-${idx}`)
            }
        })
        return set
    }, [hoveredNodeId, block.edges])

    const connectedNodeIds = useMemo(() => {
        if (!hoveredNodeId) return new Set<string>()
        const set = new Set<string>([hoveredNodeId])
        ;(block.edges || []).forEach((e) => {
            if (e.source === hoveredNodeId) set.add(e.target)
            if (e.target === hoveredNodeId) set.add(e.source)
        })
        return set
    }, [hoveredNodeId, block.edges])

    // Unique types present
    const availableTypes = useMemo(() => {
        const types = new Set<string>()
        ;(block.nodes || []).forEach((n) => types.add(n.type))
        return Array.from(types)
    }, [block.nodes])

    return (
        <div
            className={`rounded-2xl border overflow-hidden transition-all duration-300 ${
                isDark ? 'bg-gray-950/80 border-gray-800 shadow-xl shadow-black/50' : 'bg-white border-gray-200/90 shadow-sm'
            }`}
        >
            {/* Header Toolbar */}
            <div
                className={`flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b ${
                    isDark ? 'border-gray-800 bg-gray-900/60' : 'border-gray-100 bg-slate-50/70'
                }`}
            >
                <div className="flex items-center gap-2">
                    <Network className="h-4 w-4 text-emerald-500" />
                    <div>
                        <h3 className={`text-xs font-bold uppercase tracking-wider ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
                            {block.title || 'Graphe Relationnel Neo4j'}
                        </h3>
                        {block.description && (
                            <p className={`text-[10px] ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                                {block.description}
                            </p>
                        )}
                    </div>
                </div>

                {/* Filter & Zoom Buttons */}
                <div className="flex items-center gap-1.5">
                    {/* Zoom Controls */}
                    <div className="flex items-center gap-0.5 rounded-lg border border-black/10 dark:border-white/10 p-0.5">
                        <button
                            onClick={() => setZoom((z) => Math.min(z + 0.15, 1.6))}
                            className="p-1 rounded hover:bg-black/5 dark:hover:bg-white/10 text-gray-500 dark:text-gray-400"
                            title="Zoom avant"
                        >
                            <ZoomIn className="h-3.5 w-3.5" />
                        </button>
                        <button
                            onClick={() => setZoom((z) => Math.max(z - 0.15, 0.7))}
                            className="p-1 rounded hover:bg-black/5 dark:hover:bg-white/10 text-gray-500 dark:text-gray-400"
                            title="Zoom arrière"
                        >
                            <ZoomOut className="h-3.5 w-3.5" />
                        </button>
                        <button
                            onClick={() => setZoom(1)}
                            className="p-1 rounded hover:bg-black/5 dark:hover:bg-white/10 text-gray-500 dark:text-gray-400"
                            title="Réinitialiser"
                        >
                            <RotateCcw className="h-3 w-3" />
                        </button>
                    </div>

                    {/* Filter Pills */}
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => setActiveTypeFilter('all')}
                            className={`px-2 py-0.5 rounded-md text-[10px] font-semibold transition-all ${
                                activeTypeFilter === 'all'
                                    ? isDark
                                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                    : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                            }`}
                        >
                            Tous ({block.nodes?.length || 0})
                        </button>
                        {availableTypes.map((type) => {
                            const conf = TYPE_CONFIG[type]
                            return (
                                <button
                                    key={type}
                                    onClick={() => setActiveTypeFilter(type)}
                                    className={`px-2 py-0.5 rounded-md text-[10px] font-semibold transition-all ${
                                        activeTypeFilter === type
                                            ? isDark
                                                ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40'
                                                : 'bg-teal-100 text-teal-800 border border-teal-200'
                                            : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                                    }`}
                                >
                                    {conf?.label || type}
                                </button>
                            )
                        })}
                    </div>
                </div>
            </div>

            {/* Interactive SVG Viewport */}
            <div className="relative h-[380px] w-full overflow-hidden select-none bg-gradient-to-b from-transparent to-black/[0.02] dark:to-white/[0.02]">
                <svg
                    viewBox="0 0 640 360"
                    className="w-full h-full cursor-grab active:cursor-grabbing transition-transform duration-200"
                    style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
                >
                    <defs>
                        {/* Glow filters */}
                        <filter id="glow-teal" x="-20%" y="-20%" width="140%" height="140%">
                            <feGaussianBlur stdDeviation="3" result="blur" />
                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                        </filter>
                        <filter id="glow-emerald" x="-20%" y="-20%" width="140%" height="140%">
                            <feGaussianBlur stdDeviation="4" result="blur" />
                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                        </filter>

                        {/* Arrow marker */}
                        <marker
                            id="arrowhead"
                            markerWidth="8"
                            markerHeight="6"
                            refX="18"
                            refY="3"
                            orient="auto"
                        >
                            <polygon
                                points="0 0, 8 3, 0 6"
                                fill={isDark ? '#6ee7b7' : '#059669'}
                                opacity="0.8"
                            />
                        </marker>
                    </defs>

                    {/* Edge lines */}
                    {(block.edges || []).map((edge, idx) => {
                        const sourcePos = nodePositions[edge.source]
                        const targetPos = nodePositions[edge.target]
                        if (!sourcePos || !targetPos) return null

                        const edgeKey = `${edge.source}-${edge.target}-${idx}`
                        const isHighlighted = connectedEdges.has(edgeKey)
                        const isDimmed = hoveredNodeId && !isHighlighted

                        // Midpoint for relationship label
                        const midX = (sourcePos.x + targetPos.x) / 2
                        const midY = (sourcePos.y + targetPos.y) / 2

                        return (
                            <g key={edgeKey} className="transition-opacity duration-300" opacity={isDimmed ? 0.15 : 1}>
                                <line
                                    x1={sourcePos.x}
                                    y1={sourcePos.y}
                                    x2={targetPos.x}
                                    y2={targetPos.y}
                                    stroke={
                                        isHighlighted
                                            ? '#10b981'
                                            : isDark
                                            ? '#334155'
                                            : '#cbd5e1'
                                    }
                                    strokeWidth={isHighlighted ? 2.5 : 1.5}
                                    strokeDasharray={isHighlighted ? undefined : '3,3'}
                                    markerEnd="url(#arrowhead)"
                                />
                                {/* Relationship Badge */}
                                <g transform={`translate(${midX}, ${midY})`}>
                                    <rect
                                        x="-38"
                                        y="-9"
                                        width="76"
                                        height="18"
                                        rx="9"
                                        fill={isDark ? '#090d16' : '#ffffff'}
                                        stroke={isHighlighted ? '#10b981' : isDark ? '#1e293b' : '#e2e8f0'}
                                        strokeWidth="1"
                                    />
                                    <text
                                        textAnchor="middle"
                                        y="3.5"
                                        fontSize="8"
                                        fontWeight="bold"
                                        className="font-mono tracking-wider select-none"
                                        fill={isHighlighted ? '#34d399' : isDark ? '#94a3b8' : '#64748b'}
                                    >
                                        {edge.label}
                                    </text>
                                </g>
                            </g>
                        )
                    })}

                    {/* Node circles */}
                    {(block.nodes || []).map((node) => {
                        const pos = nodePositions[node.id]
                        if (!pos) return null

                        const conf = TYPE_CONFIG[node.type] || TYPE_CONFIG.Assure
                        const isSelected = selectedNode?.id === node.id
                        const isHovered = hoveredNodeId === node.id
                        const isConnected = connectedNodeIds.has(node.id)
                        const isDimmed =
                            (hoveredNodeId && !isConnected) ||
                            (activeTypeFilter !== 'all' && node.type !== activeTypeFilter)

                        const IconComponent = conf.icon

                        return (
                            <g
                                key={node.id}
                                transform={`translate(${pos.x}, ${pos.y})`}
                                onMouseEnter={() => setHoveredNodeId(node.id)}
                                onMouseLeave={() => setHoveredNodeId(null)}
                                onClick={() => setSelectedNode(node)}
                                className="cursor-pointer transition-transform duration-200"
                                opacity={isDimmed ? 0.2 : 1}
                            >
                                {/* Pulsating glow on hover / selection */}
                                {(isHovered || isSelected) && (
                                    <circle
                                        r="28"
                                        fill={conf.color}
                                        opacity="0.25"
                                        className="animate-ping"
                                    />
                                )}

                                {/* Outer circle ring */}
                                <circle
                                    r={isSelected ? 24 : 20}
                                    fill={isDark ? conf.bgDark : conf.bgLight}
                                    stroke={isSelected || isHovered ? conf.color : conf.stroke}
                                    strokeWidth={isSelected ? 3 : 2}
                                    className="transition-all duration-200"
                                />

                                {/* Node Icon placeholder in center */}
                                <circle r="12" fill={conf.color} opacity="0.9" />

                                {/* Label below node */}
                                <text
                                    textAnchor="middle"
                                    y={34}
                                    fontSize="10"
                                    fontWeight="bold"
                                    fill={isDark ? '#f1f5f9' : '#0f172a'}
                                    className="select-none font-sans"
                                >
                                    {node.label.length > 18 ? node.label.slice(0, 16) + '...' : node.label}
                                </text>

                                {/* Type Badge */}
                                <text
                                    textAnchor="middle"
                                    y={45}
                                    fontSize="8"
                                    fontWeight="500"
                                    fill={conf.color}
                                    className="select-none font-mono uppercase"
                                >
                                    {conf.label}
                                </text>

                                {/* Value badge if present (e.g. -420 TND, ID: 1426) */}
                                {node.badge && (
                                    <g transform="translate(0, -22)">
                                        <rect
                                            x="-30"
                                            y="-8"
                                            width="60"
                                            height="14"
                                            rx="7"
                                            fill={node.badge.startsWith('-') ? '#be123c' : isDark ? '#1e293b' : '#f1f5f9'}
                                            stroke={node.badge.startsWith('-') ? '#f43f5e' : isDark ? '#475569' : '#cbd5e1'}
                                            strokeWidth="1"
                                        />
                                        <text
                                            textAnchor="middle"
                                            y="2.5"
                                            fontSize="8"
                                            fontWeight="bold"
                                            fill={node.badge.startsWith('-') ? '#ffffff' : isDark ? '#38bdf8' : '#0369a1'}
                                            className="font-mono"
                                        >
                                            {node.badge}
                                        </text>
                                    </g>
                                )}
                            </g>
                        )
                    })}
                </svg>

                {/* Node Inspection Drawer */}
                {selectedNode && (
                    <div
                        className={`absolute bottom-3 right-3 max-w-[280px] w-full p-3.5 rounded-xl border shadow-xl backdrop-blur-md animate-in fade-in zoom-in-95 duration-200 ${
                            isDark
                                ? 'bg-gray-900/95 border-emerald-500/30 text-gray-100 shadow-black/60'
                                : 'bg-white/95 border-emerald-600/30 text-gray-900 shadow-slate-300'
                        }`}
                    >
                        <div className="flex items-start justify-between gap-1 pb-2 border-b border-black/10 dark:border-white/10">
                            <div>
                                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-500">
                                    {TYPE_CONFIG[selectedNode.type]?.label || selectedNode.type}
                                </span>
                                <h4 className="text-xs font-bold truncate max-w-[200px]">{selectedNode.label}</h4>
                            </div>
                            <button
                                onClick={() => setSelectedNode(null)}
                                className="p-0.5 rounded hover:bg-black/10 dark:hover:bg-white/10 text-gray-400"
                            >
                                <X className="h-3.5 w-3.5" />
                            </button>
                        </div>

                        {/* Node Properties */}
                        <div className="mt-2.5 space-y-1.5 text-[11px] font-mono">
                            <div className="flex justify-between">
                                <span className="text-gray-500">ID Nœud:</span>
                                <span className="font-bold text-teal-500">{selectedNode.id}</span>
                            </div>
                            {selectedNode.properties &&
                                Object.entries(selectedNode.properties).map(([k, v]) => (
                                    <div key={k} className="flex justify-between gap-2">
                                        <span className="text-gray-500 truncate">{k}:</span>
                                        <span className="font-semibold truncate text-right text-emerald-400 dark:text-emerald-300">
                                            {String(v)}
                                        </span>
                                    </div>
                                ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Bottom Footer Legend */}
            <div
                className={`flex flex-wrap items-center justify-between px-4 py-2 text-[10px] font-mono border-t ${
                    isDark ? 'border-gray-800 bg-gray-950/40 text-gray-400' : 'border-gray-100 bg-slate-50 text-gray-500'
                }`}
            >
                <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-emerald-500" /> Assuré
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-amber-500" /> Bulletin de Soin
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-cyan-500" /> Contrat
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-blue-500" /> Compagnie
                    </span>
                </div>
                <span>Cliquez sur un nœud pour inspecter ses propriétés Neo4j</span>
            </div>
        </div>
    )
}
