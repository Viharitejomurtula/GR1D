import { useRef, useState } from 'react'
import GridDemo from './GridDemo'
import { Deliverables, OurSolution, WhyItMattersBrief } from './Pages'
import Results from './Results'

const TABS = ['The Problem', 'Our Solution', 'Deliverables', 'Results'] as const

export default function App() {
  const [tab, setTab] = useState<(typeof TABS)[number]>('The Problem')
  const scroller = useRef<HTMLDivElement>(null)
  const why = useRef<HTMLDivElement>(null)
  const toWhy = () => scroller.current?.scrollTo({ top: why.current?.offsetTop ?? 0, behavior: 'smooth' })
  const toTop = () => scroller.current?.scrollTo({ top: 0, behavior: 'smooth' })

  return (
    <div className="flex h-full flex-col bg-[#07070a]">
      <nav className="flex h-12 shrink-0 items-center gap-9 bg-[#07070a] px-10">
        <span className="mono mr-2 text-[12.5px] font-semibold tracking-[0.2em] text-[#d9b24c]">GR1D</span>
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`h-full display cursor-pointer border-b text-[14px] font-medium tracking-[-0.005em] transition ${tab === t ? 'border-[#d9b24c] text-[#f1ecdc]' : 'border-transparent text-[#948d78] hover:text-[#d3ccb8]'}`}
          >
            {t}
          </button>
        ))}
      </nav>
      <div className="relative min-h-0 flex-1">
        {tab === 'The Problem' ? (
          <div ref={scroller} className="h-full overflow-y-auto">
            <div className="relative h-full min-h-[560px]">
              <GridDemo onFinished={toWhy} onNext={toWhy} />
            </div>
            <div ref={why} className="bg-[#07070a]">
              <WhyItMattersBrief onNext={() => { setTab('Our Solution') }} onReplay={toTop} />
            </div>
          </div>
        ) : (
          <div className="h-full overflow-y-auto">{tab === 'Our Solution' ? <OurSolution /> : tab === 'Deliverables' ? <Deliverables /> : <Results />}</div>
        )}
      </div>
    </div>
  )
}
