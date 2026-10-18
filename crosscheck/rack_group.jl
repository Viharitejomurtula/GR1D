# Independent re-implementation (Julia, base language only, fixed-step) of one rack group and the grid voltage chain, written from the
# documented equations -- NOT translated from the Modelica source. Inputs: parameters (key=value file) and the cooling power / AI swing as
# functions of time (taken from the Modelica trace, because those subsystems are not what is being checked here).
# Usage: julia rack_group.jl params.txt inputs.csv out.csv
function readkv(path)
    d = Dict{String,Float64}()
    for l in eachline(path); isempty(strip(l)) && continue; k, v = split(l, '='); d[strip(k)] = parse(Float64, strip(v)); end
    d
end
P = readkv(ARGS[1])
rows = [parse.(Float64, split(l, ',')) for l in Iterators.drop(eachline(ARGS[2]), 1)]       # header skipped: t, p_cool, p_swing
ts = [r[1] for r in rows]; pc = [r[2] for r in rows]; psw = [r[3] for r in rows]
function interp(xs, ys, x)
    x <= xs[1] && return ys[1]; x >= xs[end] && return ys[end]
    i = searchsortedlast(xs, x); f = (x - xs[i]) / (xs[i+1] - xs[i]); ys[i] + f * (ys[i+1] - ys[i])
end
# constants (Advanced Energy ORv3 3 kW datasheet / OCP busbar levels)
RATED, UV, RESTART_V, HOLDUP_J, EFF, TON = 3000.0, 172.0, 178.0, 60.0, 0.965, 1.0
BUS, DROOP, TAKEOVER_V, TAKEOVER_DELAY, BBU_BUS, FLOOR_V = 50.75, 6.0, 48.5, 0.002, 48.0, 46.0
TAU_TRIP, TAU_SENSE = 0.001, 0.001
EBBU = 1 - (BUS - TAKEOVER_V) / DROOP
npsu = P["p_it"] / RATED; emax = npsu * HOLDUP_J
uvh, uvl = UV * (1 + P["spread"]), UV * (1 - P["spread"])
zeff = (P["pf"] + P["xr"] * sqrt(1 - P["pf"]^2)) / sqrt(1 + P["xr"]^2); z = zeff * P["ztot"] * P["chain"]
ndip = Int(P["ndip"]); ds = [P["dip_start$i"] for i in 1:ndip]; dd = [P["dip_dur$i"] for i in 1:ndip]; dp = [P["dip_depth$i"] for i in 1:ndip]
function vsource(t)
    last = 0
    for i in 1:ndip
        t >= ds[i] && t < ds[i] + dd[i] && return dp[i]
        t >= ds[i] + dd[i] && (last = i)
    end
    last == 0 && return 1.0
    dt = t - (ds[last] + dd[last]); tau = P["tau"]
    1 + (dp[last] - 1) * exp(-dt / tau) + P["os"] * (dt / (4tau)) * exp(1 - dt / (4tau))
end
dt = 1e-5; T = P["stop"]; nstep = Int(round(T / dt)); out_every = 100            # 1 ms output
open(ARGS[3], "w") do io
    vs_f = 1.0; trip = 0.0; tuv = 0.0; tdown = 0.0; e = emax; soc = P["soc0"]; tlow = 0.0; tbok = 0.0; tup = 1.0e3
    active = false; psu_en_prev = true; tlow_prev = 0.0; tbok_prev = 0.0
    println(io, "time,v_source,v_sdp,v_sense,trip,e_holdup,soc,p_psu,p_bbu,p_grid,bbu_active")
    for k in 0:nstep
        t = k * dt
        pcool = interp(ts, pc, t); swing = interp(ts, psw, t)
        online = (1 - P["faulted"]) + P["faulted"] * (1 - trip); psu_en = online > 0.5
        demand = P["workload"] * P["p_it"] + swing
        ramp = min(1.0, tup / max(P["ramp"], 1e-3))
        p_psu = min(demand, online * npsu * RATED) * ramp                          # no transfer in these scenarios
        short = max(0.0, demand - p_psu)
        p_bbu = (active && soc > 0) ? min(P["bbu_w"], short) : ((ramp < 1 && soc > 0 && psu_en) ? min(P["bbu_w"], max(0.0, demand - p_psu)) : 0.0)
        p_grid = p_psu / EFF + pcool
        vs = vsource(t); p = p_grid / P["ptot"]
        v = 0.5 * (vs * (1 + z) + sqrt(max(vs^2 * (1 + z)^2 - 4 * z * vs * p, 0.0)))
        if k % out_every == 0
            println(io, join([t, vs, v, vs_f, trip, e, soc, p_psu, p_bbu, p_grid, active ? 1 : 0], ","))
        end
        # ---- state update (explicit Euler, 10 us) ----
        efrac = clamp(e / emax, 0.0, 1.0)
        demand_trip = clamp((uvh - P["supply"] * vs_f) / (uvh - uvl), 0.0, 1.0)
        tuv = demand_trip > 0 ? tuv + dt : 0.0
        eff_demand = tuv > P["uvdelay"] + 1e-6 ? demand_trip : 0.0
        trip += dt * max(0.0, (eff_demand - trip) / TAU_TRIP)
        tdown = trip > 0.01 ? tdown + dt : 0.0
        if P["supply"] * vs_f > RESTART_V && tdown > TON + P["restart_delay"]; trip = 0.0; end
        vs_f += dt * (v - vs_f) / TAU_SENSE
        e += dt * ((psu_en && (p_psu + p_bbu >= demand - 1.0)) ? max(0.0, (emax - e) / 0.05) : (e > 1e-6 ? -(demand - p_psu - p_bbu) : max(0.0, -(demand - p_psu - p_bbu))))
        soc -= dt * p_bbu / P["bbu_j"]
        tlow = efrac < EBBU ? tlow + dt : 0.0
        tbok = (psu_en && short <= 1.0) ? tbok + dt : tbok
        !psu_en && (tbok = 0.0)
        was_active = active
        # edge-triggered like the documented latch: takeover when the low-bus timer crosses its delay, hand-back when the PSU-ok timer crosses its own
        if tlow > TAKEOVER_DELAY && tlow_prev <= TAKEOVER_DELAY; active = true; elseif tbok > P["handback"] && tbok_prev <= P["handback"]; active = false; end
        tlow_prev = tlow; tbok_prev = tbok
        tup = psu_en ? tup + dt : tup
        if (!psu_en && psu_en_prev) || (was_active && !active); tup = 0.0; end
        psu_en_prev = psu_en
    end
end
