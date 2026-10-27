'use client'

import { useState } from 'react'
import { FormBlock as FormBlockType } from '../../types'
import { Send } from 'lucide-react'

type Props = { block: FormBlockType; isDark: boolean; onSubmit?: (values: Record<string, any>) => void }

export default function FormBlock({ block, isDark, onSubmit }: Props) {
    const [values, setValues] = useState<Record<string, any>>({})

    const handleChange = (name: string, value: any) => {
        setValues((prev) => ({ ...prev, [name]: value }))
    }

    const handleSubmit = () => {
        onSubmit?.(values)
    }

    return (
        <div className={`rounded-2xl border p-4 ${isDark ? 'bg-gray-900/60 border-gray-800' : 'bg-white border-gray-200'}`}>
            {block.title && (
                <h3 className={`text-sm font-bold mb-4 ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>{block.title}</h3>
            )}
            <div className="space-y-3">
                {block.fields.map((field) => (
                    <div key={field.name}>
                        <label className={`block text-xs font-medium mb-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                            {field.label}
                        </label>
                        {field.type === 'select' ? (
                            <select
                                value={values[field.name] || ''}
                                onChange={(e) => handleChange(field.name, e.target.value)}
                                className={`w-full rounded-xl px-3 py-2 text-xs border focus:outline-none focus:ring-2 ${
                                    isDark
                                        ? 'bg-gray-800 border-gray-700 text-gray-200 focus:ring-healia-teal/40'
                                        : 'bg-white border-gray-300 text-gray-700 focus:ring-healia-teal/30'
                                }`}
                            >
                                <option value="">Sélectionner...</option>
                                {field.options?.map((opt) => (
                                    <option key={opt} value={opt}>{opt}</option>
                                ))}
                            </select>
                        ) : field.type === 'slider' ? (
                            <div className="flex items-center gap-3">
                                <input
                                    type="range"
                                    min={0}
                                    max={100}
                                    value={values[field.name] || 50}
                                    onChange={(e) => handleChange(field.name, Number(e.target.value))}
                                    className="flex-1 accent-healia-teal"
                                />
                                <span className={`text-xs font-mono w-8 text-right ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                                    {values[field.name] || 50}
                                </span>
                            </div>
                        ) : (
                            <input
                                type={field.type}
                                value={values[field.name] || ''}
                                onChange={(e) => handleChange(field.name, e.target.value)}
                                placeholder={field.label}
                                className={`w-full rounded-xl px-3 py-2 text-xs border focus:outline-none focus:ring-2 ${
                                    isDark
                                        ? 'bg-gray-800 border-gray-700 text-gray-200 focus:ring-healia-teal/40'
                                        : 'bg-white border-gray-300 text-gray-700 focus:ring-healia-teal/30'
                                }`}
                            />
                        )}
                    </div>
                ))}
                <button
                    onClick={handleSubmit}
                    className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl transition-all ${
                        isDark
                            ? 'bg-healia-teal text-white hover:bg-healia-teal/90'
                            : 'bg-healia-teal text-white hover:bg-healia-teal/90'
                    }`}
                >
                    <Send className="h-3 w-3" />
                    Envoyer
                </button>
            </div>
        </div>
    )
}
