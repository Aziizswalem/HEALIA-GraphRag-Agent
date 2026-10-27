'use client'

import { useState, useRef, useEffect } from 'react'
import { MessageSquarePlus, MessageSquare, X, MessageCircle, Pencil, Check, Trash2 } from 'lucide-react'
import { SessionItem } from '../../types'

type Props = {
    sessions: SessionItem[]
    activeSessionId: string
    onSelectSession: (id: string) => void
    onNewChat?: () => void
    onCloseSidebar?: () => void
    onRenameSession?: (id: string, title: string) => void
    onDeleteSession?: (id: string) => void
    bgStyle?: 'clinical-light' | 'neon-matrix'
    userName?: string
    userEmail?: string
}

export default function Sidebar({
    sessions,
    activeSessionId,
    onSelectSession,
    onNewChat,
    onCloseSidebar,
    onRenameSession,
    onDeleteSession,
    bgStyle = 'clinical-light',
    userName = 'Admin',
    userEmail = '',
}: Props) {
    const isDark = bgStyle !== 'clinical-light'
    const [editingId, setEditingId] = useState<string | null>(null)
    const [editValue, setEditValue] = useState('')
    const inputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        if (editingId && inputRef.current) {
            inputRef.current.focus()
            inputRef.current.select()
        }
    }, [editingId])

    const handleStartRename = (id: string, currentTitle: string) => {
        setEditingId(id)
        setEditValue(currentTitle)
    }

    const handleSaveRename = () => {
        if (editingId && editValue.trim()) {
            onRenameSession?.(editingId, editValue.trim())
        }
        setEditingId(null)
    }
    return (
        <div className={`relative z-30 flex h-full w-[260px] shrink-0 flex-col border-r transition-all duration-700 ${isDark
            ? 'bg-[#060a13]/85 backdrop-blur-2xl border-white/10 text-white shadow-[12px_0_30px_rgba(0,0,0,0.4)]'
            : 'border-black/5 bg-white/60 backdrop-blur-2xl text-gray-700'
            }`}>
            {onCloseSidebar && (
                <button
                    onClick={onCloseSidebar}
                    className={`absolute right-4 top-4 md:hidden p-1.5 rounded-full transition-all ${isDark
                        ? 'bg-white/5 hover:bg-white/10 text-gray-300'
                        : 'bg-black/5 hover:bg-black/10 text-gray-500'
                        }`}
                >
                    <X className="h-4 w-4" />
                </button>
            )}

            <div className="px-6 pt-7 pb-5">
                <div className="flex items-center gap-3">
                    <img
                        src="/healio.jpg"
                        className={`h-[42px] w-[42px] rounded-xl object-cover shadow-sm border transition-all ${isDark ? 'border-healia-teal/30' : 'border-healia-teal/50'
                            }`}
                        alt="healia logo"
                    />
                    <div>
                        <h1 className={`text-xl font-extrabold tracking-tight transition-colors ${isDark ? 'text-white' : 'text-gray-800'
                            }`}>Healia</h1>
                        <p className={`text-[10px] font-semibold tracking-wider uppercase leading-none mt-0.5 ${bgStyle === 'neon-matrix' ? 'text-healia-green' : 'text-healia-dark'
                            }`}>Assistant IA Assurance </p>
                    </div>
                </div>
            </div>

            <div className="px-4 pb-5">
                <button
                    onClick={() => {
                        onNewChat?.();
                        onCloseSidebar?.();
                    }}
                    className={`flex w-full items-center justify-center gap-2 rounded-2xl font-medium px-5 py-3 text-sm transition shadow-md active:scale-95 ${bgStyle === 'neon-matrix'
                            ? 'bg-gradient-to-r from-healia-green to-healia-dark text-white shadow-healia-green/20 hover:from-healia-green hover:to-healia-dark'
                            : isDark
                                ? 'bg-gradient-to-r from-healia-teal to-healia-dark text-white shadow-healia-teal/20 hover:from-healia-teal hover:to-healia-dark'
                                : 'bg-gradient-to-r from-healia-teal to-healia-dark text-white shadow-healia-teal/20 hover:shadow-healia-teal/60'
                        }`}
                >
                    <MessageSquarePlus className="h-4 w-4 shrink-0" />
                    Nouveau Chat
                </button>
            </div>

            <div className="flex-1 overflow-y-auto px-3">
                <p className={`mb-2 px-2 text-[10px] font-bold uppercase tracking-wider ${isDark ? 'text-gray-500' : 'text-gray-400'
                    }`}>
                    Conversations
                </p>

                <div className="space-y-1">
                    {sessions.map((item) => {
                        const isActive = item.id === activeSessionId
                        const isEditing = editingId === item.id
                        return (
                            <div
                                key={item.id}
                                className={`group flex items-start gap-2.5 rounded-xl px-3 py-2.5 cursor-pointer transition-all ${isActive
                                    ? isDark
                                        ? 'bg-white/10 shadow-sm border border-healia-teal/20 text-white'
                                        : 'bg-white shadow-sm border border-healia-teal text-gray-800'
                                    : isDark
                                        ? 'hover:bg-white/5 text-gray-400 hover:text-white'
                                        : 'hover:bg-white/40 text-gray-500'
                                    }`}
                            >
                                <MessageSquare
                                    className={`mt-0.5 h-4 w-4 shrink-0 ${isActive ? (bgStyle === 'neon-matrix' ? 'text-healia-green' : 'text-healia-teal') : 'text-gray-400'}`}
                                />
                                <div
                                    className="min-w-0 flex-1"
                                    onClick={() => {
                                        if (!isEditing) {
                                            onSelectSession(item.id);
                                            onCloseSidebar?.();
                                        }
                                    }}
                                >
                                    {isEditing ? (
                                        <div className="flex items-center gap-1">
                                            <input
                                                ref={inputRef}
                                                value={editValue}
                                                onChange={(e) => setEditValue(e.target.value)}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleSaveRename()
                                                    if (e.key === 'Escape') setEditingId(null)
                                                }}
                                                onBlur={handleSaveRename}
                                                className={`w-full text-xs font-semibold px-1.5 py-0.5 rounded border bg-transparent outline-none ${isDark
                                                    ? 'border-healia-teal/40 text-white'
                                                    : 'border-healia-teal text-gray-800'
                                                    }`}
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleSaveRename() }}
                                                className={`p-0.5 rounded ${isDark ? 'hover:bg-white/10 text-healia-green' : 'hover:bg-black/5 text-healia-teal'}`}
                                            >
                                                <Check className="h-3 w-3" />
                                            </button>
                                        </div>
                                    ) : (
                                        <>
                                            <p className={`text-xs font-semibold truncate ${isActive
                                                ? 'text-white'
                                                : isDark
                                                    ? 'text-gray-300'
                                                    : 'text-gray-600'
                                                }`}>
                                                {item.title}
                                            </p>
                                            <p className={`mt-0.5 text-[9px] font-medium ${isDark ? 'text-gray-500' : 'text-black/25'
                                                }`}>{item.time}</p>
                                        </>
                                    )}
                                </div>
                                {!isEditing && (
                                    <>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onDeleteSession?.(item.id) }}
                                            className={`opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded mt-0.5 ${isDark
                                                ? 'hover:bg-white/10 text-red-400 hover:text-red-300'
                                                : 'hover:bg-black/5 text-red-400 hover:text-red-600'
                                                }`}
                                            title="Supprimer"
                                        >
                                            <Trash2 className="h-3 w-3" />
                                        </button>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); handleStartRename(item.id, item.title) }}
                                            className={`opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded mt-0.5 ${isDark
                                                ? 'hover:bg-white/10 text-gray-400 hover:text-white'
                                                : 'hover:bg-black/5 text-gray-400 hover:text-gray-700'
                                                }`}
                                            title="Renommer"
                                        >
                                            <Pencil className="h-3 w-3" />
                                        </button>
                                    </>
                                )}
                            </div>
                        )
                    })}
                    {sessions.length === 0 && (
                        <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
                            <MessageCircle className={`h-8 w-8 ${isDark ? 'text-gray-600' : 'text-black/15'}`} />
                            <p className={`text-xs font-medium ${isDark ? 'text-gray-500' : 'text-black/30'}`}>
                                Aucune conversation
                            </p>
                            <p className={`text-[10px] leading-relaxed ${isDark ? 'text-gray-600' : 'text-black/20'}`}>
                                Posez une question pour démarrer
                            </p>
                        </div>
                    )}
                </div>
            </div>

            <div className="px-3 pb-4">
                <div className={`flex items-center justify-between rounded-xl px-3 py-2 transition-all ${isDark ? 'hover:bg-white/5' : 'hover:bg-white/40'
                    }`}>
                    <div className="flex items-center gap-2.5">
                        <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-extrabold shadow-sm ${isDark ? 'bg-healia-dark/30 text-healia-teal' : 'bg-healia-teal/30 text-healia-dark'
                            }`}>
                            {userName.split(/\s+/).map(w => w[0]).join('').substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <p className="text-xs font-bold leading-tight">{userName}</p>
                            {userEmail && (
                                <p className={`text-[9px] font-medium ${isDark ? 'text-gray-500' : 'text-black/37'
                                    }`}>{userEmail}</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}