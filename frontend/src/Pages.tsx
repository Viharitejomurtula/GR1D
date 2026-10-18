import type { ReactNode } from 'react'

const label = 'mono text-[11px] tracking-[0.14em] uppercase'

function Page({ kicker, title, lede, children }: { kicker: string; title: string; lede?: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-[1040px] px-8 pt-16 pb-24">
      <p className={`${label} text-[#8a8472]`}>{kicker}</p>
      <h1 className="mt-3 max-w-[760px] text-[38px] leading-[1.12] font-medium tracking-[-0.022em] text-[#ece6d6]">{title}</h1>
      {lede && <p className="mt-5 max-w-[640px] text-[16px] leading-[1.65] text-[#a29b86]">{lede}</p>}
      <div className="mt-14">{children}</div>
    </div>
  )
}

const Row = ({ n, title, children }: { n: string; title: string; children: ReactNode }) => (
  <div className="grid gap-x-8 gap-y-1.5 border-t border-[#1f1d17] py-5 md:grid-cols-[48px_240px_1fr]">
    <div className="mono pt-0.5 text-[11px] text-[#6b6555]">{n}</div>
    <h3 className="text-[15px] font-medium text-[#e8e2d2]">{title}</h3>
    <p className="max-w-[560px] text-[14.5px] leading-[1.65] text-[#9a9380]">{children}</p>
  </div>
)

const Note = ({ title, children }: { title: string; children: ReactNode }) => (
  <div className="border-t border-[#1f1d17] pt-5">
    <p className={`${label} text-[#d9b24c]`}>{title}</p>
    <p className="mt-2 max-w-[460px] text-[14.5px] leading-[1.65] text-[#9a9380]">{children}</p>
  </div>
)

export function WhyItMattersBrief({ onNext, onReplay }: { onNext: () => void; onReplay: () => void }) {
  return (
    <section className="mx-auto max-w-[1040px] px-8 pt-24 pb-28">
      <div className="flex items-baseline justify-between">
        <p className={`${label} text-[#8a8472]`}>Why it matters</p>
        <button onClick={onReplay} className={`${label} cursor-pointer text-[#6b6555] transition hover:text-[#b8b19d]`}>↑ Replay</button>
      </div>
      <h2 className="mt-3 max-w-[720px] text-[36px] leading-[1.12] font-medium tracking-[-0.022em] text-[#ece6d6]">
        What you just watched is getting bigger, and the grid is not ready for it.
      </h2>

      <div className="mt-12">
        <Row n="01" title="Labs are raising the alarm">National laboratories cite sudden, simultaneous data center load loss as a potential danger to grid reliability.</Row>
        <Row n="02" title="It is getting worse">The July 2026 event was about 2.5 times the 2024 one, and AI data centers are being built faster than the grid can adapt.</Row>
        <Row n="03" title="Industry is building a fix">
          Companies are developing backup power and storage that connect the grid and the data center more smoothly, keeping a site’s draw
          steady through dips. ERCOT will require 90% of prior power back within 2 seconds from August 2026.
        </Row>
      </div>

      <div className="mt-16 grid gap-x-14 gap-y-10 border-t border-[#2b281f] pt-8 md:grid-cols-2">
        <div>
          <p className={`${label} text-[#e0713f]`}>The gap</p>
          <h3 className="mt-3 text-[24px] leading-[1.25] font-medium tracking-[-0.015em] text-[#ece6d6]">Nobody can prove a design will hold.</h3>
          <p className="mt-3 max-w-[460px] text-[14.5px] leading-[1.7] text-[#9a9380]">
            There is no certification system, so proof is done case by case: a handful of lab tests and simulations that can miss the rare
            combinations of conditions where things actually fail. The utility, the buyer and the financiers all have to trust a design on
            that basis.
          </p>
        </div>
        <div>
          <p className={`${label} text-[#d9b24c]`}>What fills it</p>
          <h3 className="mt-3 text-[24px] leading-[1.25] font-medium tracking-[-0.015em] text-[#ece6d6]">We hunt for the failures before they happen.</h3>
          <p className="mt-3 max-w-[460px] text-[14.5px] leading-[1.7] text-[#9a9380]">
            Our system searches the conditions a data center can face and reports the distinct ways a design fails, giving all three parties
            one shared, checkable answer to “will this design hold up when the grid dips?”
          </p>
          <button onClick={onNext} className={`${label} mt-6 cursor-pointer border border-[#d9b24c] px-4 py-2.5 text-[#e8d9ac] transition hover:bg-[#d9b24c] hover:text-[#120d02]`}>
            See how it works →
          </button>
        </div>
      </div>
    </section>
  )
}

export function OurSolution() {
  return (
    <Page
      kicker="Our solution"
      title="A tool that hunts for failures before they happen."
      lede="It does not check a design against a few test cases. It searches the whole space of conditions the world can throw at a data center and reports the distinct ways the design fails."
    >
      <Row n="01" title="Model the world">Probability distributions for dip depth and duration, repeated dips, AI load swings, temperature and battery charge level.</Row>
      <Row n="02" title="Model the hardware">Distributions for how real equipment varies from its datasheet: battery aging, response times and power supply trip thresholds.</Row>
      <Row n="03" title="Model how they depend on each other">A cold morning, a low battery and an AI load surge can arrive together. The model keeps that structure.</Row>
      <Row n="04" title="Run the physics, fast">Existing physics simulators are wrapped in a fast neural-network stand-in, so millions of scenarios can be checked.</Row>
      <Row n="05" title="Search for distinct failures">The search looks for different ways the design fails, not many copies of the same failure.</Row>
      <div className="mt-10 grid gap-x-14 gap-y-8 md:grid-cols-2">
        <Note title="No invented precision">Where there is only a manufacturer limit and no real data, the tool uses bounds, not made-up distributions.</Note>
        <Note title="What-ifs stay separate">“What if a setting was wrong” tests are kept apart from the probabilities, so they never blur the risk number.</Note>
      </div>
    </Page>
  )
}

export function Deliverables() {
  return (
    <Page
      kicker="Deliverables"
      title="One report a developer can act on and a utility can trust."
      lede="A developer of ride-through technology uses the tool during design, before building or shipping. They enter a reference data center and their design, and the tool shows how it fails and which fix is smallest."
    >
      <Row n="01" title="Pass probability">The probability that the design passes the grid rule, with an honest uncertainty band.</Row>
      <Row n="02" title="Failure modes">The worst cases found, grouped into distinct failure modes, each with an example scenario.</Row>
      <Row n="03" title="What matters most">Which factors drive the failures the most.</Row>
      <Row n="04" title="Smallest fix">For each failure mode, the smallest change that removes it, such as a bigger storage window or a changed setting.</Row>
      <Row n="05" title="Setting-mismatch checklist">A separate checklist of “what if a setting was wrong” cases, kept apart from the probability.</Row>
      <div className="mt-10 border-t border-[#1f1d17] pt-6">
        <p className="max-w-[640px] text-[15px] leading-[1.7] text-[#a29b86]">
          The same report goes to the people who approve and pay for the project: the utility, the data center owner and the financiers. All
          three get one shared, checkable answer to <span className="text-[#e8d9ac]">“will this design hold up when the grid dips?”</span> instead of
          a few lab tests and a promise.
        </p>
      </div>
    </Page>
  )
}
