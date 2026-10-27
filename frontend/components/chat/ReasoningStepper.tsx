'use client'

import React, { useState } from 'react'
import { CheckCircle2, ChevronDown, ChevronRight, Cpu, Database, Network, Search, ShieldCheck } from 'lucide-react'

export interface StepItem {
    id: string
    label: string
    detail?: string
    duration?: string
    status: 'completed' | 'running' | 'pending'
}

type Props = {
    isDark?: boolean
    currentStep?: number // 0 à 4 si en cours d'animation
    isLive?: boolean // true si en cours d'exécution
    compact?: boolean
    steps?: StepItem[]
    totalDuration?: string
}

export const ADHERENT_1426_STEPS: StepItem[] = [
    {
        id: '1',
        label: 'Analyse',
        detail: 'Détection raccourci déterministe & extraction ID 1426',
        duration: '6ms',
        status: 'completed',
    },
    {
        id: '2',
        label: 'Résolution entité',
        detail: 'Mapping direct du nœud :Assure(id: 1426)',
        duration: '4ms',
        status: 'completed',
    },
    {
        id: '3',
        label: 'Génération Cypher',
        detail: 'Sélection du template Cypher pré-indexé et optimisé',
        duration: '5ms',
        status: 'completed',
    },
    {
        id: '4',
        label: 'Validation syntaxique',
        detail: 'Vérification instantanée des clauses & filtres de sécurité',
        duration: '3ms',
        status: 'completed',
    },
    {
        id: '5',
        label: 'Exécution Neo4j',
        detail: 'Index Seek direct & assemblage GenUI multi-blocs',
        duration: '7ms',
        status: 'completed',
    },
]

export const RADIATION_SCENARIO_STEPS: StepItem[] = [
    {
        id: '1',
        label: 'Analyse',
        detail: 'Analyse sémantique & extraction des entités métier',
        duration: '0.6s',
        status: 'completed',
    },
    {
        id: '2',
        label: 'Extraction du schéma',
        detail: 'Mapping ontologique & sélection des labels Neo4j',
        duration: '1.8s',
        status: 'completed',
    },
    {
        id: '3',
        label: 'Génération Cypher',
        detail: 'Synthèse déterministe de la requête graphe',
        duration: '3.2s',
        status: 'completed',
    },
    {
        id: '4',
        label: 'Validation syntaxique',
        detail: 'Guardrails & contrôle des clauses d\'intégrité',
        duration: '1.4s',
        status: 'completed',
    },
    {
        id: '5',
        label: 'Exécution Neo4j',
        detail: 'Interrogation du cluster graphe & restitution GenUI',
        duration: '1.0s',
        status: 'completed',
    },
]

export const DEFAULT_REASONING_STEPS: StepItem[] = [
    {
        id: '1',
        label: 'Analyse',
        detail: 'Analyse sémantique & extraction des entités métier',
        duration: '14ms',
        status: 'completed',
    },
    {
        id: '2',
        label: 'Extraction du schéma',
        detail: 'Mapping ontologique & sélection des labels Neo4j',
        duration: '22ms',
        status: 'completed',
    },
    {
        id: '3',
        label: 'Génération Cypher',
        detail: 'Synthèse déterministe de la requête graphe',
        duration: '48ms',
        status: 'completed',
    },
    {
        id: '4',
        label: 'Validation syntaxique',
        detail: 'Guardrails & contrôle des clauses d\'intégrité',
        duration: '8ms',
        status: 'completed',
    },
    {
        id: '5',
        label: 'Exécution Neo4j',
        detail: 'Interrogation du cluster graphe & restitution GenUI',
        duration: '16ms',
        status: 'completed',
    },
]

export default function ReasoningStepper({
    isDark = false,
    currentStep = 5,
    isLive = false,
    compact = false,
    steps: customSteps,
    totalDuration,
}: Props) {
    const [isExpanded, setIsExpanded] = useState(!compact)

    const rawSteps = customSteps && customSteps.length > 0 ? customSteps : DEFAULT_REASONING_STEPS

    const steps = rawSteps.map((s, idx) => {
        if (!isLive) return { ...s, status: 'completed' as const }
        if (idx < currentStep) return { ...s, status: 'completed' as const }
        if (idx === currentStep) return { ...s, status: 'running' as const }
        return { ...s, status: 'pending' as const }
    })

    const headerDurationLabel = totalDuration || (
        customSteps === ADHERENT_1426_STEPS
            ? '25ms'
            : customSteps === RADIATION_SCENARIO_STEPS
            ? '8.0s'
            : '108ms'
    )

    const getIcon = (idx: number) => {
        switch (idx) {
            case 0:
                return <Search className="h-3.5 w-3.5" />
            case 1:
                return <Network className="h-3.5 w-3.5" />
            case 2:
                return <Cpu className="h-3.5 w-3.5" />
            case 3:
                return <ShieldCheck className="h-3.5 w-3.5" />
            case 4:
                return <Database className="h-3.5 w-3.5" />
            default:
                return <CheckCircle2 className="h-3.5 w-3.5" />
        }
    }

    return (
        <div
            className={`my-2.5 rounded-xl border transition-all ${
                isDark
                    ? 'border-emerald-500/20 bg-gray-950/70 shadow-lg shadow-black/40'
                    : 'border-emerald-600/25 bg-emerald-50/40 shadow-sm'
            }`}
        >
            {/* Header / Summary Bar */}
            <button
                type="button"
                onClick={() => setIsExpanded(!isExpanded)}
                className={`flex w-full items-center justify-between px-3.5 py-2 text-left text-xs font-semibold transition-colors ${
                    isDark ? 'text-emerald-400 hover:bg-emerald-500/10' : 'text-emerald-800 hover:bg-emerald-100/50'
                }`}
            >
                <div className="flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                        {isLive && (
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                        )}
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                    </span>
                    <span className="font-mono text-[11px] uppercase tracking-wider">
                        {isLive ? 'Raisonnement agentique en direct' : 'Fil d\'Ariane décisionnel (LangGraph)'}
                    </span>
                    <span
                        className={`rounded-md px-1.5 py-0.5 text-[10px] font-mono ${
                            isDark ? 'bg-emerald-500/20 text-emerald-300' : 'bg-emerald-200/60 text-emerald-900'
                        }`}
                    >
                        {isLive
                            ? `Étape ${Math.min(currentStep + 1, steps.length)}/${steps.length}`
                            : `${steps.length}/${steps.length} jalons validés · ${headerDurationLabel}`}
                    </span>
                </div>

                <div className="flex items-center gap-1 text-[11px] opacity-75">
                    <span>{isExpanded ? 'Masquer' : 'Détails'}</span>
                    {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                </div>
            </button>

            {/* Stepper horizontal */}
            {isExpanded && (
                <div className="border-t border-emerald-500/15 p-3">
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-5">
                        {steps.map((step, idx) => {
                            const isCompleted = step.status === 'completed'
                            const isRunning = step.status === 'running'

                            return (
                                <div
                                    key={step.id}
                                    className={`relative flex flex-col rounded-lg border p-2 transition-all ${
                                        isRunning
                                            ? isDark
                                                ? 'border-emerald-400 bg-emerald-950/40 text-emerald-200 ring-2 ring-emerald-500/30'
                                                : 'border-emerald-600 bg-emerald-100/80 text-emerald-950 ring-2 ring-emerald-500/20'
                                            : isCompleted
                                            ? isDark
                                                ? 'border-white/10 bg-black/40 text-gray-200'
                                                : 'border-emerald-200 bg-white/90 text-gray-800'
                                            : isDark
                                            ? 'border-white/5 bg-black/20 text-gray-500 opacity-60'
                                            : 'border-gray-200 bg-gray-50 text-gray-400 opacity-60'
                                    }`}
                                >
                                    <div className="flex items-center justify-between gap-1 mb-1">
                                        <div className="flex items-center gap-1.5 font-bold text-[11px]">
                                            <span
                                                className={`flex h-5 w-5 items-center justify-center rounded-md ${
                                                    isCompleted
                                                        ? 'bg-emerald-500 text-white'
                                                        : isRunning
                                                        ? 'animate-pulse bg-emerald-400 text-black'
                                                        : 'bg-gray-400/20 text-gray-400'
                                                }`}
                                            >
                                                {getIcon(idx)}
                                            </span>
                                            <span>{step.label}</span>
                                        </div>
                                        {step.duration && isCompleted && (
                                            <span className="font-mono text-[9px] text-emerald-500">
                                                {step.duration}
                                            </span>
                                        )}
                                    </div>

                                    <p className={`text-[10px] leading-tight ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                                        {step.detail}
                                    </p>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}
        </div>
    )
}
