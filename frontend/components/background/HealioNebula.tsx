'use client'

import { motion } from 'framer-motion'

export default function HealioNebula({ bgStyle = 'clinical-light' }: { bgStyle?: 'clinical-light' | 'neon-matrix' }) {
    const isDark = bgStyle !== 'clinical-light'
    return (
        <>
            <motion.div
                animate={{
                    scale: [1, 1.08, 1],
                    opacity: isDark ? [0.08, 0.18, 0.08] : [0.25, 0.45, 0.25],
                }}
                transition={{
                    duration: 12,
                    repeat: Infinity,
                    ease: 'easeInOut',
                }}
                className={`absolute left-1/2 top-1/2 h-[700px] w-[700px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-3xl transition-all duration-1000 ${isDark ? 'bg-healia-green/10' : 'bg-healia-teal/30'
                    }`}
            />

            <motion.div
                animate={{
                    scale: [1, 1.12, 1],
                    opacity: isDark ? [0.05, 0.12, 0.05] : [0.15, 0.3, 0.15],
                }}
                transition={{
                    duration: 16,
                    repeat: Infinity,
                    ease: 'easeInOut',
                }}
                className={`absolute left-1/2 top-1/2 h-[950px] w-[950px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-3xl transition-all duration-1000 ${isDark ? 'bg-healia-dark/5' : 'bg-healia-teal/20'
                    }`}
            />
        </>
    )
}