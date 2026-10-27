'use client'

import { motion } from 'framer-motion'

const particles = Array.from({ length: 60 })

export default function ParticleField({ bgStyle = 'clinical-light' }: { bgStyle?: 'clinical-light' | 'neon-matrix' }) {
    const isDark = bgStyle !== 'clinical-light'

    return (
        <>
            {particles.map((_, i) => {
                const size = Math.random() * 4 + 1

                return (
                    <motion.div
                        key={i}
                        className={`absolute rounded-full transition-colors duration-1000 ${isDark ? 'bg-healia-green' : 'bg-healia-teal'
                            }`}
                        style={{
                            width: size,
                            height: size,
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                            boxShadow: isDark ? '0 0 15px rgba(77,167,60,0.7)' : '0 0 15px rgba(75,184,189,0.7)',
                        }}
                        animate={{
                            y: [0, -40, 0],
                            x: [0, 20, 0],
                            opacity: [0.2, 1, 0.2],
                        }}
                        transition={{
                            duration: Math.random() * 10 + 10,
                            repeat: Infinity,
                            ease: 'easeInOut',
                        }}
                    />
                )
            })}
        </>
    )
}