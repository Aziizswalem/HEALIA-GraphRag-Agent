'use client'

import Lottie from 'lottie-react'
import animationData from './healio-anim.json'

interface Props {
    loop?: boolean
    onComplete?: () => void
}

export default function HealioAnimation({ loop = true, onComplete }: Props) {
    return (
        <div className="w-full h-full flex items-center justify-center relative">
            <Lottie
                animationData={animationData}
                loop={loop}
                onComplete={onComplete}
                style={{ width: '100%', height: '100%' }}
            />
        </div>
    )
}