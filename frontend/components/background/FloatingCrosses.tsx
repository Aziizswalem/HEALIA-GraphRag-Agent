'use client'

import { motion } from 'framer-motion'

function StageeShape({ size, isDark }: { size: number; isDark: boolean }) {
    const s = size
    return (
        <svg
            width={s}
            height={s}
            viewBox="0 0 120 120"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            {/* Top arm */}
            <rect x="42" y="0" width="36" height="36" rx="4" fill="url(#g1)" opacity="0.9" />
            <rect x="48" y="4" width="24" height="28" rx="3" fill="url(#g2)" opacity="0.5" />

            {/* Bottom arm */}
            <rect x="42" y="84" width="36" height="36" rx="4" fill="url(#g1)" opacity="0.9" />
            <rect x="48" y="88" width="24" height="28" rx="3" fill="url(#g2)" opacity="0.5" />

            {/* Left arm */}
            <rect x="0" y="42" width="36" height="36" rx="4" fill="url(#g1)" opacity="0.9" />
            <rect x="4" y="48" width="28" height="24" rx="3" fill="url(#g2)" opacity="0.5" />

            {/* Right arm */}
            <rect x="84" y="42" width="36" height="36" rx="4" fill="url(#g1)" opacity="0.9" />
            <rect x="88" y="48" width="28" height="24" rx="3" fill="url(#g2)" opacity="0.5" />

            {/* Center */}
            <rect x="42" y="42" width="36" height="36" rx="4" fill="url(#g3)" opacity="0.95" />
            <rect x="46" y="46" width="28" height="28" rx="3" fill="url(#g4)" opacity="0.6" />

            {/* Top-right diagonal accent */}
            <rect x="78" y="6" width="18" height="18" rx="3" fill="url(#g1)" opacity="0.45" />
            <rect x="6" y="78" width="18" height="18" rx="3" fill="url(#g1)" opacity="0.35" />
            <rect x="96" y="78" width="18" height="18" rx="3" fill="url(#g1)" opacity="0.35" />

            <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1" gradientUnits="objectBoundingBox">
                    <stop stopColor={isDark ? '#4da73c' : '#4bb8bd'} />
                    <stop offset="1" stopColor={isDark ? '#047063' : '#047063'} />
                </linearGradient>
                <linearGradient id="g2" x1="0" y1="0" x2="1" y2="1" gradientUnits="objectBoundingBox">
                    <stop stopColor={isDark ? '#a7f3d0' : '#99f6e4'} stopOpacity="0.9" />
                    <stop offset="1" stopColor={isDark ? '#4da73c' : '#4bb8bd'} stopOpacity="0.3" />
                </linearGradient>
                <linearGradient id="g3" x1="0" y1="0" x2="1" y2="1" gradientUnits="objectBoundingBox">
                    <stop stopColor={isDark ? '#047063' : '#4bb8bd'} />
                    <stop offset="1" stopColor={isDark ? '#047063' : '#047063'} />
                </linearGradient>
                <linearGradient id="g4" x1="0" y1="0" x2="1" y2="1" gradientUnits="objectBoundingBox">
                    <stop stopColor={isDark ? '#d1fae5' : '#a7f3e8'} stopOpacity="0.8" />
                    <stop offset="1" stopColor={isDark ? '#4da73c' : '#4bb8bd'} stopOpacity="0.2" />
                </linearGradient>
            </defs>
        </svg>
    )
}

function DiamondSparkle({ size, isDark }: { size: number; isDark: boolean }) {
    return (
        <svg width={size} height={size} viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10 0 L13 7 L20 10 L13 13 L10 20 L7 13 L0 10 L7 7 Z" fill={isDark ? '#4da73c' : '#4bb8bd'} opacity="0.7" />
        </svg>
    )
}

function SmallPlus({ size, isDark }: { size: number; isDark: boolean }) {
    return (
        <svg width={size} height={size} viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="8" y="0" width="4" height="20" rx="2" fill={isDark ? '#4da73c' : '#4bb8bd'} opacity="0.6" />
            <rect x="0" y="8" width="20" height="4" rx="2" fill={isDark ? '#4da73c' : '#4bb8bd'} opacity="0.6" />
        </svg>
    )
}

const bigCrosses = [
    { left: '22%', top: '12%', size: 90, rotate: -15, duration: 35 },
    { left: '72%', top: '8%', size: 130, rotate: 10, duration: 40 },
    { left: '18%', top: '55%', size: 110, rotate: 5, duration: 45 },
    { left: '80%', top: '45%', size: 80, rotate: -8, duration: 38 },
    { left: '55%', top: '70%', size: 60, rotate: 20, duration: 32 },
]

const sparkles = Array.from({ length: 18 }, (_, i) => ({
    left: `${(i * 13 + 5) % 100}%`,
    top: `${(i * 17 + 8) % 100}%`,
    size: Math.random() * 8 + 6,
    type: i % 3 === 0 ? 'diamond' : 'plus',
    duration: 15 + (i % 8) * 3,
    delay: i * 0.7,
}))

export default function FloatingCrosses({ bgStyle = 'clinical-light' }: { bgStyle?: 'clinical-light' | 'neon-matrix' }) {
    const isDark = bgStyle !== 'clinical-light'

    return (
        <>
            {/* Large 3D crosses */}
            {bigCrosses.map((cross, i) => (
                <motion.div
                    key={`cross-${i}`}
                    className="absolute pointer-events-none"
                    style={{ left: cross.left, top: cross.top }}
                    animate={{
                        y: [0, -20, 0],
                        x: [0, 10, 0],
                        rotate: [cross.rotate, cross.rotate + 8, cross.rotate],
                        opacity: [0.35, 0.65, 0.35],
                    }}
                    transition={{
                        duration: cross.duration,
                        repeat: Infinity,
                        ease: 'easeInOut',
                    }}
                >
                    <StageeShape size={cross.size} isDark={isDark} />
                </motion.div>
            ))}

            {/* Small sparkles and plus signs */}
            {sparkles.map((sp, i) => (
                <motion.div
                    key={`sparkle-${i}`}
                    className="absolute pointer-events-none"
                    style={{ left: sp.left, top: sp.top }}
                    animate={{
                        y: [0, -12, 0],
                        opacity: [0.2, 0.7, 0.2],
                    }}
                    transition={{
                        duration: sp.duration,
                        repeat: Infinity,
                        ease: 'easeInOut',
                        delay: sp.delay,
                    }}
                >
                    {sp.type === 'diamond' ? (
                        <DiamondSparkle size={sp.size} isDark={isDark} />
                    ) : (
                        <SmallPlus size={sp.size} isDark={isDark} />
                    )}
                </motion.div>
            ))}
        </>
    )
}