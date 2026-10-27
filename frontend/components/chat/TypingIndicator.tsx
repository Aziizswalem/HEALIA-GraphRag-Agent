'use client'

import React, { useState, useEffect, useRef } from 'react'
import ReasoningStepper from './ReasoningStepper'

type Props = {
    bgStyle?: 'clinical-light' | 'neon-matrix'
}

export default function TypingIndicator({ bgStyle = 'clinical-light' }: Props) {
    const startTime = useRef(Date.now())
    const [elapsed, setElapsed] = useState(0)
    const [activeStep, setActiveStep] = useState(0)
    const isDark = bgStyle !== 'clinical-light'

    useEffect(() => {
        const id = setInterval(() => {
            const sec = Math.floor((Date.now() - startTime.current) / 1000)
            setElapsed(sec)
            // Évolution progressive des étapes de raisonnement
            setActiveStep((prev) => (prev < 4 ? prev + 1 : 4))
        }, 350)
        return () => clearInterval(id)
    }, [])

    const fmt = (s: number) => {
        const m = Math.floor(s / 60)
        const sec = s % 60
        return m > 0 ? `${m}m ${sec}s` : `${sec}s`
    }

    return (
        <div className="w-full max-w-3xl space-y-2 animate-fade-in">
            {/* Fil d'Ariane de raisonnement en direct (Figure 2.5) */}
            <ReasoningStepper
                isDark={isDark}
                currentStep={activeStep}
                isLive={true}
                compact={false}
            />

            {/* Bulle d'attente synthétique */}
            <div className="flex items-center gap-2 bg-black/5 dark:bg-white/5 px-4 py-2.5 rounded-2xl w-fit">
                <span className="h-2 w-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="h-2 w-2 bg-teal-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="h-2 w-2 bg-emerald-400 rounded-full animate-bounce" />
                <span className="text-xs font-mono font-medium text-black/60 dark:text-white/60 ml-1">
                    Exécution agentique en cours · {fmt(elapsed)}
                </span>
            </div>
        </div>
    )
}