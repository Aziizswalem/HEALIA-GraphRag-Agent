'use client'

import { motion } from 'framer-motion'

export default function OrbitLines({ bgStyle = 'clinical-light' }: { bgStyle?: 'clinical-light' | 'neon-matrix' }) {
    const isDark = bgStyle !== 'clinical-light'

    return (
        <>
            <motion.div
                animate={{ rotate: 360 }}
                transition={{
                    duration: 120,
                    repeat: Infinity,
                    ease: 'linear',
                }}
                className={`absolute left-1/2 top-1/2 h-[900px] w-[900px] -translate-x-1/2 -translate-y-1/2 rounded-full border transition-colors duration-1000 ${isDark ? 'border-healia-green/10' : 'border-healia-teal/20'
                    }`}
            />

            <motion.div
                animate={{ rotate: -360 }}
                transition={{
                    duration: 160,
                    repeat: Infinity,
                    ease: 'linear',
                }}
                className={`absolute left-1/2 top-1/2 h-[650px] w-[650px] -translate-x-1/2 -translate-y-1/2 rounded-full border transition-colors duration-1000 ${isDark ? 'border-healia-dark/10' : 'border-healia-teal/20'
                    }`}
            />
        </>
    )
}