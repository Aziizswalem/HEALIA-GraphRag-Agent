'use client'

import React, { useState, useRef } from 'react'
import { Send, Paperclip } from 'lucide-react'

type Props = {
    onSend: (text: string) => void
    onAttach?: (fileName: string) => void
    disabled?: boolean
    bgStyle?: 'clinical-light' | 'neon-matrix'
}

export default function ChatInput({ onSend, onAttach, disabled, bgStyle = 'clinical-light' }: Props) {
    const [text, setText] = useState('')
    const fileInputRef = useRef<HTMLInputElement>(null)
    const isDark = bgStyle !== 'clinical-light'

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (!text.trim() || disabled) return
        onSend(text)
        setText('')
    }

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file && onAttach) {
            onAttach(file.name)
        }
    }

    return (
        <form onSubmit={handleSubmit} className="relative flex items-center w-full">
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden"
            />

            <div className={`flex w-full items-center rounded-2xl border p-1 opacity-95 hover:opacity-100 focus-within:shadow-md backdrop-blur-xl transition-all duration-300 ${isDark
                    ? 'border-white/10 bg-black/60 shadow-[0_4px_24px_rgba(0,0,0,0.5)] focus-within:border-healia-green/40'
                    : 'border-slate-200 bg-white/75 shadow-sm focus-within:border-healia-teal focus-within:bg-white'
                }`}>
                <button
                    type="button"
                    disabled={disabled}
                    onClick={() => fileInputRef.current?.click()}
                    className={`p-2.5 rounded-xl transition hover:scale-105 ${isDark ? 'text-gray-400 hover:text-white hover:bg-white/5' : 'text-gray-400 hover:text-healia-teal hover:bg-slate-50'
                        }`}
                    title="Importer CSV/Excel"
                >
                    <Paperclip className="h-4.5 w-4.5" />
                </button>

                <input
                    type="text"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    disabled={disabled}
                    placeholder="Posez une question sur les données médicales..."
                    className={`flex-1 text-xs outline-none bg-transparent px-3 py-1.5 font-medium min-w-0 ${isDark ? 'text-white placeholder-gray-500' : 'text-gray-800 placeholder-gray-400'
                        }`}
                />

                <button
                    type="submit"
                    disabled={disabled || !text.trim()}
                    className={`p-2.5 rounded-xl text-white transition active:scale-95 disabled:opacity-35 ${bgStyle === 'neon-matrix'
                            ? 'bg-gradient-to-r from-healia-green to-healia-dark font-semibold shadow-sm'
                            : 'bg-gradient-to-r from-healia-teal to-healia-dark font-semibold shadow-sm shadow-healia-teal/10'
                        }`}
                >
                    <Send className="h-4 w-4" />
                </button>
            </div>
        </form>
    )
}