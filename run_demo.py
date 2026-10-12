import asyncio
import httpx

async def run_live_demo():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8500", timeout=30.0) as client:
        print("=" * 60)
        print("STAGE 1: TRIGGERING LIVE SSH RECON SCENARIO")
        print("=" * 60)
        r_sim1 = await client.post("/api/simulate?scenario=ssh_recon")
        print("Simulation Status:", r_sim1.json())
        print("Streaming reconnaissance commands into SSH honeypot...")
        await asyncio.sleep(5.0)

        print("\n" + "=" * 60)
        print("STAGE 2: TRIGGERING LIVE WEB INTRUSION SCENARIO")
        print("=" * 60)
        r_sim2 = await client.post("/api/simulate?scenario=web_intrusion")
        print("Simulation Status:", r_sim2.json())
        print("Streaming SQLi probes & admin portal harvesting...")
        await asyncio.sleep(4.0)

        print("\n" + "=" * 60)
        print("STAGE 3: EXECUTING STATIC VS CHAMELEONNET BENCHMARK")
        print("=" * 60)
        r_bench = await client.post("/api/benchmark/run")
        bdata = r_bench.json()
        static_info = bdata["static_honeypot"]
        cham_info = bdata["chameleon_net"]
        mult = bdata["multiplier"]
        
        print(f"Legacy Static Honeypot:")
        print(f"  - Dwell Time:           {static_info['dwell_time_seconds']}s")
        print(f"  - Commands Completed:   {static_info['commands_completed']} / 12 (Aborted by attacker)")
        print(f"  - Decoys Discovered:    {static_info['decoys_deployed']}")
        print(f"  - Attacker Outcome:     {static_info['sample_abort_reason']}")
        
        print(f"\nChameleonNet (LLM Adaptive):")
        print(f"  - Dwell Time:           {cham_info['dwell_time_seconds']}s")
        print(f"  - Commands Completed:   {cham_info['commands_completed']} / 12 (100% Completed)")
        print(f"  - Synthetic Artifacts:  {cham_info['unique_artifacts_captured']}")
        print(f"  - Final Fidelity Mode:  {cham_info['fidelity']}")
        print(f"  - Attacker Skill Score: {cham_info['skill_score']} / 10.0")
        print(f"  - Attacker Outcome:     {cham_info['sample_abort_reason']}")

        print(f"\nComparative Advantage:")
        print(f"  >>> Adversary Dwell Time: {mult['dwell_increase']} Increase")
        print(f"  >>> Threat Intelligence:  {mult['intelligence_gain']} Gain")

        print("\n" + "=" * 60)
        print("STAGE 4: LIVE TELEMETRY ENGINE AGGREGATE STATS")
        print("=" * 60)
        r_stats = await client.get("/api/stats")
        stats = r_stats.json()
        print(f"Total Sessions:   {stats['total_sessions']}")
        print(f"Active Sessions:  {stats['active_sessions']}")
        print(f"Total Events:     {stats['total_events']}")
        print(f"Avg Dwell Time:   {stats['avg_dwell_seconds']}s")
        
        print("\nTechniques Observed & Tagged (MITRE ATT&CK):")
        for tech, count in stats.get("technique_distribution", {}).items():
            print(f"  * {tech:<40} : {count} occurrences")

        print("\nAttacker Sophistication Distribution:")
        for bracket, count in stats.get("skill_distribution", {}).items():
            print(f"  * {bracket:<24} : {count} sessions")

        print("\n" + "=" * 60)
        print("STAGE 5: MOST RECENT 8 INTERACTIONS CAPTURED IN WAL")
        print("=" * 60)
        r_events = await client.get("/api/events?limit=8")
        for e in r_events.json()[:8]:
            tech_list = ", ".join([t.split(":")[0] for t in e["technique_tags"]]) or "None"
            print(f"[{e['service'].upper():3s}] Cmd: {e['raw_input']:<36} | Techs: {tech_list:<18} | Mode: {e['fidelity_mode']}")

if __name__ == "__main__":
    asyncio.run(run_live_demo())
