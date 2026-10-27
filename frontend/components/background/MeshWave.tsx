'use client'

export default function MeshWave({ bgStyle = 'clinical-light' }: { bgStyle?: 'clinical-light' | 'neon-matrix' }) {
    const isDark = bgStyle !== 'clinical-light'

    return (
        <div className="absolute bottom-0 left-0 right-0 h-[320px] opacity-40">
            <svg
                viewBox="0 0 1440 320"
                className="absolute bottom-0 h-full w-full"
                preserveAspectRatio="none"
            >
                <path
                    fill={isDark ? 'rgba(4,112,99,0.15)' : 'rgba(75,184,189,0.2)'}
                    className="transition-all duration-1000"
                    d="M0,224L80,208C160,192,320,160,480,165.3C640,171,800,213,960,229.3C1120,245,1280,235,1360,229.3L1440,224L1440,320L0,320Z"
                />
            </svg>
        </div>
    )
}