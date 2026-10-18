import type { ReactNode } from 'react'

const label = 'mono text-[12px] font-medium tracking-[0.14em] uppercase'

type Tone = 'ok' | 'warn' | 'gap'
const TONE: Record<Tone, string> = { ok: '#7bc47f', warn: '#e0b341', gap: '#ff7a4d' }

function Chip({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span className="mono inline-block whitespace-nowrap text-[10.5px] font-medium tracking-[0.1em] uppercase" style={{ color: TONE[tone] }}>
      <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: TONE[tone] }} />
      {children}
    </span>
  )
}

const b = (t: string) => <strong className="font-semibold text-[#f1ecdc]">{t}</strong>

function Stage({ id, n, title, what, status, children }: { id: string; n: string; title: string; what: string; status: ReactNode; children: ReactNode }) {
  return (
    <section id={id} className="mt-32 scroll-mt-8">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 border-t border-[#d9b24c]/60 pt-6">
        <p className={`${label} text-[#d9b24c]`}>Stage {n}</p>
        {status}
      </div>
      <h2 className="display mt-3 max-w-[800px] text-[40px] leading-[1.05] font-semibold tracking-[-0.035em] text-[#f6f1e2]">{title}</h2>
      <p className="mt-4 max-w-[680px] text-[18px] leading-[1.55] text-[#d3ccb8]">{what}</p>
      <div className="mt-4 space-y-12">{children}</div>
    </section>
  )
}

function Sub({ title, tone, children }: { title: string; tone?: Tone; children: ReactNode }) {
  return (
    <div className="mt-10">
      <h3 className={`${label} text-[11.5px]`} style={{ color: tone ? TONE[tone] : '#f0c85a' }}>{title}</h3>
      <div className="mt-4 max-w-[780px] space-y-3 text-[15.5px] leading-[1.6] text-[#c4bca7]">{children}</div>
    </div>
  )
}

function List({ items, tone = 'gap' }: { items: ReactNode[]; tone?: Tone }) {
  return (
    <ul className="space-y-2.5">
      {items.map((t, i) => (
        <li key={i} className="grid grid-cols-[18px_1fr]"><span style={{ color: TONE[tone] }}>–</span><span>{t}</span></li>
      ))}
    </ul>
  )
}

function Table({ head, rows, cols }: { head: string[]; rows: ReactNode[][]; cols: string }) {
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[780px]">
        <div className="grid gap-x-6 border-b border-[#d9b24c]/60 pb-2" style={{ gridTemplateColumns: cols }}>
          {head.map((h) => <span key={h} className="mono text-[10.5px] font-medium tracking-[0.14em] text-[#8d8670] uppercase">{h}</span>)}
        </div>
        {rows.map((r, i) => (
          <div key={i} className="grid items-baseline gap-x-6 border-b border-white/10 py-3 text-[14.5px] leading-[1.5] text-[#d3ccb8]" style={{ gridTemplateColumns: cols }}>
            {r.map((c, j) => <div key={j}>{c}</div>)}
          </div>
        ))}
      </div>
    </div>
  )
}

const STAGES = [
  ['distributions', '01', 'Probability distributions'],
  ['network', '02', 'Bayesian network'],
  ['physics', '03', 'Physics simulator'],
  ['surrogate', '04', 'Neural surrogate'],
  ['hunting', '05', 'Failure hunting'],
]
const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

export default function Validation({ onBack }: { onBack: () => void }) {
  return (
    <div className="mx-auto max-w-[1000px] px-10 pt-16 pb-40">
      <button onClick={onBack} className={`${label} cursor-pointer text-[#8d8670] underline-offset-[7px] transition hover:text-white hover:underline`}>← Our solution</button>
      <p className={`${label} mt-12 text-[#d9b24c]`}>Validation / Testing</p>
      <h1 className="display mt-4 max-w-[860px] text-[52px] leading-[1.03] font-semibold tracking-[-0.04em] text-[#f6f1e2]">
        A simulation is only as good as what it is checked against.
      </h1>
      <p className="mt-6 max-w-[680px] text-[19px] leading-[1.55] text-[#d3ccb8]">
        Each stage of the pipeline is laid out the same way: what it is built from, what it was checked against, how sensitive it is, and what we could not pin down.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-8 gap-y-2">
        <Chip tone="ok">Matches</Chip><Chip tone="warn">Matches with a bias or caveat</Chip><Chip tone="gap">Gap or not yet done</Chip>
      </div>

      <nav className="mt-12 grid gap-px overflow-hidden border border-white/12 bg-white/12 sm:grid-cols-5">
        {STAGES.map(([id, n, t]) => (
          <button key={id} onClick={() => jump(id)} className="cursor-pointer bg-[#07070a] px-4 py-4 text-left transition hover:bg-[#14130f]">
            <span className="mono block text-[11px] text-[#d9b24c]">{n}</span>
            <span className="display mt-1 block text-[16px] font-medium text-[#f1ecdc]">{t}</span>
          </button>
        ))}
      </nav>

      {/* 01 */}
      <Stage id="distributions" n="01" title="Probability distributions"
        what="Every uncertain input (dip depth, dip duration, temperature, battery state, equipment variation) gets a range or a distribution with a stated source and a grade for how good that source is."
        status={<Chip tone="warn">Ranges sourced · most shapes assumed</Chip>}>
        <Sub title="How we derived them">
          <p>Each of the 22 inputs has a low, typical and high value tied to a source, graded as {b('6 measured')}, {b('6 datasheet proxies')} (a similar product’s datasheet),
            {b(' 8 assumed')} and {b('2 opinion')} (vendor articles). Where we have real events we fit them; where we have only a range we draw uniformly inside it rather than invent a shape.</p>
        </Sub>
        <Table cols="1.1fr 2fr 1.1fr"
          head={['Input', 'What we based it on', 'Grade']}
          rows={[
            ['Dip duration', 'ERCOT Large Load Events deck (Nov 2024): 16 of 18 events cleared in 3–4 cycles, 2 delayed 10–19 cycles. P(delayed) = 2/18, 95% interval 1.4–34.7%', <Chip key="1" tone="warn">Measured · 18 events</Chip>],
            ['Dip depth', 'Texas event retained voltages (0.305–0.844 pu) set the range. The sampler uses EPRI distribution-level sag bands (69% in 0.70–0.90 pu, 27% in 0.10–0.70, 4% below 0.10)', <Chip key="2" tone="warn">30-year-old bands</Chip>],
            ['Repeated dips', 'One Eastern Interconnection event: six dips in 82 s with gaps from 0.5 to 55 s', <Chip key="3" tone="gap">One non-Texas event</Chip>],
            ['Faulted phases', '1, 2 or 3 phases at 70.3 / 26.0 / 3.6%, from an ERCOT protection study table', <Chip key="4" tone="warn">Not re-checked against source</Chip>],
            ['Outdoor temperature', 'Every hour of Dallas–Fort Worth weather, 2021–2025, drawn directly', <Chip key="5" tone="ok">Measured</Chip>],
            ['AI load swing size', 'NREL/NLR GenAI Power Profiles, 2,246 measured runs: 0.47 training, 0.20 inference', <Chip key="6" tone="ok">Measured</Chip>],
            ['AI load swing frequency', 'One preprint gives a 0.2–3 Hz band; the same traces show no split by workload', <Chip key="7" tone="warn">Band only</Chip>],
            ['Site load', 'ERCOT forecast, LBNL and a Microsoft paper, range 0.2–0.97 of rated, typical 0.5', <Chip key="8" tone="warn">Assumed range</Chip>],
            ['Equipment hardware', 'Datasheets for a Vertiv UPS, a TDK capacitor, an SEL relay and an Advanced Energy power supply', <Chip key="9" tone="warn">Proxy products</Chip>],
          ]} />
        <Sub title="What we could not make exact distributions of" tone="gap">
          <p>For these we have a range or a single number, so the tool uses bounds and says so, instead of a made-up bell curve:</p>
          <List items={[
            <>{b('Battery hall temperature')}: no source gives the spread across sites, so it is uniform over the 18–27 °C recommended range.</>,
            <>{b('Equipment age')}: only whole-facility averages exist (mean 11.3 years), so it is uniform 0–15 years.</>,
            <>{b('Workload mix')} between training and inference: equal shares, swept from 10% to 90% as a check.</>,
            <>{b('Cooling split')} between compressors, fans and pumps, and the {b('state-of-charge error')} and {b('compressor trip point')}, which rest on vendor articles.</>,
            <>{b('Power supply input-current limit')}: not in any public datasheet.</>,
            <>{b('Dip depth for a data center specifically')}: the bands are distribution-level and decades old.</>,
          ]} />
        </Sub>
        <Sub title="Checked against">
          <p>14 automated tests check that sampled draws stay in the sourced ranges, that the delayed-clearing share and faulted-phase mix match their sources, that outdoor temperature matches the DFW data, and that
            the same seed gives the same scenarios.</p>
        </Sub>
        <Sub title="Sensitivity analysis">
          <p>A wiring check perturbs every scenario input in eight different contexts and confirms the simulation output changes. On its last run it found {b('two inputs (restart surge size and length) that changed nothing')} in any context. They are sampled but ignored by the physics, so no result depends on them yet.</p>
          <p>The hardest-to-source inputs are tagged for sensitivity analysis instead of more research, so the sweep, not a guess, decides how much each one matters.</p>
        </Sub>
      </Stage>

      {/* 02 */}
      <Stage id="network" n="02" title="Bayesian network"
        what="Links the inputs through shared drivers (temperature, site load, equipment age, workload) so the sampler draws realistic combinations rather than independent values."
        status={<Chip tone="warn">Method sound · links thinly evidenced</Chip>}>
        <Sub title="What it is built from">
          <List tone="ok" items={[
            <>{b('The method.')} Output covariance from input covariance and a sensitivity matrix, as in the JCGM 100 and 102 measurement-uncertainty standards (equations read from the source text). It has 28 nodes and 22 edges.</>,
            <>{b('The drivers.')} Dallas–Fort Worth hourly temperature and ERCOT load, 2021–2025, with a Gaussian copula fitted by season and 6-hour daypart.</>,
            <>{b('The factor links.')} 12 of 53 possible factor-to-driver links have evidence: 4 measured, 2 model defaults, 3 datasheet proxies, 3 assumed. The measured ones come from Sandia and Panasonic cell tests and the NREL AI power data.</>,
          ]} />
        </Sub>
        <Sub title="What it was validated against">
          <Table cols="1.4fr 1fr 1.2fr"
            head={['Check', 'Result', 'Verdict']}
            rows={[
              ['Temperature to load model, held-out 2026 hours (6,544 h)', 'R² 0.95 in fit; error 0.061 on held-out data', <Chip key="1" tone="ok">Matches</Chip>],
              ['Same load model vs ERCOT’s own load series', 'Correlation 0.972, R² 0.93', <Chip key="2" tone="ok">Matches</Chip>],
              ['Temperature 5–95% band, held-out 2026', 'Covers 86% of hours vs 90% target; September only 67%', <Chip key="3" tone="warn">Slightly narrow</Chip>],
              ['Linear covariance vs 100,000-draw Monte Carlo', '261 of 98,280 pairs differ by more than 0.1', <Chip key="4" tone="ok">Matches</Chip>],
              ['Sampler across machines', 'Found and fixed a bug that gave different draws on different machines', <Chip key="5" tone="ok">Fixed</Chip>],
            ]} />
          <p className="pt-2">9 network tests check that the graph is valid, draws are reproducible, root frequencies and table rules match their specification, and conditioning on evidence works.</p>
        </Sub>
        <Sub title="Sensitivity analysis we ran">
          <p>The covariance was recomputed across a grid of assumptions that we could not settle, {b('98,280 factor-pair results')} in all:</p>
          <List tone="ok" items={[
            'how much outdoor temperature reaches the battery room (none up to 28%),',
            'how strongly temperature and load are coupled (0, 0.5, 1),',
            'the spread of equipment age (2.5 vs 4.3 years), the size of noise, and the capacitor and power supply mappings,',
            'the workload mix from 10% to 90% training, where workload explains 14–38% of AI swing variance.',
          ]} />
          <p>Replacing a prior battery-resistance slope with our fitted one moved some correlations by up to 0.38 (resistance against capacity went from −0.77 to −0.98), so those links are sensitive to that one fit.</p>
        </Sub>
        <Sub title="What we could not pin down" tone="gap">
          <List items={[
            <>Five edges are structure only, with {b('no number behind them')}. The structure and parameters are set from literature; nothing is learned from data.</>,
            <>The battery-resistance slope rests on two temperatures (10 and 25 °C). Aging links rest on one paper’s model, not measured aging data.</>,
            <>Noise for 10 of the 13 factors with a noise term is simply a sixth of the range. Our own cell replicates suggest the spread is 5–10 times larger for resistance.</>,
            <>The standards back the arithmetic only. They do not say the sensitivity numbers are right, and no published work applies this to data center ride-through.</>,
            <>Datasets we tried and could not get or confirm (Sandia long-term aging, MATR, Bayreuth) are listed and not used.</>,
          ]} />
        </Sub>
      </Stage>

      {/* 03 */}
      <Stage id="physics" n="03" title="Physics simulator"
        what="An OpenModelica model of the converter, DC link, rack batteries, server power supplies, servers and cooling, graded on the same RMS voltage ERCOT’s rule uses."
        status={<Chip tone="warn">Matches real events with known biases</Chip>}>
        <Sub title="Checked against real Texas events">
          <p>Load loss for the two facilities is fitted with one parameter (the share of load behind legacy latching protection). Peak current and recovery are not fitted, so they are the evidence.</p>
        </Sub>
        <Table cols="1.5fr 1fr 0.8fr 0.8fr 1.2fr"
          head={['Real event', 'Outcome', 'Real', 'Model', 'Status']}
          rows={[
            ['Crypto facility A, 0.535 pu', 'Sustained load loss', '46%', '44.5%', <Chip key="a" tone="warn">Fitted</Chip>],
            ['', 'Peak current', '1.60 pu', '1.70 pu', <Chip key="a2" tone="ok">Not fitted · +6%</Chip>],
            ['Crypto facility B, 0.670 pu', 'Sustained load loss', '24%', '24.5%', <Chip key="b" tone="warn">Fitted</Chip>],
            ['', 'Peak current', '1.50 pu', '1.49 pu', <Chip key="b2" tone="ok">Not fitted · −1%</Chip>],
            ['Shallow dip, 0.844 pu', 'Load loss', '19%', '24.5%', <Chip key="c" tone="warn">Predicted · 5.5 pts high</Chip>],
            ['Vendor product, 70 sags', 'Median recovery', '0.41 s', '0.39 s', <Chip key="d" tone="ok">Predicted</Chip>],
            ['', 'Worst-case recovery', '0.49 s', '1.37 s', <Chip key="d2" tone="gap">Predicted · too slow</Chip>],
            ['', 'Never disconnected', 'Yes', 'Yes', <Chip key="d3" tone="ok">Predicted</Chip>],
          ]} />
        <p className="mono text-[11px] leading-[1.6] text-[#8d8670]">Sources: NERC crypto incident review (Jan 2026), NERC Large Load Loss review, ERCOT Large Load Events (Nov 2024), AionTracks ERCOT LLWG deck (Aug 2026). The two facilities come from one report, so they count once.</p>

        <Sub title="Checked against independent solvers">
          <p>Each sub-model was rebuilt in a separate tool and compared. These found real errors, which we kept instead of tuning away.</p>
        </Sub>
        <Table cols="1.2fr 1.1fr 2.2fr"
          head={['Sub-model', 'Checked with', 'Result']}
          rows={[
            ['Grid voltage in a dip', 'DPsim and a plain-Python solve, 36 cases', <span key="1"><Chip tone="gap">Model optimistic</Chip> The two references agree to 1.4×10⁻⁹ pu. The model’s dip voltage is too high by 0.04 pu on average and up to 0.165 pu, worst at 0.5–0.7 pu, where the ERCOT events sit.</span>],
            ['Power supply hold-up', 'ngspice circuit', <span key="2"><Chip tone="warn">Open</Chip> The 1/P hold-up law and the 20 ms datasheet point match. The default mode only agrees if the input can draw about 2× the datasheet current, which is not public.</span>],
            ['Battery cold derating', 'PyBaMM, three cell sets', <span key="3"><Chip tone="warn">Fine in range</Chip> Within about 7% for 18–35 °C. Below about 10 °C at the real discharge rate it is untested.</span>],
            ['Drive ride-through', 'Hand energy balance, in a test', <span key="4"><Chip tone="ok">Matches</Chip> Asserted to within 15%, with the inertia term added for kinetic buffering.</span>],
            ['Grid dip shapes', 'ANDES, IEEE 14-bus', <span key="5"><Chip tone="warn">Brackets events</Chip> Retained voltage 0.24–0.79 pu covers the real events. It is a textbook grid, not Texas.</span>],
            ['Voltage solution', 'Closed-form solve', <span key="6"><Chip tone="ok">Matches</Chip> Within 2×10⁻³ at four dip depths. Runs with a collapsed solution are marked invalid.</span>],
          ]} />

        <Sub title="Sensitivity analysis we ran">
          <List tone="ok" items={[
            <>{b('Power supply lockout delay')} swept 0 to 25 ms against both facilities. One cycle reproduces both, which is an inference from the data, not independent evidence.</>,
            <>{b('Leave-one-out.')} Predicting one facility from the other’s fit is off by up to 19.6 points. Facility B has a cliff: below a 25% legacy share the battery never hands back inside the window.</>,
            <>{b('Facility heterogeneity.')} One lumped group vs six groups with growing spread in loading, hold-up, battery size and trip point.</>,
            <>{b('Structural fixes switched on and off')} (chain loading, power supply capability) to see what each changes.</>,
          ]} />
          <p>82 automated tests cover the sampler, network, grader (multi-dip and the three-dips-in-a-minute rule) and physics.</p>
        </Sub>
        <Sub title="What we could not pin down" tone="gap">
          <List items={[
            'Validation rests on one NERC report, three Texas cases and one vendor benchmark.',
            'Voltage is optimistic (current too low) while the power supply mode makes current too high, so the two errors may be offsetting in a fitted debounce.',
            'The vendor’s worst-case recovery is much faster than ours. A likely cause is that our dips include deep sags the vendor would not test, which is unverified.',
            'Cold-hall battery behaviour at real rates, aging, unbalanced and single-phase faults, reactive power and generator transfer are untested or out of scope.',
          ]} />
        </Sub>
      </Stage>

      {/* 04 */}
      <Stage id="surrogate" n="04" title="Neural surrogate"
        what="An ensemble of small neural networks that learns to imitate the simulator in milliseconds, predicting pass or fail, how close a case is to the edge, and which failure mode."
        status={<Chip tone="gap">Accuracy figures not yet recorded</Chip>}>
        <Sub title="What it is built from">
          <p>It is trained on 2,000 simulator runs drawn by the scenario sampler. Three outputs: pass probability, a smooth recovery margin (which trains better near the edge than pass/fail alone) and the failure mode out of eight.
            The weights export to a file the browser evaluates directly.</p>
        </Sub>
        <Sub title="How it is checked">
          <List tone="ok" items={[
            <>{b('Held-out runs.')} Each member is scored on simulator runs it never trained on: pass accuracy, margin error and failure-mode accuracy.</>,
            <>{b('Edge accuracy.')} The headline number is accuracy on cases where the ensemble is undecided (pass probability between 25% and 75%), because easy passes and easy failures flatter any model.</>,
            <>{b('Self-reported uncertainty.')} Where members disagree, the surrogate flags a guess, and those cases are sent back to the simulator.</>,
            <>{b('Nothing reported unconfirmed.')} Every failure it predicts is re-run in the physics simulator, and only confirmed ones reach a report.</>,
          ]} />
        </Sub>
        <Sub title="What we could not pin down" tone="gap">
          <List items={[
            <>{b('The held-out accuracy and edge accuracy have not been recorded yet.')} We will not quote numbers until a trained run produces them.</>,
            'The speed gain over the simulator has not been benchmarked here.',
            'A surrogate reproduces whatever it was trained on, bugs included, so every gap in stage 03 carries through. It must be retrained after any simulator change.',
            'Behaviour outside the sampled ranges is not tested.',
          ]} />
        </Sub>
      </Stage>

      {/* 05 */}
      <Stage id="hunting" n="05" title="Failure hunting"
        what="Run millions of realistic scenarios through the surrogate, keep the predicted failures, group them into distinct ways a design fails, and confirm each in the simulator."
        status={<Chip tone="gap">Designed · not yet built or validated</Chip>}>
        <Sub title="What it is built on">
          <p>Scenarios come from the sampler and the Bayesian network, so likely combinations are searched more than impossible ones. The surrogate screens them, and the simulator confirms.
            The Results tab currently shows illustrative values for this stage, not real output.</p>
        </Sub>
        <Sub title="How we plan to validate it" tone="warn">
          <List tone="warn" items={[
            <>{b('Recall.')} On a small region of scenarios, run every case through the simulator and check the hunt finds the failures that brute force finds.</>,
            <>{b('Known failures.')} Check it rediscovers facility A and B’s failures from the real Texas events without being told.</>,
            <>{b('Confirmation rate.')} What share of predicted failures the simulator confirms.</>,
            <>{b('Distinctness.')} That the failures it reports are different mechanisms, not near-copies.</>,
            <>{b('Stability.')} Whether the failure probability and factor ranking hold up across different random seeds.</>,
          ]} />
        </Sub>
        <Sub title="What we could not pin down" tone="gap">
          <List items={[
            'None of the five checks above has been run, so we make no claim about how complete the search is.',
            'Factor importance, smallest fix and what-if analysis depend on this stage and are not built.',
            'Its results are only as good as stages 01 to 04, and every gap above is inherited.',
          ]} />
        </Sub>
      </Stage>
    </div>
  )
}
