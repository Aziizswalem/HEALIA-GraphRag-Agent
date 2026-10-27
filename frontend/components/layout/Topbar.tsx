'use client'

import { Menu } from 'lucide-react'

type Props = {
    onOpenSidebar?: () => void
    neo4jStatus: 'connected' | 'idle' | 'querying'
    bgStyle: 'clinical-light' | 'neon-matrix'
    onChangeBgStyle: (style: 'clinical-light' | 'neon-matrix') => void
    sessionTitle?: string | null
    hasMessages?: boolean
}

export default function Topbar({
    onOpenSidebar,
    neo4jStatus,
    bgStyle,
    onChangeBgStyle,
    sessionTitle,
    hasMessages
}: Props) {
    const isDark = bgStyle !== 'clinical-light'

    return (
        <div className={`relative z-20 flex items-center justify-between px-4 md:px-6 py-3 bg-transparent transition-all duration-700 ${isDark ? 'text-white' : 'text-gray-800'
            }`}>
            <div className="flex items-center gap-3">
                {onOpenSidebar && (
                    <button
                        onClick={onOpenSidebar}
                        className={`p-2 rounded-lg border shadow-sm transition-all hover:scale-105 active:scale-95 ${isDark
                            ? 'bg-black/40 hover:bg-black/60 border-white/10 text-gray-300'
                            : 'bg-white/70 hover:bg-white border-black/5 text-gray-500'
                            }`}
                        title="Menu"
                    >
                        <Menu className="h-4.5 w-4.5" />
                    </button>
                )}
                <h1 className={`text-base font-bold leading-none tracking-tight truncate max-w-[240px] ${isDark ? 'text-healia-teal' : 'text-healia-dark'
                    }`}>
                    {hasMessages && sessionTitle ? sessionTitle : 'Healia'}
                </h1>
            </div>

            <div className="flex items-center gap-2">
                <div className={`flex items-center rounded-lg p-0.5 border shadow-sm ${isDark ? 'bg-white/5 border-white/10' : 'bg-gray-100/80 border-black/5'
                    }`}>
                    <button
                        onClick={() => onChangeBgStyle('clinical-light')}
                        className={`px-2 py-1 text-[10px] uppercase font-bold tracking-wider rounded-md transition-all ${bgStyle === 'clinical-light'
                            ? 'bg-white text-healia-teal shadow-sm'
                            : isDark ? 'text-gray-400 hover:text-white' : 'text-gray-400 hover:text-gray-700'
                            }`}>
                        Clair
                    </button>
                    <button
                        onClick={() => onChangeBgStyle('neon-matrix')}
                        className={`px-2 py-1 text-[10px] uppercase font-bold tracking-wider rounded-md transition-all ${bgStyle === 'neon-matrix'
                            ? 'bg-healia-green text-white shadow-md'
                            : isDark ? 'text-gray-400 hover:text-white' : 'text-gray-400 hover:text-gray-700'
                            }`}>
                        Sombre
                    </button>
                </div>

                <div className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[11px] shadow-sm backdrop-blur-xl ${neo4jStatus === 'connected'
                    ? isDark
                        ? 'border-healia-green/20 bg-healia-green/10 text-healia-green'
                        : 'border-healia-green/20 bg-healia-green/10 text-healia-dark'
                    : neo4jStatus === 'querying'
                        ? isDark
                            ? 'border-healia-teal/20 bg-healia-teal/10 text-healia-teal animate-pulse'
                            : 'border-healia-teal/20 bg-healia-teal/10 text-healia-teal animate-pulse'
                        : isDark
                            ? 'border-yellow-500/20 bg-yellow-500/10 text-yellow-300'
                            : 'border-yellow-100 bg-yellow-50/80 text-yellow-700'
                    }`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${neo4jStatus === 'connected'
                        ? 'bg-healia-green shadow-[0_0_6px_rgba(77,167,60,0.6)]'
                        : neo4jStatus === 'querying'
                            ? 'bg-healia-teal shadow-[0_0_8px_rgba(75,184,189,0.8)]'
                            : 'bg-yellow-500'
                        }`} />
                    <span className="font-semibold">{neo4jStatus === 'connected' ? 'Neo4j' : neo4jStatus === 'querying' ? 'Requête...' : 'Veille'}</span>
                </div>
            </div>
        </div>
    )
}
