# AI load swing magnitude and speed (Factor #1) — evidence and limitations

Source: NLR GenAI power profiles (F1b, CC BY 4.0), measured, 0.2 s resolution, 4 GPUs/node. All values below are OBSERVED, not assumed.

## Distributions (empirical; models/ai_load_swing_params.json, models/ai_inference_swing_params.json)
- Training (41 runs, 2-16 nodes; Llama2-70B LoRA, Stable Diffusion): per-node power ~0.5-1 kW low state, ~3 kW high state.
  Max ramp ~2.4 kW/s per node at 0.2 s; 5 s swings cluster at 0.5-0.8 kW (Llama2) or 2.0-2.2 kW (Stable Diffusion); capped at ~2.5 kW/node (idle-to-peak).
- Inference (Llama3-70B, 1 node, 1628 runs): load-dependent.
  Online, steady request rates: 99th pct 1 s ramp 2-8 W/s per node (near-flat, ~2.1-2.8 kW).
  Online finite/bursty and offline batch runs: 99th pct 1 s ramp 0.6-1.2 kW/s, max 0.8-1.5 kW per 0.2 s.

## Node synchronization (measured, data/processed/nlr_node_sync.csv)
Across all 40 multi-node training jobs (2-16 nodes) the node-level 1 s power differences are almost perfectly correlated
(median pairwise corr 0.97-0.98, min 0.91) with best lag 0.0 s (resolution 0.2 s). The aggregate/sum-of-nodes variability ratio
is 0.99 versus 1/sqrt(N) = 0.25 (16 nodes) if nodes were independent. Training nodes within one job swing in lockstep, so
per-job aggregate swing scales linearly with node count.

## Limitations
- Research cluster, benchmark jobs (MLPerf-style training, vLLM benchmark traffic); not a production job mix.
- Sync test covers GPU power only, jobs up to 16 nodes; clock alignment across nodes assumed (NTP); 0.2 s resolution.
- Scaling beyond 16 nodes (thousands of GPUs, multiple jobs, checkpoint stalls, failures) is an extrapolation and needs explicit assumptions.
- Only the training sync test was done; inference is single-node.
- Whole-facility profiles in the dataset (03_whole-facility_profiles) are simulated (DIPLOEE) and were not used.
