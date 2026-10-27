'use client'

import React, { useRef, useEffect } from 'react'
import ChatInput from './ChatInput'
import ChatMessage from './ChatMessage'
import WelcomeCard from './WelcomeCard'
import TypingIndicator from './TypingIndicator'
import { Message } from '../../types'
import { Square } from 'lucide-react'

type Props = {
    messages: Message[]
    onSend: (message: string) => void | Promise<void>
    onAttachFile: (fileName: string) => void
    isTyping: boolean
    bgStyle?: 'clinical-light' | 'neon-matrix'
    onCancel?: () => void
    onEditUserMessage?: (messageId: string, newContent: string) => void | Promise<void>
    onDeleteMessage?: (messageId: string) => void
}

export default function ChatWindow({
    messages,
    onSend,
    onAttachFile,
    isTyping,
    bgStyle = 'clinical-light',
    onCancel,
    onEditUserMessage,
    onDeleteMessage
}: Props) {
    const scrollContainerRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight
        }
    }, [messages, isTyping])

    const isDark = bgStyle !== 'clinical-light'
    const hasMessages = messages.length > 0

    return (
        <div className="flex h-full w-full flex-col">
            {/* Scrollable messages */}
            <div
                ref={scrollContainerRef}
                className={`flex-1 scroll-smooth ${hasMessages ? 'overflow-y-auto px-4 md:px-6 pb-4' : 'overflow-hidden flex flex-col items-center justify-center px-4'
                    }`}
            >
                {!hasMessages ? (
                    <div className="w-full max-w-4xl flex flex-col items-center justify-center animate-fade-in duration-700">
                        <div className="mb-6 text-center select-none">
                            <p className={`mb-1 text-xs font-semibold tracking-wider uppercase transition-colors duration-700 ${isDark ? 'text-healia-green/60' : 'text-healia-dark/60'
                                }`}>
                                Bon retour
                            </p>
                            <h1 className={`text-2xl sm:text-3xl md:text-4xl font-black leading-none tracking-tight transition-colors duration-700 ${isDark ? 'text-emerald-50' : 'text-gray-800'
                                }`}>
                                Comment{' '}
                                <span className={isDark ? 'text-healia-green' : 'text-healia-teal'}>puis-je</span>{' '}
                                vous aider aujourd'hui ?
                            </h1>
                        </div>
                        <WelcomeCard onPrompt={onSend} bgStyle={bgStyle} />
                    </div>
                ) : (
                    <div className="w-full space-y-0 px-4 md:px-48">
                        {messages.map((msg) => (
                            <ChatMessage
                                key={msg.id}
                                id={msg.id}
                                role={msg.role}
                                content={msg.content}
                                cypherQuery={msg.cypherQuery}
                                thinkingTime={msg.thinkingTime}
                                genuiBlocks={msg.genuiBlocks}
                                traceId={msg.traceId}
                                executionPlan={msg.executionPlan}
                                latencyMs={msg.latencyMs}
                                hasStepper={msg.hasStepper !== false}
                                currentStep={msg.currentStep}
                                isLive={msg.isLive}
                                stepperSteps={msg.stepperSteps}
                                stepperTotal={msg.stepperTotal}
                                bgStyle={bgStyle}
                                onEdit={onEditUserMessage}
                                onDelete={onDeleteMessage!}
                            />
                        ))}
                        {isTyping && !messages.some((m) => m.isLive) && (
                            <div className="flex justify-start pl-11 py-3 w-full">
                                <TypingIndicator bgStyle={bgStyle} />
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Fixed input bar */}
            <div className="shrink-0 px-4 md:px-8 pb-4 md:pb-6 pt-2">
                <div className="w-full relative">
                    {isTyping && onCancel && (
                        <div className="absolute -top-12 left-1/2 -translate-x-1/2 z-20">
                            <button
                                onClick={onCancel}
                                className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-full border shadow-md hover:scale-105 active:scale-95 transition-all duration-300 ${isDark
                                    ? 'bg-gray-900 border-healia-green/30 text-healia-green hover:bg-gray-850 hover:border-healia-green'
                                    : 'bg-white border-healia-teal/50 text-healia-teal hover:bg-healia-teal/10 hover:border-healia-teal'
                                    }`}
                            >
                                <Square className="h-3 w-3 fill-current" />
                                Annuler
                            </button>
                        </div>
                    )}
                    <ChatInput onSend={onSend} onAttach={onAttachFile} disabled={isTyping} bgStyle={bgStyle} />
                </div>
            </div>
        </div>
    )
}
