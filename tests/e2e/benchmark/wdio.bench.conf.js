// Benchmark de browser.act: misma config que ../wdio.conf.js, pero con caché propia
// (benchmark/__act__/, no pisa la commiteada) y registro de uso por llamada en BENCH_OUT (NDJSON).
//   BENCH_CACHE=write (defecto) con benchmark/__act__/ vacía → el modelo graba cada act (en frío)
//   BENCH_CACHE=locked → solo repite benchmark/__act__/ (sin modelo)
import { appendFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { initChatModel } from 'langchain'
import { config as base } from '../wdio.conf.js'

const aqui = (p) => fileURLToPath(new URL(p, import.meta.url))
const out = process.env.BENCH_OUT
const log = (tipo, datos) => out && appendFileSync(out, JSON.stringify({ tipo, t: Date.now(), ...datos }) + '\n')

// Mismo modelo que wdio.conf.js (Sonnet 5, temperature 1, maxTokens por defecto del servicio),
// creado aquí solo para leer el usage completo de cada llamada (incluye tokens de caché de prompt).
const model = process.env.ANTHROPIC_API_KEY && await initChatModel('claude-sonnet-5', {
    modelProvider: 'anthropic', temperature: 1, maxTokens: 4096,
    callbacks: [{ handleLLMEnd: (o) => o.generations.flat().forEach((g) => log('llm', { usage: g.message?.usage_metadata })) }],
})

// Un registro por act: { instruction, source, healed, usage, durationMs, error }
process.on('ai:act', (r) => log('act', { instruction: r.instruction, source: r.source, healed: r.healed, usage: r.usage, durationMs: r.durationMs, error: r.error }))

export const config = {
    ...base,
    specs: [aqui(process.env.BENCH_SPEC ?? '../features/clasificar-ia.feature')],
    cucumberOpts: { ...base.cucumberOpts, require: [aqui('../steps/*.js')] },
    reporters: ['spec'],
    services: [['ai', { model: model || base.services[0][1].model, cache: process.env.BENCH_CACHE ?? 'write', cacheDir: aqui('./__act__/') }]],
}
