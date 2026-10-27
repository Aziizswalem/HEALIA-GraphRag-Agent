'use client'

import { motion } from 'framer-motion'
import FloatingCrosses from './FloatingCrosses'
import FloatingParticles from './FloatingParticles'

export default function AnimatedBackground({ bgStyle = 'clinical-light' }: { bgStyle?: 'clinical-light' | 'neon-matrix' }) {
    const isDark = bgStyle !== 'clinical-light'

    return (
        <div className="absolute inset-0 overflow-hidden">
            {/* Base Background color container */}
            <div className={`absolute inset-0 transition-colors duration-1000 ${isDark ? 'bg-[#03060c]' : 'bg-[#eef4f7]'
                }`} />

            {/* Radial gradient - top center bright spot */}
            <div className={`absolute inset-0 transition-all duration-1000 ${isDark
                    ? 'bg-[radial-gradient(ellipse_80%_60%_at_50%_0%,rgba(4,112,99,0.15)_0%,rgba(3,6,12,0.95)_60%,rgba(3,6,12,1)_100%)]'
                    : 'bg-[radial-gradient(ellipse_80%_60%_at_50%_0%,rgba(255,255,255,1)_0%,rgba(237,248,250,0.95)_50%,rgba(220,240,245,0.8)_100%)]'
                }`} />

            {/* Subtle large cyan glow */}
            <motion.div
                animate={{ scale: [1, 1.04, 1], opacity: isDark ? [0.06, 0.12, 0.06] : [0.12, 0.2, 0.12] }}
                transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
                className={`absolute left-1/2 top-1/3 h-[900px] w-[900px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-3xl transition-colors duration-1000 ${isDark ? 'bg-healia-green/25' : 'bg-healia-teal/30'
                    }`}
            />

            {/* Bottom right soft teal blob */}
            <motion.div
                animate={{ scale: [1, 1.06, 1], opacity: isDark ? [0.04, 0.1, 0.04] : [0.1, 0.18, 0.1] }}
                transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut', delay: 3 }}
                className={`absolute right-0 bottom-0 h-[600px] w-[600px] translate-x-1/4 translate-y-1/4 rounded-full blur-3xl transition-colors duration-1000 ${isDark ? 'bg-healia-dark/20' : 'bg-healia-dark/20'
                    }`}
            />

            {/* Subtle diagonal lines */}
            <svg
                className={`absolute inset-0 h-full w-full transition-opacity duration-1000 ${isDark ? 'opacity-[0.03]' : 'opacity-[0.07]'}`}
                viewBox="0 0 1600 900"
                fill="none"
                preserveAspectRatio="none"
            >
                <path d="M0 180 C 400 60, 900 400, 1600 180" stroke={isDark ? '#4da73c' : '#4bb8bd'} strokeWidth="1.5" />
                <path d="M0 260 C 500 90, 1100 450, 1600 240" stroke={isDark ? '#4da73c' : '#4bb8bd'} strokeWidth="1.5" />
                <path d="M0 340 C 600 140, 1200 560, 1600 300" stroke={isDark ? '#4da73c' : '#4bb8bd'} strokeWidth="1.5" />
                <path d="M0 420 C 300 200, 800 600, 1600 380" stroke={isDark ? '#4da73c' : '#4bb8bd'} strokeWidth="1" />
            </svg>

            {/* Floating 3D crosses + sparkles */}
            <FloatingCrosses bgStyle={bgStyle} />

            {/* Subtle floating dots */}
            <FloatingParticles bgStyle={bgStyle} />
        </div>
    )
}