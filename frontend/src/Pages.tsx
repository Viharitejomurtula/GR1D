import type { ReactNode } from 'react'
import SolutionDiagram from './SolutionDiagram'

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

export function WhyItMattersBrief({ onNext, onReplay }: { onNext: () => void; onReplay: () => void }) {
  return (
    <section className="mx-auto max-w-[900px] px-10 pt-36 pb-48">
      <div className="flex items-baseline justify-between">
        <p className={`${label} text-[#d9b24c]`}>Why it matters</p>
        <button onClick={onReplay} className={`${label} cursor-pointer text-[#8d8670] underline-offset-[7px] transition hover:text-white hover:underline`}>↑ Replay</button>
      </div>
      <h2 className="display mt-4 max-w-[800px] text-[56px] leading-[1.02] font-semibold tracking-[-0.04em] text-[#f6f1e2]">
        What you just watched is getting bigger, and the grid is not ready for it.
      </h2>

      <div className="mt-24 space-y-14">
        <Item n="01" title="Labs are raising the alarm.">National laboratories cite sudden, simultaneous data center load loss as a potential danger to grid reliability.</Item>
        <Item n="02" title="It is getting worse.">The July 2026 event was about 2.5 times the 2024 one, and AI data centers are being built faster than the grid can adapt.</Item>
        <Item n="03" title="Industry is building a fix.">
          Companies are developing backup power and storage that connect the grid and the data center more smoothly, keeping a site’s draw
          steady through dips. ERCOT will require 90% of prior power back within 2 seconds from August 2026.
        </Item>
      </div>

      <div className="mt-40">
        <p className={`${label} text-[#ff7a4d]`}>The gap</p>
        <h3 className="display mt-4 max-w-[760px] text-[44px] leading-[1.05] font-semibold tracking-[-0.035em] text-[#f6f1e2]">
          Nobody can prove a design will hold.
        </h3>
        <p className="mt-6 max-w-[620px] text-[19px] leading-[1.55] text-[#d3ccb8]">
          There is no certification system, so proof is done case by case: a handful of lab tests and simulations that can miss the rare
          combinations of conditions where things actually fail. The utility, the buyer and the financiers all have to trust a design on
          that basis.
        </p>
      </div>

      <div className="mt-28">
        <p className={`${label} text-[#d9b24c]`}>What fills it</p>
        <h3 className="display mt-4 max-w-[760px] text-[44px] leading-[1.05] font-semibold tracking-[-0.035em] text-[#f6f1e2]">
          We hunt for the failures before they happen.
        </h3>
        <p className="mt-6 max-w-[620px] text-[19px] leading-[1.55] text-[#d3ccb8]">
          Our system searches the conditions a data center can face and reports the distinct ways a design fails, giving all three parties
          one shared, checkable answer to “will this design hold up when the grid dips?”
        </p>
        <button onClick={onNext} className={`${label} mt-10 cursor-pointer text-[13px] text-[#f0c85a] underline-offset-[8px] transition hover:text-white hover:underline`}>
          See how it works →
        </button>
      </div>
    </section>
  )
}

export function OurSolution() {
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
          <Item n="01" title="Model the world.">Probability distributions for dip depth and duration, repeated dips, AI load swings, temperature and battery charge level.</Item>
          <Item n="02" title="Model the hardware.">Distributions for how real equipment varies from its datasheet: battery aging, response times and power supply trip thresholds.</Item>
          <Item n="03" title="Model how they depend on each other.">A cold morning, a low battery and an AI load surge can arrive together. The model keeps that structure.</Item>
          <Item n="04" title="Run the physics, fast.">Existing physics simulators are wrapped in a fast neural-network stand-in, so millions of scenarios can be checked.</Item>
          <Item n="05" title="Search for distinct failures.">The search looks for different ways the design fails, not many copies of the same failure.</Item>
          <div className="pt-4">
            <p className={`${label} text-[#d9b24c]`}>No invented precision</p>
            <p className="mt-2 max-w-[600px] text-[17px] leading-[1.6] text-[#c4bca7]">Where there is only a manufacturer limit and no real data, the tool uses bounds, not made-up distributions.</p>
            <p className={`${label} mt-8 text-[#d9b24c]`}>What-ifs stay separate</p>
            <p className="mt-2 max-w-[600px] text-[17px] leading-[1.6] text-[#c4bca7]">“What if a setting was wrong” tests are kept apart from the probabilities, so they never blur the risk number.</p>
          </div>
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
