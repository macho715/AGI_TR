#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checklist Generator (P0-2)
Generates field operations checklist.
"""

from datetime import datetime
from typing import List


def generate_checklist(
    sequence: List,
    profile,
    output_path: str = "BALLAST_OPERATIONS_CHECKLIST.md",
) -> str:
    """
    Generate field operations checklist (Markdown format).

    Args:
        sequence: List of BallastStep objects
        profile: SiteProfile with SSOT parameters
        output_path: Output file path

    Returns:
        Markdown string for checklist
    """
    # Calculate totals
    import math
    total_time_h = sum((s.time_h if s.time_h is not None and not (isinstance(s.time_h, float) and math.isnan(s.time_h)) else 0.0) for s in sequence)
    if total_time_h is None or (isinstance(total_time_h, float) and math.isnan(total_time_h)):
        total_time_h = 0.0
    hold_points = [s for s in sequence if s.hold_point]

    # Get SSOT parameters
    ballast_params = profile.ballast_params if profile else {}
    default_scenario = ballast_params.get("default_scenario", "A")
    contingency = ballast_params.get("contingency", {})
    scenario_config = contingency.get(default_scenario, {})
    pump_rate = scenario_config.get("pump_rate_tph", 10.0)

    daylight_only = ballast_params.get("daylight_only", True)
    daylight_start = ballast_params.get("daylight_start", "06:00")
    daylight_end = ballast_params.get("daylight_end", "18:00")

    gates = profile.data.get("gates", []) if profile else []
    # Get gate limits
    fwd_max = next(
        (g.get("limit_value") for g in gates if g.get("gate_id") == "FWD_MAX_2p70_critical_only"),
        2.70,
    )
    aft_min = next(
        (g.get("limit_value") for g in gates if g.get("gate_id") == "AFT_MIN_2p70_propulsion"),
        2.70,
    )

    checklist = f"""# BALLAST OPERATIONS CHECKLIST
## AGI Site - RoRo Operations Field Guide

**Document:** BALLAST-OPS-CHECKLIST-AGI-v1.0
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**SSOT Version:** AGI Site Profile COMPLETE v1.0

---

## EXECUTIVE SUMMARY

**Total Duration:** {total_time_h:.1f} hours
**Hold Points:** {len(hold_points)}
**Pump Scenario:** {default_scenario} ({pump_rate} t/h)
**Daylight Only:** {'YES' if daylight_only else 'NO'} ({daylight_start}-{daylight_end})
**Critical Gates:** FWD <= {fwd_max}m (critical stages), AFT >= {aft_min}m (all stages)

---

## SECTION 1: PRE-START VERIFICATION (Complete ALL before operations)

### 1.1 Pump System Verification
- [ ] **Pump Test:** Completed within 24 hours (Record #: ________)
- [ ] **Pump Scenario:** Confirmed as **{default_scenario}** ({pump_rate} t/h)
- [ ] **Backup Pump:** Available and tested (if scenario requires)
- [ ] **Pump Log:** Reviewed for recent maintenance/issues
- [ ] **Flow Rate:** Field-verified at {pump_rate} t/h +/-5%
- [ ] **Vent System:** All tank vents clear and functional

**Cougar Ace Lesson:** Pump capacity MUST be field-verified, not assumed from specs.

### 1.2 Valve Lineup Verification
- [ ] **Valve Drawing:** Current revision confirmed with ship's records
- [ ] **Physical Inspection:** All valve positions match drawing 100%
- [ ] **VOID3 Verification:** Confirmed as **PRE-BALLAST STORAGE ONLY** (no transfer valves)
- [ ] **Emergency Valves:** Positions identified and tested
- [ ] **Valve Labels:** All clearly visible and correct
- [ ] **Remote Operation:** Bridge/pump room valve controls tested

**Hoegh Osaka Lesson:** Valve errors can cause catastrophic stability loss.

### 1.3 Draft Measurement System
- [ ] **Draft Marks:** FWD, AFT, MID visible and readable
- [ ] **Tolerance:** Set to **+/-2 cm** (normal), **+/-4 cm** (critical stop)
- [ ] **Calculation Method:** Confirmed as **Method B** (AGENTS.md Lpp/LCF-based)
- [ ] **Instruments:** Laser/mechanical draft gauge calibrated
- [ ] **Backup Method:** Manual marks + calculation sheet prepared
- [ ] **Trim Calculation:** Formula verified and calculator ready

### 1.4 Communication Systems
- [ ] **Bridge-Pump Room:** VHF/intercom tested
- [ ] **Pump Room-Deck:** Portable radio tested
- [ ] **Deck-SPMT:** Comms with cargo team established
- [ ] **Emergency Freq:** Monitored and tested
- [ ] **Call Signs:** Distributed to all personnel
- [ ] **Backup Comms:** Mobile phones with signal verified

### 1.5 Environmental Limits (SSOT)
- [ ] **Wind Speed:** Current ______ kt (Limit: 15 kt)
- [ ] **Wave Height:** Current ______ m (Limit: 1.5 m)
- [ ] **Visibility:** Good (>= 1 NM)
- [ ] **Daylight:** Operations within {daylight_start}-{daylight_end} window
- [ ] **Weather Forecast:** Next {int(total_time_h) + 2 if total_time_h is not None and not (isinstance(total_time_h, float) and math.isnan(total_time_h)) else 2} hours reviewed
- [ ] **Abort Criteria:** Briefed to all personnel

### 1.6 Documentation Preparation
- [ ] **BWRB:** Ballast Water Record Book ready
- [ ] **Hold Point Forms:** {len(hold_points)} forms printed and numbered
- [ ] **Sequence Sheet:** BALLAST_SEQUENCE printed and distributed
- [ ] **Emergency Procedures:** Posted in pump room and bridge
- [ ] **Camera/GPS:** Ready for timestamped evidence collection

### 1.7 Safety Equipment
- [ ] **PPE:** All personnel equipped (hard hat, safety shoes, life jacket)
- [ ] **Firefighting:** Equipment checked and accessible
- [ ] **First Aid:** Kit available and personnel briefed
- [ ] **Evacuation Routes:** Clear and marked
- [ ] **Emergency Stops:** All emergency stop buttons tested

### 1.8 Personnel Briefing
- [ ] **Roles:** Master, Chief Officer, Pump Room, Deck Officer assigned
- [ ] **Sequence:** All personnel understand step-by-step plan
- [ ] **Hold Points:** Criteria and procedures briefed
- [ ] **Emergency:** Abort criteria and procedures briefed
- [ ] **Sign-off:** All personnel signatures obtained

**MASTER'S APPROVAL:**
- [ ] All pre-start checks completed and satisfactory
- Signature: ___________________  Time: __________

---

## SECTION 2: DURING OPERATIONS

### 2.1 Hold Point Protocol
**Total Hold Points:** {len(hold_points)}

**For EACH Hold Point:**
1. **STOP** all ballast operations
2. **MEASURE** drafts (FWD, AFT, MID) with 2-person verification
3. **CALCULATE** trim using Method B
4. **COMPARE** with predicted values
5. **RECORD** deviations on hold point form
6. **DECIDE** using criteria:
   - Deviation <= 2 cm: **GO** (green light)
   - Deviation 2-4 cm: **RECALCULATE** remaining sequence (yellow light)
   - Deviation > 4 cm: **NO-GO** - STOP and investigate (red light)
7. **SIGN-OFF** by Master/Chief Officer (both signatures required)
8. **LOG** decision in BWRB
9. **COMMUNICATE** decision to all teams
10. **PROCEED** only after explicit GO authorization

### 2.2 Continuous Monitoring (Every 15 Minutes)
- [ ] Draft changes logged
- [ ] Pump operation status confirmed
- [ ] Tank levels checked (where accessible)
- [ ] Ramp angle <= 6.0 deg (SSOT limit)
- [ ] UKC maintained >= 0.5 m at all times
- [ ] Trim within +/-2.4 m envelope
- [ ] Environmental conditions recorded

### 2.3 Emergency Stop Criteria (IMMEDIATE STOP if any)
- [ ] Wind > 15 knots
- [ ] Wave height > 1.5 m
- [ ] Pump failure or abnormal noise
- [ ] Unexpected draft deviation > 4 cm
- [ ] Ramp angle exceeds 6.0 deg
- [ ] UKC < 0.5 m
- [ ] Trim exceeds +/-2.4 m
- [ ] Communication loss
- [ ] Any safety concern raised by any personnel
- [ ] Master's discretion

**EMERGENCY STOP PROCEDURE:**
1. Sound alarm (3 short blasts)
2. Close all ballast valves immediately
3. Stop all pumps
4. Verify all operations ceased
5. Notify Master and all teams
6. Investigate root cause before resuming

---

## SECTION 3: POST-OPERATIONS

### 3.1 Documentation Completion
- [ ] **BWRB:** All entries completed with signatures
- [ ] **Hold Point Forms:** All {len(hold_points)} forms signed and filed
- [ ] **Final Drafts:** FWD ______ m, AFT ______ m, TRIM ______ cm
- [ ] **Pump Log:** Total time ______ h, Total volume ______ t
- [ ] **Deviations:** All documented with root cause analysis
- [ ] **Photos:** Timestamped with GPS coordinates uploaded

### 3.2 Equipment Status
- [ ] **Pumps:** Secured and logged
- [ ] **Valves:** All in closed/safe position
- [ ] **Tanks:** Final levels recorded
- [ ] **Vents:** All open and clear
- [ ] **Bilges:** Checked and dry

### 3.3 Reporting
- [ ] **Master's Report:** Operations summary submitted
- [ ] **Chief Officer Report:** Tank status and stability confirmed
- [ ] **Lessons Learned:** Any issues/improvements documented
- [ ] **Next Operations:** Briefing scheduled

### 3.4 Handover
- [ ] **Tank Status:** Updated in ballast management system
- [ ] **Valve Positions:** Logged and verified
- [ ] **System Ready:** For next operations or departure
- [ ] **Watch Handover:** Next duty officer briefed

---

## SECTION 4: HOLD POINT DETAILS

"""

    # Add hold point table
    for i, hp in enumerate(hold_points, 1):
        checklist += f"""
### Hold Point {i}: {hp.stage} - Step {hp.step}

**Tank:** {hp.tank}
**Action:** {hp.action} ({hp.delta_t:+.1f} t)
**Pump Time:** {hp.time_h:.1f} hours

**PREDICTED VALUES:**
- FWD Draft: {hp.draft_fwd:.3f} m
- AFT Draft: {hp.draft_aft:.3f} m
- Trim: {hp.trim:.1f} cm
- UKC: {hp.ukc:.2f} m

**MEASURED VALUES:**
- FWD Draft: __________ m (Deviation: __________ cm)
- AFT Draft: __________ m (Deviation: __________ cm)
- Trim: __________ cm (Deviation: __________ cm)
- UKC: __________ m

**DECISION:**
- [ ] GO (<=2cm deviation)
- [ ] RECALCULATE (2-4cm deviation)
- [ ] NO-GO (>4cm deviation)

**SIGN-OFF:**
- Master: _____________________  Time: __________
- Chief Officer: _______________  Time: __________

**NOTES:**
____________________________________________________________
____________________________________________________________

---
"""

    checklist += f"""
## SECTION 5: LESSONS FROM MARINE CASUALTIES

### Cougar Ace (2006) - Ballast System Failure
**What Happened:** Ballast water transfer caused severe list during car carrier voyage
**Root Causes:**
- Pump capacity assumptions not field-verified
- Valve lineup errors not detected
- Real-time monitoring insufficient

**Our Mitigations:**
- Pump test within 24h with actual flow rate verification
- 100% valve lineup physical inspection
- {len(hold_points)} hold points with +/-2cm tolerance
- Continuous 15-minute monitoring

### Hoegh Osaka (2015) - Stability Loss During Departure
**What Happened:** RoRo vessel grounded due to stability/ballast issues
**Root Causes:**
- Ballast plan vs actual execution mismatch
- Tank operability constraints not enforced system-wide
- Insufficient hold point verification

**Our Mitigations:**
- VOID3 PRE-BALLAST ONLY enforced (no transfer operations)
- Tank operability validated pre-operation
- Step-by-step sequence with mandatory hold points
- Go/No-Go criteria with Master sign-off

---

## SECTION 6: SIGN-OFF

**I CERTIFY THAT:**
1. All pre-start checks have been completed satisfactorily
2. All personnel have been briefed and understand their roles
3. All environmental limits are within acceptable range
4. All safety equipment is functional and accessible
5. I have reviewed the ballast sequence and hold point criteria
6. I authorize the commencement of ballast operations

**MASTER'S FINAL AUTHORIZATION:**

Name: _________________________
Signature: ____________________
Date/Time: ____________________
Vessel Position: _______________

**CHIEF OFFICER CONCURRENCE:**

Name: _________________________
Signature: ____________________
Date/Time: ____________________

---

**END OF CHECKLIST**

**Generated by:** Ballast Pipeline SSOT System v1.0
**Based on:** AGENTS.md SSOT + IMO Guidelines + Casualty Lessons
**Next Review:** After operations completion or any incident

================================================================================
"""

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(checklist)

    print(f"[OK] Checklist generated: {output_path}")

    return checklist


if __name__ == "__main__":
    print("Checklist Generator - P0-2")
    print("Generates field operations checklist from ballast sequence")
