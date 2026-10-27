'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import dynamic from 'next/dynamic'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from '../components/layout/Sidebar'
import Topbar from '../components/layout/Topbar'
import ChatWindow from '../components/chat/ChatWindow'
import AnimatedBackground from '../components/background/AnimatedBackground'
import OrbitLines from '../components/background/OrbitLines'
import HealioNebula from '../components/background/HealioNebula'
import ParticleField from '../components/background/ParticleField'
import MeshWave from '../components/background/MeshWave'
import { SessionItem, Message } from '../types'

// Dynamically import the Lottie animation to prevent Next.js SSR build errors
const HealioAnimation = dynamic(
    () => import('../components/ui/HealioAnimation'),
    { ssr: false }
)

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

function toSessionItem(raw: any): SessionItem {
    const msgCount = raw.message_count ?? raw.messages?.length ?? 0
    return {
        id: raw.session_id,
        title: raw.title || 'Nouvelle analyse',
        time: raw.updated_at
            ? new Date(raw.updated_at * 1000).toLocaleDateString()
            : "A l'instant",
        messages: (raw.messages || []).map((m: any) => ({
            id: String(m.id ?? `${raw.session_id}_${m.role}_${m.ts}`),
            role: m.role,
            content: m.content,
            cypherQuery: m.cypher || m.cypherQuery || '',
            genuiBlocks: m.genui_blocks || m.genuiBlocks || [],
            thinkingTime: m.thinkingTime,
            traceId: m.trace_id || m.traceId,
            executionPlan: m.execution_plan || m.executionPlan,
            latencyMs: m.latency_ms || m.latencyMs,
            hasStepper: m.hasStepper !== false,
            currentStep: 5,
            isLive: false,
            stepperSteps: m.stepper_steps || m.stepperSteps,
            stepperTotal: m.stepper_total || m.stepperTotal,
            timestamp: m.ts ? new Date(m.ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
        })),
    }
}

function questionTitle(text: string): string {
    const t = (text || '').trim().replace(/\s+/g, ' ')
    return t ? (t.length > 60 ? t.slice(0, 57) + '...' : t) : 'Nouvelle analyse'
}

function AppContent() {
    const [sessions, setSessions] = useState<SessionItem[]>([])
    const [activeSessionId, setActiveSessionId] = useState<string>('')
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [isTyping, setIsTyping] = useState(false)
    const [neo4jStatus, setNeo4jStatus] = useState<'connected' | 'idle' | 'querying'>('connected')
    const [bgStyle, setBgStyle] = useState<'clinical-light' | 'neon-matrix'>('clinical-light')
    const [showPreloader, setShowPreloader] = useState(true)
    const [activeAbortController, setActiveAbortController] = useState<AbortController | null>(null)
    const [sessionsLoaded, setSessionsLoaded] = useState(false)
    const [userName, setUserName] = useState('Admin')
    const [userEmail, setUserEmail] = useState('')
    const [odooUserId, setOdooUserId] = useState('')
    const odooUserIdRef = useRef('')



    // Read user info from URL query params (Odoo iframe mode)
    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const name = params.get('user_name')
        const email = params.get('user_email')
        const uid = params.get('odoo_user_id')
        if (name) setUserName(name)
        if (email) setUserEmail(email)
        if (uid) {
            setOdooUserId(uid)
            odooUserIdRef.current = uid
        }
    }, [])

    const loadSessions = useCallback(async () => {
        try {
            const headers: Record<string, string> = {}
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current
            const res = await fetch(`${API_BASE}/sessions/`, { headers })
            if (res.ok) {
                const data = await res.json()
                const items: SessionItem[] = data.map(toSessionItem)
                setSessions(prev => {
                    const merged = items.map((backend: SessionItem) => {
                        const local = prev.find(s => s.id === backend.id)
                        return local && local.messages.length > backend.messages.length
                            ? local
                            : backend
                    })
                    const localOnly = prev.filter(s => !items.find((b: SessionItem) => b.id === s.id))
                    return [...merged, ...localOnly]
                })
                setSessionsLoaded(true)
                const saved = sessionStorage.getItem('healia_active_session')
                if (saved && items.find(s => s.id === saved)) {
                    setActiveSessionId(saved)
                }
                // Ne pas auto-sélectionner une ancienne session → nouvelle conversation par défaut
            }
        } catch (e) {
            console.warn('Failed to load sessions:', e)
        } finally {
            setSessionsLoaded(true)
        }
    }, [])

    useEffect(() => { loadSessions() }, [loadSessions])

    // Restore session from URL query params (Odoo iframe mode)
    useEffect(() => {
        if (!sessionsLoaded) return
        const params = new URLSearchParams(window.location.search)
        const odooSessionId = params.get('session_id')
        if (odooSessionId) {
            setActiveSessionId(odooSessionId)
            sessionStorage.setItem('healia_active_session', odooSessionId)
            loadSessionDetail(odooSessionId)
        }
    }, [sessionsLoaded])

    const loadSessionDetail = useCallback(async (sessionId: string) => {
        try {
            const headers: Record<string, string> = {}
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current
            const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { headers })
            if (res.ok) {
                const data = await res.json()
                const item = toSessionItem(data)
                setSessions(prev => {
                    const exists = prev.find(s => s.id === sessionId)
                    if (exists) {
                        return prev.map(s => s.id === sessionId ? item : s)
                    }
                    return [item, ...prev]
                })
            }
        } catch (e) {
            console.warn('Failed to load session detail:', e)
        }
    }, [])

    const handleSelectSession = (sessionId: string) => {
        setActiveSessionId(sessionId)
        sessionStorage.setItem('healia_active_session', sessionId)
        loadSessionDetail(sessionId)
    }

    const generateLlmTitle = useCallback(async (sessionId: string, message: string) => {
        try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' }
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current
            const res = await fetch(`${API_BASE}/chat/title`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ message }),
            })
            if (res.ok) {
                const data = await res.json()
                const title = data.title
                if (title) {
                    setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title } : s))
                }
            }
        } catch (e) {
            console.warn('Failed to generate title:', e)
        }
    }, [])

    // Safety fallback to close intro preloader in case Lottie fails to fire onComplete 
    useEffect(() => {
        const timer = setTimeout(() => {
            setShowPreloader(false)
        }, 3000)
        return () => clearTimeout(timer)
    }, [])

    const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0] || null
    const activeMessages = activeSession?.messages || []
    const activeWebSocketRef = useRef<WebSocket | null>(null)

    const streamMessageViaWebSocket = (
        text: string,
        sessionId: string,
        targetSessionId: string,
        assistantMsgId: string,
        thinkingStartedAt: number
    ): Promise<boolean> => {
        return new Promise((resolve) => {
            const wsBase = API_BASE.replace(/^http/, 'ws')
            const wsUrl = `${wsBase}/ws/chat`
            let ws: WebSocket | null = null
            let completed = false

            try {
                ws = new WebSocket(wsUrl)
                activeWebSocketRef.current = ws
            } catch (err) {
                console.warn('WebSocket init failed, fallback to HTTP:', err)
                resolve(false)
                return
            }

            const timeout = setTimeout(() => {
                if (!completed) {
                    console.warn('WebSocket timed out, falling back to HTTP')
                    try { ws?.close() } catch {}
                    activeWebSocketRef.current = null
                    resolve(false)
                }
            }, 60000)

            ws.onopen = () => {
                try {
                    ws?.send(JSON.stringify({
                        message: text,
                        session_id: sessionId || undefined
                    }))
                } catch (e) {
                    console.warn('Failed to send WS payload:', e)
                    completed = true
                    clearTimeout(timeout)
                    resolve(false)
                }
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)
                    const eventType = data.type

                    if (eventType === 'start') {
                        const traceId = data.trace_id || ''
                        setSessions(prev => prev.map(s => {
                            if (s.id !== targetSessionId) return s
                            return {
                                ...s,
                                messages: s.messages.map(m => m.id === assistantMsgId ? { ...m, traceId } : m)
                            }
                        }))
                    } else if (eventType === 'step_start' || eventType === 'node_start') {
                        let stepIdx = typeof data.step_index === 'number' ? data.step_index : 0
                        const nodeName = data.node || ''
                        if (nodeName === 'intent_classifier') stepIdx = 0
                        else if (nodeName === 'schema_retriever') stepIdx = 1
                        else if (nodeName === 'cypher_generator') stepIdx = 2
                        else if (nodeName === 'cypher_validator') stepIdx = 3
                        else if (nodeName === 'graph_executor') stepIdx = 4
                        else if (nodeName === 'synthesizer') stepIdx = 4

                        setSessions(prev => prev.map(s => {
                            if (s.id !== targetSessionId) return s
                            return {
                                ...s,
                                messages: s.messages.map(m => m.id === assistantMsgId ? {
                                    ...m,
                                    currentStep: stepIdx,
                                    isLive: true,
                                } : m)
                            }
                        }))
                    } else if (eventType === 'cypher') {
                        const cypherQuery = data.cypher || ''
                        setSessions(prev => prev.map(s => {
                            if (s.id !== targetSessionId) return s
                            return {
                                ...s,
                                messages: s.messages.map(m => m.id === assistantMsgId ? { ...m, cypherQuery } : m)
                            }
                        }))
                    } else if (eventType === 'token') {
                        const chunk = data.token || ''
                        setSessions(prev => prev.map(s => {
                            if (s.id !== targetSessionId) return s
                            return {
                                ...s,
                                messages: s.messages.map(m => m.id === assistantMsgId ? {
                                    ...m,
                                    content: m.content + chunk,
                                    isLive: true,
                                } : m)
                            }
                        }))
                    } else if (eventType === 'final') {
                        completed = true
                        clearTimeout(timeout)
                        const finalAnswer = data.answer || ''
                        const cypherQuery = data.cypher || ''
                        const genuiBlocks = data.genui_blocks || []
                        const traceId = data.trace_id || ''
                        const returnedSessionId = data.session_id
                        const stepperSteps = data.stepper_steps || undefined
                        const stepperTotal = data.stepper_total || undefined
                        const latencyMs = typeof data.latency_ms === 'number' ? data.latency_ms : 18.4
                        const thinkingTime = typeof data.thinking_time === 'number'
                            ? data.thinking_time
                            : Math.max(1, Math.round((Date.now() - thinkingStartedAt) / 1000))

                        setSessions(prev => prev.map(s => {
                            if (s.id !== targetSessionId && s.id !== returnedSessionId) return s
                            return {
                                ...s,
                                id: returnedSessionId || s.id,
                                messages: s.messages.map(m => m.id === assistantMsgId ? {
                                    ...m,
                                    content: finalAnswer || m.content,
                                    cypherQuery: cypherQuery || m.cypherQuery,
                                    genuiBlocks,
                                    traceId,
                                    isLive: false,
                                    currentStep: 5,
                                    thinkingTime,
                                    latencyMs,
                                    stepperSteps,
                                    stepperTotal,
                                } : m)
                            }
                        }))

                        if (returnedSessionId && targetSessionId !== returnedSessionId) {
                            setActiveSessionId(returnedSessionId)
                            sessionStorage.setItem('healia_active_session', returnedSessionId)
                        }

                        setIsTyping(false)
                        setNeo4jStatus('connected')
                        activeWebSocketRef.current = null
                        try { ws?.close() } catch {}
                        resolve(true)
                    } else if (eventType === 'error') {
                        console.warn('WebSocket error event:', data.error)
                        completed = true
                        clearTimeout(timeout)
                        activeWebSocketRef.current = null
                        try { ws?.close() } catch {}
                        resolve(false)
                    }
                } catch (e) {
                    console.error('Error parsing WS message:', e)
                }
            }

            ws.onerror = (err) => {
                console.warn('WebSocket error, falling back to HTTP:', err)
                if (!completed) {
                    completed = true
                    clearTimeout(timeout)
                    activeWebSocketRef.current = null
                    resolve(false)
                }
            }

            ws.onclose = () => {
                if (!completed) {
                    completed = true
                    clearTimeout(timeout)
                    activeWebSocketRef.current = null
                    resolve(false)
                }
            }
        })
    }

    const handleCancel = async () => {
        if (activeWebSocketRef.current) {
            try {
                activeWebSocketRef.current.close()
            } catch {}
            activeWebSocketRef.current = null
        }

        if (activeAbortController) {
            activeAbortController.abort()
            setActiveAbortController(null)
        }
        setIsTyping(false)
        setNeo4jStatus('connected')

        setSessions(prev => prev.map(s => {
            if (s.id !== activeSessionId) return s
            return {
                ...s,
                messages: s.messages.map(m => m.isLive ? { ...m, isLive: false } : m)
            }
        }))

        try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' }
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current
            await fetch(`${API_BASE}/sessions/${activeSessionId}/cancel`, {
                method: 'POST',
                headers,
            })
        } catch (error) {
            console.error("Failed to notify backend of cancellation:", error)
        }
    }

    const handleEditUserMessage = async (messageId: string, newText: string) => {
        const session = sessions.find(s => s.id === activeSessionId)
        if (!session) return

        const messageIndex = session.messages.findIndex(m => m.id === messageId)
        if (messageIndex === -1) return

        // 1. Truncate the messages before the edited user message
        const messagesBefore = session.messages.slice(0, messageIndex)

        // 2. Format history for backend
        const backendMessages = messagesBefore.map(m => ({
            role: m.role,
            content: m.content,
            ts: 0.0
        }))

        // 3. Send update session messages call to backend
        try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' }
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current
            await fetch(`${API_BASE}/sessions/${activeSessionId}/messages`, {
                method: 'PUT',
                headers,
                body: JSON.stringify(backendMessages)
            })
        } catch (error) {
            console.error("Failed to update backend messages:", error)
        }

        // 4. Update frontend session state locally
        const editedUserMsg: Message = {
            ...session.messages[messageIndex],
            content: newText,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
        const updatedMessages = [...messagesBefore, editedUserMsg]

        setSessions(prev => prev.map(s => {
            if (s.id === activeSessionId) {
                return {
                    ...s,
                    time: "A l'instant",
                    messages: updatedMessages
                }
            }
            return s
        }))

        // 5. Run the new query
        setIsTyping(true)
        setNeo4jStatus('querying')

        if (activeAbortController) {
            activeAbortController.abort()
        }
        const controller = new AbortController()
        setActiveAbortController(controller)



        const assistantMsgId = `msg_assist_${Date.now()}`
        const initialAssistantMsg: Message = {
            id: assistantMsgId,
            role: 'assistant',
            content: '',
            cypherQuery: '',
            genuiBlocks: [],
            thinkingTime: 0,
            hasStepper: true,
            currentStep: 0,
            isLive: true,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }

        setSessions(prev => prev.map(s => {
            if (s.id === activeSessionId) {
                return {
                    ...s,
                    messages: [...updatedMessages, initialAssistantMsg]
                }
            }
            return s
        }))

        // Priority 1: WebSocket streaming
        const streamedOk = await streamMessageViaWebSocket(
            newText,
            activeSessionId || '',
            activeSessionId,
            assistantMsgId,
            Date.now()
        )

        if (streamedOk) {
            return
        }

        // Priority 2: HTTP POST /chat fallback
        let responseText = ""
        let cypherScript = ""
        let genuiBlocks: any[] = []

        try {
            const apiBaseUrl = API_BASE
            const headers: Record<string, string> = { 'Content-Type': 'application/json' }
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current
            const response = await fetch(`${apiBaseUrl}/chat`, {
                method: 'POST',
                headers,
                signal: controller.signal,
                body: JSON.stringify({
                    message: newText,
                    session_id: activeSessionId
                })
            })

            if (response.ok) {
                const data = await response.json()
                responseText = data.answer || "Aucune réponse reçue."
                cypherScript = data.cypher || ""
                genuiBlocks = data.genui_blocks || []
            } else {
                const errorData = await response.json().catch(() => ({}))
                responseText = `Erreur ${response.status}: ${errorData.error || response.statusText}`
            }
        } catch (error: any) {
            if (error.name === 'AbortError') {
                console.log("Edit query execution aborted by user")
                return
            }
            console.error("FastAPI Connection failed:", error)
            responseText = `Impossible de joindre le serveur : ${error.message}. Vérifiez que le serveur FastAPI est lancé.`
        } finally {
            setActiveAbortController(null)
        }

        setSessions(prev => prev.map(s => {
            if (s.id === activeSessionId) {
                return {
                    ...s,
                    messages: s.messages.map(m => m.id === assistantMsgId ? {
                        ...m,
                        content: responseText,
                        cypherQuery: cypherScript,
                        genuiBlocks,
                        isLive: false,
                        currentStep: 5
                    } : m)
                }
            }
            return s
        }))

        setIsTyping(false)
        setNeo4jStatus('connected')
    }

    const handleSend = async (text: string) => {
        const thinkingStartedAt = Date.now()
        const currentId = activeSessionId || `s_${Date.now()}`
        const isNewSession = currentId.startsWith('s_')
        const sessionId = (!isNewSession ? activeSessionId : undefined)

        if (!activeSessionId) {
            setActiveSessionId(currentId)
            setSessions(prev => [...prev, {
                id: currentId,
                title: questionTitle(text),
                time: "A l'instant",
                messages: [],
            }])
        }

        const newUserMsg: Message = {
            id: `msg_user_${Date.now()}`,
            role: 'user',
            content: text,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }

        const assistantMsgId = `msg_assist_${Date.now()}`
        const initialAssistantMsg: Message = {
            id: assistantMsgId,
            role: 'assistant',
            content: '',
            cypherQuery: '',
            genuiBlocks: [],
            thinkingTime: 0,
            hasStepper: true,
            currentStep: 0,
            isLive: true,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }

        // Immediately add user message and live assistant placeholder message
        setSessions(prev => prev.map(s => {
            if (s.id === currentId) {
                return {
                    ...s,
                    time: "A l'instant",
                    messages: [...s.messages, newUserMsg, initialAssistantMsg]
                }
            }
            return s
        }))

        setIsTyping(true)
        setNeo4jStatus('querying')

        if (activeAbortController) {
            activeAbortController.abort()
        }
        const controller = new AbortController()
        setActiveAbortController(controller)

        // ── 1. Priority: WebSocket real-time event streaming (Reasoning Stepper) ──
        const streamedOk = await streamMessageViaWebSocket(
            text,
            sessionId || '',
            currentId,
            assistantMsgId,
            thinkingStartedAt
        )

        if (streamedOk) {
            if (isNewSession) {
                generateLlmTitle(currentId, text)
            }
            return
        }

        // ── 2. Fallback: HTTP POST /chat in case WebSocket is unavailable ──
        let responseText = ""
        let cypherScript = ""
        let genuiBlocks: any[] = []
        let targetSessionId = currentId
        let returnedTraceId = ""
        let returnedLatencyMs: number | undefined = undefined
        let returnedExecutionPlan = ""

        try {
            const apiBaseUrl = API_BASE
            const headers: Record<string, string> = { 'Content-Type': 'application/json' }
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current

            const response = await fetch(`${apiBaseUrl}/chat`, {
                method: 'POST',
                headers,
                signal: controller.signal,
                body: JSON.stringify({
                    message: text,
                    ...(sessionId ? { session_id: sessionId } : {}),
                })
            })

            if (response.ok) {
                const data = await response.json()
                responseText = data.answer || "Aucune réponse reçue."
                cypherScript = data.cypher || ""
                genuiBlocks = data.genui_blocks || []
                returnedTraceId = data.trace_id || ""
                returnedLatencyMs = data.metrics?.neo4j_exec_ms
                returnedExecutionPlan = data.execution_plan || ""
                const returnedSessionId = data.session_id
                if (isNewSession && returnedSessionId) {
                    setSessions(prev => prev.map(s =>
                        s.id === currentId
                            ? { ...s, id: returnedSessionId, time: "A l'instant" }
                            : s
                    ))
                    setActiveSessionId(returnedSessionId)
                    sessionStorage.setItem('healia_active_session', returnedSessionId)
                    targetSessionId = returnedSessionId
                    loadSessionDetail(returnedSessionId)
                    if (typeof window !== 'undefined' && window.parent !== window) {
                        window.parent.postMessage(
                            { type: 'healia_session_id', session_id: returnedSessionId },
                            '*'
                        )
                    }
                }
            } else {
                const errorData = await response.json().catch(() => ({}))
                responseText = `Erreur ${response.status}: ${errorData.error || response.statusText}`
            }
        } catch (error: any) {
            if (error.name === 'AbortError') {
                console.log("Query execution aborted by user")
                return
            }
            console.error("FastAPI Connection failed:", error)
            responseText = `Impossible de joindre le serveur : ${error.message}. Vérifiez que le serveur FastAPI est lancé.`
        } finally {
            setActiveAbortController(null)
        }

        const thinkingTime = Math.floor((Date.now() - thinkingStartedAt) / 1000)

        setSessions(prev => prev.map(s => {
            if (s.id === targetSessionId) {
                return {
                    ...s,
                    messages: s.messages.map(m => m.id === assistantMsgId ? {
                        ...m,
                        content: responseText,
                        cypherQuery: cypherScript,
                        genuiBlocks,
                        thinkingTime,
                        traceId: returnedTraceId,
                        latencyMs: returnedLatencyMs,
                        executionPlan: returnedExecutionPlan,
                        hasStepper: true,
                        currentStep: 5,
                        isLive: false,
                    } : m)
                }
            }
            return s
        }))

        setIsTyping(false)
        setNeo4jStatus('connected')
    }

    const handleAttachFile = (fileName: string) => {
        const attachMsg: Message = {
            id: `msg_sys_attach_${Date.now()}`,
            role: 'assistant',
            content: `Fichier "${fileName}" importé dans le pipeline. Vous pouvez maintenant me poser des questions sur ces données par rapport à vos enregistrements Neo4j.`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }

        setSessions(prev => prev.map(s => {
            if (s.id === activeSessionId) {
                return {
                    ...s,
                    messages: [...s.messages, attachMsg]
                }
            }
            return s
        }))
    }

    const handleRenameSession = async (sessionId: string, newTitle: string) => {
        setSessions(prev => prev.map(s =>
            s.id === sessionId ? { ...s, title: newTitle } : s
        ))
        try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' }
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current
            await fetch(`${API_BASE}/sessions/${sessionId}/title`, {
                method: 'PUT',
                headers,
                body: JSON.stringify({ title: newTitle }),
            })
        } catch (e) {
            console.warn('Failed to rename session:', e)
        }
    }

    const handleDeleteSession = async (sessionId: string) => {
        try {
            const headers: Record<string, string> = {}
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current
            const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
                method: 'DELETE',
                headers,
            })
            if (res.ok) {
                setSessions(prev => {
                    const filtered = prev.filter(s => s.id !== sessionId)
                    if (activeSessionId === sessionId) {
                        const next = filtered[0] || null
                        setActiveSessionId(next?.id || '')
                        if (next) sessionStorage.setItem('healia_active_session', next.id)
                        else sessionStorage.removeItem('healia_active_session')
                    }
                    return filtered
                })
            }
        } catch (e) {
            console.warn('Failed to delete session:', e)
        }
    }

    const handleDeleteMessage = async (messageId: string) => {
        const session = sessions.find(s => s.id === activeSessionId)
        if (!session) return
        const msgIndex = session.messages.findIndex(m => m.id === messageId)
        if (msgIndex === -1) return

        const remainingMessages = session.messages.slice(0, msgIndex)
        const backendMessages = remainingMessages.map(m => ({
            role: m.role,
            content: m.content,
            ts: 0.0,
        }))

        setSessions(prev => prev.map(s =>
            s.id === activeSessionId
                ? { ...s, messages: remainingMessages }
                : s
        ))

        try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' }
            if (odooUserIdRef.current) headers['X-Odoo-User'] = odooUserIdRef.current
            await fetch(`${API_BASE}/sessions/${activeSessionId}/messages`, {
                method: 'PUT',
                headers,
                body: JSON.stringify(backendMessages),
            })
        } catch (e) {
            console.warn('Failed to delete message:', e)
        }
    }

    const handleNewChat = () => {
        const newSessionId = `s_${Date.now()}`
        const newSession: SessionItem = {
            id: newSessionId,
            title: 'Nouvelle analyse',
            time: "A l'instant",
            messages: []
        }

        setSessions(prev => [newSession, ...prev])
        setActiveSessionId(newSessionId)
        sessionStorage.removeItem('healia_active_session')
    }

    const isDark = bgStyle !== 'clinical-light'

    return (
        <div className={`relative flex h-screen w-screen overflow-hidden font-sans select-none transition-colors duration-1000 ${isDark ? 'dark text-gray-100' : 'text-gray-700'
            }`}>
            {/* ── App Launch Preloader ── */}
            <AnimatePresence>
                {showPreloader && (
                    <motion.div
                        initial={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.5, ease: 'easeInOut' }}
                        className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white"
                    >
                        <div className="w-[300px] sm:w-[450px] h-[300px] sm:h-[450px] relative flex items-center justify-center">
                            <HealioAnimation
                                loop={true}
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Background Visualization Layer ── */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <AnimatedBackground bgStyle={bgStyle} />
                <OrbitLines bgStyle={bgStyle} />
                <HealioNebula bgStyle={bgStyle} />
                <ParticleField bgStyle={bgStyle} />
                <MeshWave bgStyle={bgStyle} />
            </div>

            {/* ── Sliding Drawers ── */}
            <AnimatePresence>
                {sidebarOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 0.4 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setSidebarOpen(false)}
                            className="absolute inset-0 z-40 bg-black"
                        />

                        <motion.div
                            initial={{ x: '-100%' }}
                            animate={{ x: 0 }}
                            exit={{ x: '-100%' }}
                            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                            className="absolute left-0 top-0 bottom-0 z-50"
                        >
                            <Sidebar
                                sessions={sessions}
                                activeSessionId={activeSessionId}
                                onSelectSession={handleSelectSession}
                                onNewChat={handleNewChat}
                                onCloseSidebar={() => setSidebarOpen(false)}
                                onRenameSession={handleRenameSession}
                                onDeleteSession={handleDeleteSession}
                                bgStyle={bgStyle}
                                userName={userName}
                                userEmail={userEmail}
                            />
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* ── Foreground Interactive UI Container ── */}
            <div className="relative z-10 flex flex-1 flex-col h-full overflow-hidden">
                <Topbar
                    onOpenSidebar={() => setSidebarOpen(true)}
                    neo4jStatus={neo4jStatus}
                    bgStyle={bgStyle}
                    onChangeBgStyle={setBgStyle}
                    sessionTitle={activeSession?.title}
                    hasMessages={activeMessages.length > 0}
                />

                <div className="flex-1 overflow-hidden">
                    <ChatWindow
                        messages={activeMessages}
                        onSend={handleSend}
                        onAttachFile={handleAttachFile}
                        isTyping={isTyping}
                        bgStyle={bgStyle}
                        onCancel={handleCancel}
                        onEditUserMessage={handleEditUserMessage}
                        onDeleteMessage={handleDeleteMessage}
                    />
                </div>
            </div>
        </div>
    )
}

function AppContentWrapper() {
    const [mounted, setMounted] = useState(false)
    useEffect(() => { setMounted(true) }, [])
    if (!mounted) {
        return (
            <div className="flex h-screen w-screen items-center justify-center">
                <div className="w-[300px] h-[300px] relative flex items-center justify-center">
                    <HealioAnimation loop={true} />
                </div>
            </div>
        )
    }
    return <AppContent />
}

export default function App() {
    return <AppContentWrapper />
}
