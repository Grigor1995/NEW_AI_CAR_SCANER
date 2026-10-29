from __future__ import annotations
import re
from .models import DiagnosticSession, Hypothesis, DiagnosticTest, SessionState


class DiagnosticReasoningEngine:
    """Context-aware deterministic diagnostic reasoning.

    This layer intentionally does not declare a failed component as confirmed. It
    classifies the current evidence into diagnostic categories and creates a
    scenario-specific hypothesis set. LLMs can later explain/orchestrate the
    result, but they do not replace these deterministic facts.
    """

    def analyze(self, session: DiagnosticSession) -> DiagnosticSession:
        facts = [e.fact.lower() for e in session.evidence]
        text = " ".join(facts)
        dtcs = {d.code.upper() for d in session.dtcs}

        categories: list[tuple[str, str]] = []
        self._add_dtc_categories(dtcs, categories)
        self._add_symptom_categories(text, categories)
        self._add_context_categories(text, categories)

        # For a fuel-mode-specific misfire, keep the hypothesis set focused on
        # the four diagnostic domains used by the LPG misfire golden case.
        vehicle_fuel = {str(f).strip().lower() for f in (session.vehicle.fuel if session.vehicle else [])}
        dual_fuel_lpg = "lpg" in vehicle_fuel and "petrol" in vehicle_fuel
        has_misfire_dtc = any(re.fullmatch(r"P03\d{2}", code) for code in dtcs)
        fuel_mode_specific = (
            "petrol normal" in text
            or "normal on petrol" in text
            or "smoothly on petrol" in text
            or "significantly reduces" in text
            or "petrol_normal" in text
            or "lpg_only" in text
        )
        # The symptom may be edited/deleted after it was initially reported.
        # Vehicle fuel configuration + a P03xx DTC still identifies the
        # LPG misfire golden-case domain.
        lpg_misfire = (
            (
                "lpg" in text
                and any(x in text for x in ("misfire", "shak", "jerk"))
                and has_misfire_dtc
                and fuel_mode_specific
            )
            or (dual_fuel_lpg and has_misfire_dtc and ("lpg" in text or not session.symptoms))
        )
        if lpg_misfire:
            focused = {
                "ignition / combustion",
                "LPG fuel delivery / mixture",
                "air-fuel / intake",
                "mechanical cylinder condition",
            }
            categories = [item for item in categories if item[0] in focused]
            statements = {
                "ignition / combustion": "A marginal ignition system can misfire under the higher demand associated with LPG/load; confirm with cylinder-specific evidence.",
                "LPG fuel delivery / mixture": "The fault is strongly associated with LPG operation; verify LPG pressure, injector delivery, and mixture/calibration before condemning ignition hardware.",
                "air-fuel / intake": "An air-fuel or intake imbalance can become more visible under LPG load; verify trims, airflow, and intake integrity.",
                "mechanical cylinder condition": "A cylinder-specific misfire remains mechanically possible; verify compression, leak-down, and timing evidence before ruling it out.",
            }
            categories = [(cat, statements[cat]) for cat in (
                "LPG fuel delivery / mixture",
                "ignition / combustion",
                "air-fuel / intake",
                "mechanical cylinder condition",
            )]
            # Compatibility aliases for older reasoning/decision consumers.
            categories.extend([
                ("LPG fuel delivery", statements["LPG fuel delivery / mixture"]),
                ("LPG injection", statements["LPG fuel delivery / mixture"]),
                ("ignition under LPG load", statements["ignition / combustion"]),
                ("ignition", statements["ignition / combustion"]),
                ("intake", statements["air-fuel / intake"]),
            ])

        # Preserve order while removing duplicates.
        seen: set[str] = set()
        unique: list[tuple[str, str]] = []
        for category, statement in categories:
            if category not in seen:
                seen.add(category)
                unique.append((category, statement))

        session.hypotheses = [
            Hypothesis(
                category=category,
                statement=statement,
                supporting_evidence_ids=self._supporting_evidence_ids(category, session),
                contradicting_evidence_ids=self._contradicting_evidence_ids(category, session),
            )
            for category, statement in unique
        ]
        return self._recommend(session, text, dtcs)

    @staticmethod
    def _supporting_evidence_ids(category: str, session: DiagnosticSession) -> list:
        category = category.lower()
        hints = {
            "ignition / combustion": ("misfire", "spark", "coil", "ignition", "p03"),
            "air-fuel / intake": ("air", "fuel", "trim", "intake", "mixture", "misfire"),
            "mechanical cylinder condition": ("compression", "leak-down", "leakdown", "mechanical", "misfire", "p03"),
            "lpg fuel delivery / mixture": ("lpg", "gas pressure", "injector", "mixture", "trim"),
            "lpg fuel delivery": ("lpg", "gas pressure", "injector"),
            "lpg injection": ("lpg", "injector"),
            "ignition under lpg load": ("lpg", "misfire", "load", "acceleration"),
            "ignition": ("spark", "coil", "ignition", "misfire", "p03"),
            "intake": ("intake", "air leak", "vacuum", "misfire"),
            "load-dependent behavior": ("load", "acceleration", "rpm"),
            "load-dependent combustion": ("load", "acceleration", "misfire", "rpm"),
            "idle stability / air-fuel control": ("idle", "trim", "maf", "map", "misfire"),
            "oil / combustion condition": ("smoke", "oil", "combustion"),
            "lean mixture": ("lean", "trim", "p0171", "p0174", "air leak"),
            "rich mixture": ("rich", "trim", "p0172", "p0175", "injector"),
            "air metering / maf": ("maf", "airflow", "p010"),
            "coolant temperature sensing": ("coolant", "temperature", "ect", "p011"),
            "oxygen sensor / fuel feedback": ("oxygen", "o2", "lambda", "p013", "p014", "p015", "p016"),
            "catalyst efficiency": ("catalyst", "p0420", "p0430"),
            "cam/crank correlation": ("timing", "cam", "crank", "p0016", "p0017", "p0018", "p0019"),
            "transmission control / gear ratio": ("transmission", "gear", "slip", "p073"),
            "power supply / voltage": ("battery", "voltage", "charging", "p056"),
            "vehicle network communication": ("can", "communication", "gateway", "u010", "u012"),
            "starting system / engine start": ("start", "crank", "authorization", "battery"),
            "engine stalling": ("stall", "stalls", "dies", "rpm"),
            "cooling system": ("overheat", "overheating", "coolant", "fan", "temperature"),
            "electrical power supply": ("electrical", "battery", "voltage", "charging"),
        }
        terms = hints.get(category, tuple(x for x in re.split(r"[/ ]+", category) if len(x) > 3))
        return [e.id for e in session.evidence if any(term in e.fact.lower() for term in terms)]

    @staticmethod
    def _contradicting_evidence_ids(category: str, session: DiagnosticSession) -> list:
        category = category.lower()
        contradiction_terms = {
            "mechanical cylinder condition": ("compression normal", "leak-down normal", "leakdown normal", "mechanical normal"),
            "ignition / combustion": ("spark normal", "coil normal", "ignition normal"),
            "ignition under lpg load": ("spark normal", "coil normal", "ignition normal"),
            "ignition": ("spark normal", "coil normal", "ignition normal"),
            "intake": ("no leak", "intake normal", "vacuum normal"),
            "lean mixture": ("trim normal", "mixture normal", "no leak"),
            "rich mixture": ("trim normal", "mixture normal"),
            "air metering / maf": ("maf normal", "airflow normal"),
            "coolant temperature sensing": ("temperature normal", "ect normal"),
            "oxygen sensor / fuel feedback": ("o2 normal", "lambda normal"),
            "catalyst efficiency": ("catalyst normal"),
            "cam/crank correlation": ("timing normal", "correlation normal"),
            "transmission control / gear ratio": ("slip normal", "gear normal", "transmission normal"),
            "power supply / voltage": ("voltage normal", "battery normal", "charging normal"),
            "vehicle network communication": ("can normal", "communication normal", "network normal"),
            "cooling system": ("temperature normal", "fan works normally"),
            "electrical power supply": ("voltage normal", "battery normal", "charging normal"),
        }
        terms = contradiction_terms.get(category, ())
        return [e.id for e in session.evidence if any(term in e.fact.lower() for term in terms)]

    @staticmethod
    def _add_dtc_categories(dtcs: set[str], categories: list[tuple[str, str]]) -> None:
        for code in sorted(dtcs):
            if re.fullmatch(r"P03\d{2}", code):
                categories.append(("ignition / combustion", f"The {code} family indicates a cylinder-specific misfire/combustion issue; determine whether it follows fuel mode, load, or cylinder."))
                categories.append(("air-fuel / intake", f"A misfire can result from an air-fuel or intake imbalance; verify mixture, airflow, and related evidence before concluding component failure."))
                categories.append(("mechanical cylinder condition", f"A cylinder-specific misfire can have a mechanical cause; verify compression, leak-down, and valve/timing evidence before ruling this domain out."))
            elif code in {"P0171", "P0174"}:
                categories.append(("lean mixture", f"{code} indicates a lean condition; separate air leak, fuel delivery, and sensor/model causes."))
            elif code in {"P0172", "P0175"}:
                categories.append(("rich mixture", f"{code} indicates a rich condition; separate excess fuel from incorrect airflow/lambda feedback."))
            elif code in {"P0100", "P0101", "P0102", "P0103", "P0104"}:
                categories.append(("air metering / MAF", f"{code} points to the air-metering signal/system; verify signal plausibility, wiring, and unmetered air."))
            elif code in {"P0115", "P0116", "P0117", "P0118", "P0119"}:
                categories.append(("coolant temperature sensing", f"{code} points to coolant-temperature sensing/rationality; compare cold-start and warmed-up readings."))
            elif re.fullmatch(r"P01[3-6]\d", code):
                categories.append(("oxygen sensor / fuel feedback", f"{code} points to oxygen-sensor/fuel-feedback behavior; compare commanded/observed mixture and sensor response."))
            elif code in {"P0420", "P0430"}:
                categories.append(("catalyst efficiency", f"{code} indicates catalyst-efficiency monitoring; verify sensor behavior and exhaust conditions before attributing catalyst failure."))
            elif code in {"P0016", "P0017", "P0018", "P0019"}:
                categories.append(("cam/crank correlation", f"{code} indicates a cam/crank correlation concern; verify timing correlation before considering mechanical timing faults."))
            elif re.fullmatch(r"P07[23]\d", code) or code in {"P0730", "P0731", "P0732", "P0733", "P0734", "P0735"}:
                categories.append(("transmission control / gear ratio", f"{code} indicates a transmission control or ratio concern; compare commanded versus actual gear, speed, and slip."))
            elif code in {"P0560", "P0561", "P0562", "P0563"}:
                categories.append(("power supply / voltage", f"{code} points to system-voltage behavior; verify battery, charging voltage, and voltage stability under load."))
            elif code.startswith("U"):
                categories.append(("vehicle network communication", f"{code} is a network/communication DTC; verify bus health, ECU reachability, power/ground, and gateway routing."))

    @staticmethod
    def _add_symptom_categories(text: str, categories: list[tuple[str, str]]) -> None:
        if any(x in text for x in ("no start", "won't start", "does not start", "cranks but")):
            categories.append(("starting system / engine start", "The reported no-start behavior requires separating crank, authorization, fuel, ignition, and engine-speed evidence."))
        if any(x in text for x in ("stall", "stalls", "dies while driving")):
            categories.append(("engine stalling", "The stalling condition should be correlated with RPM, fuel pressure, ignition, and relevant ECU status."))
        if any(x in text for x in ("overheat", "overheating", "temperature high", "coolant boiling")):
            categories.append(("cooling system", "The overheating symptom requires measured coolant temperature, fan behavior, coolant circulation, and system-level checks."))
        if any(x in text for x in ("battery", "slow crank", "weak crank", "electrical")):
            categories.append(("electrical power supply", "The electrical symptom should be validated with battery and charging voltage measurements under defined conditions."))

    @staticmethod
    def _add_context_categories(text: str, categories: list[tuple[str, str]]) -> None:
        lpg_only = "lpg" in text and (
            "petrol normal" in text
            or "normal on petrol" in text
            or "smoothly on petrol" in text
            or "only on lpg" in text
            or ("petrol" in text and "significantly reduces" in text)
            or "lpg_only" in text
        )
        if lpg_only and any(x in text for x in ("misfire", "shak", "jerk")):
            categories.extend([
                ("LPG fuel delivery / mixture", "The fault is strongly associated with LPG operation; verify LPG pressure, injector delivery, and mixture/calibration before condemning ignition hardware."),
                ("ignition under LPG load", "A marginal ignition system can misfire under the higher demand associated with LPG/load; confirm with cylinder-specific evidence."),
                ("air-fuel / intake", "An air-fuel or intake imbalance can become more visible under LPG load; verify trims, airflow, and intake integrity."),
                ("mechanical cylinder condition", "A cylinder-specific misfire remains mechanically possible; verify compression, leak-down, and timing evidence before ruling it out."),
                ("LPG fuel delivery", "The fault is strongly associated with LPG operation; verify LPG pressure, injector delivery, and mixture/calibration before condemning ignition hardware."),
                ("LPG injection", "The fault is strongly associated with LPG operation; verify LPG pressure, injector delivery, and mixture/calibration before condemning ignition hardware."),
                ("ignition", "A marginal ignition system can misfire under the higher demand associated with LPG/load; confirm with cylinder-specific evidence."),
                ("intake", "An air-fuel or intake imbalance can become more visible under LPG load; verify trims, airflow, and intake integrity."),
            ])

        if "acceleration" in text or "under load" in text:
            categories.append(("load-dependent behavior", "The event is operating-condition dependent; reproduce it with synchronized RPM/load measurements."))

        # Legacy consumers/tests use the short category names. Keep these
        # aliases whenever the evidence clearly identifies an LPG-specific
        # misfire/shaking condition, including cases where the DTC was added
        # separately from the symptom text.
        if lpg_only and any(x in text for x in ("misfire", "shak", "jerk")):
            categories.extend([
                ("ignition", "A marginal ignition system can misfire under LPG/load; confirm with cylinder-specific evidence."),
                ("intake", "An air-fuel or intake imbalance can become more visible under LPG load; verify trims, airflow, and intake integrity."),
            ])
        if "idle" in text and any(x in text for x in ("rough", "shaking", "unstable")):
            categories.append(("idle stability / air-fuel control", "The idle symptom should be separated into airflow, mixture, ignition, and mechanical contributors."))
        if "smoke" in text or "oil consumption" in text:
            categories.append(("oil / combustion condition", "Visible smoke or oil-consumption evidence requires separating combustion, ventilation, and lubricant-related causes."))

    @staticmethod
    def _recommend(session: DiagnosticSession, text: str, dtcs: set[str]) -> DiagnosticSession:
        # Recommendations are scenario-specific. These are diagnostic actions,
        # not component verdicts.
        recommendations: list[DiagnosticTest] = []

        def add(
            name: str,
            purpose: str,
            target: list[str],
            safety: list[str] | None = None,
            risk: str = "LOW",
            cost: float = 1.0,
            information_gain: float | None = None,
        ) -> None:
            # Rule-driven recommendations must expose real decision metadata as
            # well, instead of falling back to DiagnosticTest's zero defaults.
            n = max(len(session.hypotheses), 1)
            target_count = len(set(target) & {h.category for h in session.hypotheses})
            coverage = min(max(target_count / n, 0.0), 1.0)
            # Use a bounded uncertainty/value score. A small floor keeps
            # single-hypothesis cases useful without pretending the test is fully
            # discriminative.
            if information_gain is None:
                information_gain = round(0.25 + 0.75 * (1.0 - abs(0.5 - coverage) * 2.0), 4)
            risk_penalty = {"LOW": 0.0, "MEDIUM": 0.10, "HIGH": 0.20}.get(risk, 0.15)
            cost_penalty = min(max((cost - 1.0) / 4.0, 0.0), 1.0)
            priority = round(
                min(max(0.60 * information_gain + 0.25 * (1.0 - cost_penalty) + 0.15 * (1.0 - risk_penalty), 0.0), 1.0),
                4,
            )
            recommendations.append(DiagnosticTest(
                name=name,
                purpose=purpose,
                safety_notes=safety or [],
                target_hypotheses=target,
                prerequisites=[],
                priority_score=priority,
                expected_information_gain=round(information_gain, 4),
                estimated_cost=cost,
                risk_level=risk,
            ))

        cats = {h.category for h in session.hypotheses}
        if "LPG fuel delivery / mixture" in cats:
            add("Measure LPG pressure at idle and under load", "Determine whether gas pressure remains stable during the symptom window.", ["LPG fuel delivery / mixture"], ["Use approved LPG diagnostic procedures and keep ignition sources controlled."], cost=1.5)
            add("Compare STFT/LTFT on petrol versus LPG", "Separate a fuel-system-specific mixture problem from an engine-wide control problem.", ["LPG fuel delivery / mixture", "lean mixture", "rich mixture"], cost=1.0)
            add("Compare LPG injector contribution / balance", "Check whether one cylinder receives materially different LPG delivery.", ["LPG fuel delivery / mixture"], ["Follow LPG system manufacturer procedures."], "MEDIUM", cost=2.0)
        if "ignition / combustion" in cats or "ignition under LPG load" in cats:
            add("Compare cylinder misfire counters under the same load", "Determine whether the event remains isolated to a cylinder and under which fuel mode it occurs.", ["ignition / combustion", "ignition under LPG load"], cost=1.0)
            add("Check ignition performance under controlled load", "Correlate ignition behavior with the exact RPM/load/fuel condition where the misfire occurs.", ["ignition / combustion", "ignition under LPG load"], ["Use properly rated test equipment and workshop precautions."], "MEDIUM", cost=2.0)
        if "air metering / MAF" in cats:
            add("Validate MAF signal against RPM/load plausibility", "Determine whether the airflow signal is plausible across operating points.", ["air metering / MAF"], cost=1.0)
            add("Inspect intake and MAF wiring/connectors", "Separate wiring/connector faults from a sensor-signal problem.", ["air metering / MAF", "lean mixture"], cost=1.0)
        if "lean mixture" in cats:
            add("Check for unmetered-air leak", "Look for air entering downstream of the expected metering point.", ["lean mixture"], cost=1.5)
            add("Measure fuel pressure under load", "Verify that fuel delivery can maintain required pressure during the reported condition.", ["lean mixture"], cost=2.0)
        if "rich mixture" in cats:
            add("Check injector leakage / fuel pressure", "Separate excess fuel delivery from feedback or airflow-model errors.", ["rich mixture"], cost=2.0)
            add("Compare lambda response and fuel trims", "Determine whether the rich condition is persistent and how the feedback system responds.", ["rich mixture", "oxygen sensor / fuel feedback"], cost=1.5)
        if "oxygen sensor / fuel feedback" in cats:
            add("Check O2 sensor response and heater behavior", "Validate sensor response speed, plausibility, and heater-related behavior.", ["oxygen sensor / fuel feedback"], cost=2.0)
        if "catalyst efficiency" in cats:
            add("Compare upstream/downstream O2 behavior after warm-up", "Verify catalyst-monitoring conditions before attributing low efficiency to the catalyst itself.", ["catalyst efficiency"], cost=1.5)
        if "coolant temperature sensing" in cats or "cooling system" in cats:
            add("Compare ECU coolant temperature with independent measurement", "Separate sensor/rationality problems from actual thermal conditions.", ["coolant temperature sensing", "cooling system"], cost=1.0)
            add("Verify cooling fan command and actual fan operation", "Determine whether fan activation matches the measured temperature condition.", ["cooling system"], cost=1.0)
        if "cam/crank correlation" in cats:
            add("Compare cam/crank correlation data and timing values", "Validate correlation before considering mechanical timing intervention.", ["cam/crank correlation"], ["Follow manufacturer timing and engine-running safety procedures."], "MEDIUM", cost=2.5)
        if "transmission control / gear ratio" in cats:
            add("Compare commanded gear, actual gear and slip", "Determine whether the ratio deviation is hydraulic, sensor-related, or control-related.", ["transmission control / gear ratio"], cost=2.0)
            add("Check transmission fluid temperature and pressure evidence", "Correlate the event with operating temperature and available hydraulic evidence.", ["transmission control / gear ratio"], ["Follow transmission service safety procedures."], "MEDIUM", cost=2.5)
        if "power supply / voltage" in cats or "electrical power supply" in cats:
            add("Measure battery voltage at rest and during crank", "Determine whether battery voltage is adequate and stable during starting load.", ["power supply / voltage", "electrical power supply"], cost=1.0)
            add("Measure charging voltage under electrical load", "Check alternator/regulator behavior across representative loads.", ["power supply / voltage", "electrical power supply"], cost=1.0)
        if "vehicle network communication" in cats:
            add("Capture CAN traffic and verify ECU/gateway responses", "Separate bus integrity, gateway routing, ECU availability, and application-level faults.", ["vehicle network communication"], cost=2.5)
        if "starting system / engine start" in cats:
            add("Verify engine speed, battery voltage and start authorization", "Separate crank/electrical/authorization issues before fuel or ignition parts are isolated.", ["starting system / engine start", "power supply / voltage"], cost=1.0)
        if "engine stalling" in cats:
            add("Correlate stall event with RPM, fuel pressure and ECU status", "Determine whether the stall is caused by fuel, ignition, speed-signal, or control evidence.", ["engine stalling", "ignition / combustion"], cost=1.0)
        if "idle stability / air-fuel control" in cats:
            add("Compare idle fuel trims, MAF/MAP and misfire counters", "Separate air-fuel control from ignition and mechanical idle contributors.", ["idle stability / air-fuel control", "lean mixture", "air metering / MAF"], cost=1.0)

        # Safe generic fallback for unknown scenarios.
        if not recommendations:
            add("Collect baseline live data and reproduce the symptom", "Establish time-synchronized RPM, load, temperature, and relevant sensor evidence before narrowing the fault domain.", [], cost=1.0)
            add("Read ECU DTCs and freeze-frame data", "Obtain ECU-reported evidence and operating conditions associated with the event.", [], cost=1.0)

        session.recommendations = recommendations
        session.state = SessionState.TESTING
        return session
