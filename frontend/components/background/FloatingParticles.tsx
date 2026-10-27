'use client'

import { motion } from 'framer-motion'

const particles = Array.from({ length: 40 }, (_, i) => i)

export default function FloatingParticles({ bgStyle = 'clinical-light' }: { bgStyle?: 'clinical-light' | 'neon-matrix' }) {
    const isDark = bgStyle !== 'clinical-light'

    return (
        <>
            {particles.map((i) => {
                const size = Math.random() * 3 + 1.5
                return (
                    <motion.div
                        key={i}
                        className={`absolute rounded-full transition-colors duration-1000 ${isDark ? 'bg-healia-green/60' : 'bg-healia-teal/60'
                            }`}
                        style={{
                            width: size,
                            height: size,
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                            boxShadow: isDark ? '0 0 8px rgba(77,167,60,0.4)' : '0 0 8px rgba(75,184,189,0.4)',
                        }}
                        animate={{
                            y: [0, -35, 0],
                            opacity: [0.1, 0.5, 0.1],
                        }}
                        transition={{
                            duration: Math.random() * 12 + 10,
                            repeat: Infinity,
                            ease: 'easeInOut',
                            delay: Math.random() * 5,
                        }}
                    />
                )
            })}
        </>
    )
}