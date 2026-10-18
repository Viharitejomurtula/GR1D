import type { CSSProperties, ReactNode } from 'react'
import { useEffect, useRef, useState } from 'react'
import SolutionDiagram from './SolutionDiagram'
import UseCases from './UseCases'
import techTimes from './assets/clip-techtimes.png'
import nercAlert from './assets/clip-nerc-alert.png'

const label = 'mono text-[12px] font-medium tracking-[0.14em] uppercase'

// Plain statements on a plain background: short lines, lots of air, no boxes or rules.
function Item({ n, title, children }: { n: string; title: string; children: ReactNode }) {
  return (
    <div className="grid gap-x-6 md:grid-cols-[44px_1fr]">
      <div className="mono pt-[7px] text-[12px] text-[#d9b24c]">{n}</div>
      <div>
        <h3 className="display text-[26px] leading-[1.15] font-semibold tracking-[-0.025em] text-[#f6f1e2]">{title}</h3>
        <p className="mt-2 max-w-[600px] text-[17px] leading-[1.6] text-[#c4bca7]">{children}</p>
      </div>
    </div>
  )
}

function Page({ kicker, title, lede, children }: { kicker: string; title: string; lede?: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-[900px] px-10 pt-24 pb-40">
      <p className={`${label} text-[#d9b24c]`}>{kicker}</p>
      <h1 className="display mt-4 max-w-[800px] text-[56px] leading-[1.02] font-semibold tracking-[-0.04em] text-[#f6f1e2]">{title}</h1>
      {lede && <p className="mt-7 max-w-[620px] text-[19px] leading-[1.55] text-[#d3ccb8]">{lede}</p>}
      <div className="mt-24 space-y-14">{children}</div>
    </div>
  )
}

// Drops onto the page at an angle when scrolled into view, like a pasted clipping.
function Slap({ children, rotate, from = 1, delay = 0, className = '', style }: {
  children: ReactNode; rotate: number; from?: 1 | -1; delay?: number; className?: string; style?: CSSProperties
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [on, setOn] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setOn(true); io.disconnect() } }, { threshold: 0.35 })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return (
    <div ref={ref} className={className} style={{
      ...style,
      opacity: on ? 1 : 0,
      transform: on ? `rotate(${rotate}deg) scale(1)` : `translate(${from * 140}px, -90px) rotate(${rotate + from * 14}deg) scale(1.45)`,
      transition: `transform 0.42s cubic-bezier(0.2, 1.5, 0.4, 1) ${delay}s, opacity 0.12s linear ${delay}s`,
    }}>
      {children}
    </div>
  )
}

const COMPANIES = ['AionTracks', 'Vertiv', 'Eaton', 'Schneider Electric', 'ABB', 'Siemens', 'Delta Electronics', 'Legrand', 'Hitachi Energy', 'GE Vernova', 'Fluence', 'Tesla']

export function WhyItMattersBrief({ onNext, onReplay }: { onNext: () => void; onReplay: () => void }) {
  const ink = 'text-[#16140e]'
  const body = 'text-[#4a4535]'
  const shadow = 'shadow-[0_2px_4px_rgba(40,30,10,0.25),0_18px_40px_-8px_rgba(40,30,10,0.45)]'
  return (
    <div className="bg-[#e8e1cf]">
      <section className="mx-auto max-w-[1240px] px-10 pt-32 pb-48">
        <div className="flex items-baseline justify-between">
          <p className={`${label} text-[#8a6410]`}>Why it matters</p>
          <button onClick={onReplay} className={`${label} cursor-pointer text-[#7a725a] underline-offset-[7px] transition hover:text-black hover:underline`}>↑ Replay</button>
        </div>
        <h2 className={`display mt-4 max-w-[860px] text-[56px] leading-[1.02] font-semibold tracking-[-0.04em] ${ink}`}>
          What you just watched is getting bigger, and the grid is not ready for it.
        </h2>

        <div className="mt-24 grid gap-x-16 lg:grid-cols-[minmax(0,520px)_1fr]">
          <div className="space-y-20">
            <LightItem n="01" title="Labs are raising the alarm.">National laboratories cite sudden, simultaneous data center load loss as a potential danger to grid reliability.</LightItem>
            <LightItem n="02" title="It is getting worse.">The July 2026 event was about 2.5 times the 2024 one, and AI data centers are being built faster than the grid can adapt.</LightItem>
            <LightItem n="03" title="Industry is building a fix.">
              Companies are building the connection between the grid and the data center so that a site’s draw stays steady through dips. ERCOT will require 90% of prior power back within 2 seconds from August 2026.
              <span className="mt-7 block max-w-[440px]">
                <span className="mono block border-b border-[#16140e] pb-2 text-[11px] font-medium tracking-[0.16em] text-[#7a725a] uppercase">Working on it</span>
                <span className="grid grid-cols-2 gap-x-8">
                  {COMPANIES.map((c, i) => (
                    <Slap key={c} rotate={0} from={i % 2 ? -1 : 1} delay={i * 0.08}>
                      <span className="display block border-b border-[#16140e]/20 py-3 text-[19px] font-semibold tracking-[-0.015em] text-[#16140e]">{c}</span>
                    </Slap>
                  ))}
                </span>
              </span>
            </LightItem>
          </div>

          <div className="relative hidden min-h-[1180px] lg:block">
            <Slap rotate={3} from={1} className="absolute top-0 right-0 w-[560px]">
              <img src={techTimes} alt="Tech Times: AI Data Centers Triggered 1,800 MW Grid Drop; NERC Issues Highest Alert" className={`w-full ${shadow}`} />
            </Slap>
            <Slap rotate={-5} from={-1} delay={0.05} className="absolute top-[420px] left-0 w-[340px]">
              <img src={nercAlert} alt="NERC Level 3 Alert: Essential Action to Industry on computational load" className={`w-full ${shadow}`} />
            </Slap>
          </div>
        </div>

        <div className="mt-36">
          <p className={`${label} text-[#b13d12]`}>The gap</p>
          <h3 className={`display mt-4 max-w-[760px] text-[44px] leading-[1.05] font-semibold tracking-[-0.035em] ${ink}`}>
            Nobody can prove a design will hold.
          </h3>
          <p className={`mt-6 max-w-[620px] text-[19px] leading-[1.55] ${body}`}>
            There is no certification system, so proof is done case by case: a handful of lab tests and simulations that can miss the rare
            combinations of conditions where things actually fail. The utility, the buyer and the financiers all have to trust a design on
            that basis.
          </p>
        </div>

        <div className="mt-28">
          <p className={`${label} text-[#8a6410]`}>What fills it</p>
          <h3 className={`display mt-4 max-w-[760px] text-[44px] leading-[1.05] font-semibold tracking-[-0.035em] ${ink}`}>
            We hunt for the failures before they happen.
          </h3>
          <p className={`mt-6 max-w-[620px] text-[19px] leading-[1.55] ${body}`}>
            Our system searches the conditions a data center can face and reports the distinct ways a design fails, giving all three parties
            one shared, checkable answer to “will this design hold up when the grid dips?”
          </p>
          <button onClick={onNext} className={`${label} mt-10 cursor-pointer text-[13px] text-[#8a6410] underline-offset-[8px] transition hover:text-black hover:underline`}>
            See how it works →
          </button>
        </div>
      </section>
    </div>
  )
}

function LightItem({ n, title, children }: { n: string; title: string; children: ReactNode }) {
  return (
    <div className="grid gap-x-6 md:grid-cols-[44px_1fr]">
      <div className="mono pt-[7px] text-[12px] text-[#8a6410]">{n}</div>
      <div>
        <h3 className="display text-[26px] leading-[1.15] font-semibold tracking-[-0.025em] text-[#16140e]">{title}</h3>
        <p className="mt-2 max-w-[600px] text-[17px] leading-[1.6] text-[#4a4535]">{children}</p>
      </div>
    </div>
  )
}


export function OurSolution({ onValidation }: { onValidation: () => void }) {
  return (
    <div className="mx-auto max-w-[1240px] px-10 pt-20 pb-40">
      <p className={`${label} text-[#d9b24c]`}>Our solution</p>
      <h1 className="display mt-4 max-w-[860px] text-[52px] leading-[1.03] font-semibold tracking-[-0.04em] text-[#f6f1e2]">
        We stress-test the connection between the grid and the data center.
      </h1>
      <p className="mt-6 max-w-[660px] text-[19px] leading-[1.55] text-[#d3ccb8]">
        Two things come out: a ranking of which factors move the result the most, and the distribution of how often a design holds up.
      </p>

      <div className="mt-14">
        <SolutionDiagram />
        <p className="mono mt-3 text-[11px] tracking-[0.06em] text-[#8d8670]">
          Illustrative values. The pipeline does not produce these outputs yet; this shows what they will look like.
        </p>
      </div>

      <div className="mx-auto mt-32 max-w-[900px]">
        <p className={`${label} text-[#d9b24c]`}>How it works</p>
        <div className="mt-10 space-y-14">
          <Item n="01" title="Treat every input as a probability distribution.">
            Dip depth and duration, repeated dips, AI load swings, temperature, battery charge and aging, and how real equipment varies
            from its datasheet are each fitted to public data (ERCOT and NERC events, measured AI power traces) instead of a single guess.
          </Item>
          <Item n="02" title="Link them with a Bayesian network.">
            A cold morning, an aged battery and an AI load surge tend to arrive together. The network ties 14 equipment factors to shared
            drivers like temperature, site load, equipment age and workload, so scenarios are drawn with that dependence intact.
          </Item>
          <Item n="03" title="Run a physics engine, validated against real events.">
            An OpenModelica model of the converter, batteries, power supplies, servers and cooling, graded the way ERCOT’s rule is. It was
            checked against two real Texas facilities that lost 46% and 24% of load, a shallow 0.844 pu dip it was not fitted to (22% predicted
            vs 19% real), and a vendor’s 70-sag recovery test (0.39 s median vs 0.41 s).
          </Item>
          <Item n="04" title="Use a neural surrogate for speed.">
            The simulator is slow, so an ensemble of neural networks learns to imitate it in milliseconds, which makes millions of scenarios
            affordable. Where the networks disagree it flags its own uncertainty, and every failure it finds is re-run in the real simulator
            before it reaches the report.
          </Item>
          <Item n="05" title="Search for distinct failures.">The search looks for different ways the design fails, not many copies of the same failure.</Item>
          <div className="pt-4">
            <p className={`${label} text-[#d9b24c]`}>No invented precision</p>
            <p className="mt-2 max-w-[600px] text-[17px] leading-[1.6] text-[#c4bca7]">Where there is only a manufacturer limit and no real data, the tool uses bounds, not made-up distributions.</p>
            <p className={`${label} mt-8 text-[#d9b24c]`}>What-ifs stay separate</p>
            <p className="mt-2 max-w-[600px] text-[17px] leading-[1.6] text-[#c4bca7]">“What if a setting was wrong” tests are kept apart from the probabilities, so they never blur the risk number.</p>
          </div>
        </div>
        <div className="mt-24 border-t border-white/12 pt-10">
          <button onClick={onValidation} className="group flex w-full cursor-pointer items-center justify-between text-left">
            <span>
              <span className={`${label} block text-[#d9b24c]`}>Don’t take our word for it</span>
              <span className="display mt-2 block text-[32px] font-semibold tracking-[-0.03em] text-[#f6f1e2] transition group-hover:text-white">Validation / Testing</span>
            </span>
            <span className="display text-[44px] text-[#f0c85a] transition group-hover:translate-x-2 group-hover:text-white">→</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export function Deliverables() {
  return (
    <Page
      kicker="Deliverables"
      title="One report a developer can act on and a utility can trust."
      lede="A developer of ride-through technology uses the tool during design, before building or shipping. They enter a reference data center and their design, and the tool shows how it fails and which fix is smallest."
    >
      <UseCases />
      <Item n="01" title="Pass probability.">The probability that the design passes the grid rule, with an honest uncertainty band.</Item>
      <Item n="02" title="Failure modes.">The worst cases found, grouped into distinct failure modes, each with an example scenario.</Item>
      <Item n="03" title="What matters most.">Which factors drive the failures the most.</Item>
      <Item n="04" title="Smallest fix.">For each failure mode, the smallest change that removes it, such as a bigger storage window or a changed setting.</Item>
      <Item n="05" title="Setting-mismatch checklist.">A separate checklist of “what if a setting was wrong” cases, kept apart from the probability.</Item>
      <p className="max-w-[640px] pt-8 text-[19px] leading-[1.55] text-[#d3ccb8]">
        The same report goes to the people who approve and pay for the project: the utility, the data center owner and the financiers. All
        three get one shared, checkable answer to <span className="text-[#f0c85a]">“will this design hold up when the grid dips?”</span> instead of
        a few lab tests and a promise.
      </p>
    </Page>
  )
}
