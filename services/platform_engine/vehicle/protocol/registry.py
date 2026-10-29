"""Authoritative BACKEND catalogue of standards; not an assertion of hardware support.

Transport (CAN/K-Line/Ethernet), diagnostics (UDS/OBD/J1939), and adapter
capability are separate. Vehicle make/model never confirms a protocol.
Only an observed adapter/ECU handshake can provide measured evidence.
No write services, security access, programming or DTC clearing here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Protocol:
    id: str
    standard: str
    layer: str
    family: str
    elm_code: str | None = None
    support: str = "metadata_only"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# "adapter_dependent" only describes a potential wire transport. It does NOT
# mean that our backend can perform physical ECU transactions.
PROTOCOLS: tuple[Protocol, ...] = (
    Protocol("j1850_pwm", "SAE J1850 PWM", "obd_transport", "J1850", "1", "adapter_dependent", "Older North-American Ford-family applications; auto-detect first."),
    Protocol("j1850_vpw", "SAE J1850 VPW", "obd_transport", "J1850", "2", "adapter_dependent", "Older North-American GM-family applications; auto-detect first."),
    Protocol("iso9141_2", "ISO 9141-2 K-Line", "obd_transport", "K-Line", "3", "adapter_dependent", "K-Line, 5-baud init; older European/Asian OBD."),
    Protocol("iso14230_4_slow", "ISO 14230-4 KWP2000 (5-baud)", "obd_transport", "K-Line", "4", "adapter_dependent", "Legacy emissions OBD over K-Line."),
    Protocol("iso14230_4_fast", "ISO 14230-4 KWP2000 (fast init)", "obd_transport", "K-Line", "5", "adapter_dependent", "Legacy emissions OBD over K-Line."),
    Protocol("iso15765_4_can11_500", "ISO 15765-4 CAN 11-bit / 500 kbit/s", "obd_transport", "CAN", "6", "adapter_dependent", "Common passenger-vehicle CAN OBD."),
    Protocol("iso15765_4_can29_500", "ISO 15765-4 CAN 29-bit / 500 kbit/s", "obd_transport", "CAN", "7", "adapter_dependent", "Extended-address CAN OBD."),
    Protocol("iso15765_4_can11_250", "ISO 15765-4 CAN 11-bit / 250 kbit/s", "obd_transport", "CAN", "8", "adapter_dependent", "Not universally supported by adapters or vehicles."),
    Protocol("iso15765_4_can29_250", "ISO 15765-4 CAN 29-bit / 250 kbit/s", "obd_transport", "CAN", "9", "adapter_dependent", "Not universally supported by adapters or vehicles."),
    Protocol("j1939_250", "SAE J1939-73 29-bit / 250 kbit/s", "commercial_obd", "J1939", "A", "passive_dm1_dm2_decoder", "DM1/DM2 SPN/FMI decoding including complete TP.BAM captures; no RTS/CTS or active polling."),
    Protocol("j1939_500", "SAE J1939 / 500 kbit/s", "commercial_obd", "J1939", None, "metadata_only", "Support requires J1939-capable device and implementation."),
    Protocol("uds_on_can", "ISO 14229-1 UDS on ISO 15765-2 DoCAN", "diagnostic_application", "UDS", None, "read_only_addressed_elm_can", "Explicit CAN ECU IDs and detected CAN required; UDS 22 and 19/02 only. No security/programming services."),
    Protocol("uds_on_doip", "ISO 14229 UDS over ISO 13400 DoIP", "diagnostic_application", "DoIP", None, "read_only_tcp", "TCP routing activation plus UDS 22 and 19/02; explicit ECU logical addresses required. No UDP discovery/TLS gateway authentication."),
    Protocol("uds_on_can_fd", "UDS over CAN FD", "diagnostic_application", "CAN-FD", None, "metadata_only", "Requires CAN-FD adapter and ECU-specific discovery; not ELM327 classical CAN."),
    Protocol("wwh_obd", "ISO 27145 WWH-OBD", "regulatory_diagnostic", "WWH-OBD", None, "metadata_only", "CAN or DoIP depending on the vehicle; distinct from generic OBD-II Mode 01."),
    Protocol("obdonuds", "SAE J1979-2 OBDonUDS", "regulatory_diagnostic", "OBDonUDS", None, "metadata_only", "Introduction and compliance differ by market/class/model year."),
    Protocol("kwp1281", "VW Group KW1281", "manufacturer_specific", "K-Line", None, "metadata_only", "Not ISO 14230-4 generic OBD; special adapter/software needed."),
    Protocol("single_wire_can", "SAE J2411 Single-Wire CAN / GMLAN", "manufacturer_specific", "SWCAN", None, "metadata_only", "Manufacturer bus outside generic emissions CAN pins."),
    Protocol("lin", "ISO 17987 LIN", "subsystem_bus", "LIN", None, "metadata_only", "Not a generic OBD-II vehicle connection."),
    Protocol("flexray", "ISO 17458 FlexRay / UDSonFR", "subsystem_bus", "FlexRay", None, "metadata_only", "Not a generic OBD-II vehicle connection."),
    Protocol("j1708_j1587", "SAE J1708 / J1587", "commercial_legacy", "J1708", None, "passive_parameter_decoder", "J1708 checksum and J1587 parameter framing; no OEM scaling, electrical driver or classic ELM polling."),
    Protocol("j1979_classic", "SAE J1979 classic emissions diagnostic services", "diagnostic_application", "OBD-II", None, "adapter_dependent", "Modes 01/03/09 etc over negotiated emissions OBD transport; distinct from the wire protocol."),
    Protocol("iso15765_2", "ISO 15765-2 ISO-TP", "transport", "CAN", None, "simulator_only", "Multi-frame diagnostics; requires CAN adapter supporting ISO-TP or host stack."),
    Protocol("kwp2000_oem", "ISO 14230-3 KWP2000 manufacturer diagnostics", "manufacturer_specific", "K-Line", None, "metadata_only", "Not the same as mandatory KWP emissions services."),
    Protocol("vw_tp16", "Volkswagen Group CAN TP1.6", "manufacturer_specific", "VAG", None, "metadata_only", "Legacy VW Group OEM CAN transport; not ISO-TP and not standard ELM ATSP."),
    Protocol("vw_tp20", "Volkswagen Group CAN TP2.0", "manufacturer_specific", "VAG", None, "metadata_only", "VW/Audi proprietary transport, later superseded by UDS/ISO-TP."),
    Protocol("bmw_kbus", "BMW K-Bus", "manufacturer_specific", "BMW", None, "metadata_only", "Body network, not emissions K-Line protocol."),
    Protocol("bmw_dcan", "BMW D-CAN diagnostics", "manufacturer_specific", "BMW", None, "metadata_only", "BMW-specific ECU access over CAN, requires proper adapter and addressing."),
    Protocol("bmw_enet", "BMW ENET / Ethernet diagnostics", "manufacturer_specific", "BMW", None, "metadata_only", "Manufacturer Ethernet diagnostic transport; adapter/tool specific."),
    Protocol("ford_ms_can", "Ford medium-speed CAN", "manufacturer_specific", "Ford", None, "metadata_only", "OEM body modules; often not exposed by basic single-CAN ELM adapters."),
    Protocol("ford_hs_can", "Ford high-speed CAN", "manufacturer_specific", "Ford", None, "metadata_only", "OEM network; SAE J1979 generic CAN is a separate profile."),
    Protocol("gm_gmlan", "General Motors GMLAN", "manufacturer_specific", "GM", None, "metadata_only", "OEM CAN protocol families; gateway/module-specific."),
    Protocol("nissan_consult", "Nissan CONSULT proprietary diagnostics", "manufacturer_specific", "Nissan", None, "metadata_only", "Tool/vendor-specific service protocol, not generic EOBD."),
    Protocol("honda_hds", "Honda HDS manufacturer diagnostics", "manufacturer_specific", "Honda", None, "metadata_only", "Manufacturer diagnostic software/services; model/year dependent."),
    Protocol("toyota_techstream", "Toyota Techstream manufacturer diagnostics", "manufacturer_specific", "Toyota", None, "metadata_only", "Manufacturer services over available transport, not a single wire protocol."),
    Protocol("mercedes_oem", "Mercedes-Benz OEM diagnostics (K-Line/CAN/DoIP families)", "manufacturer_specific", "Mercedes-Benz", None, "metadata_only", "Mercedes ECU diagnosis varies by control unit/year/market; no asserted W211 protocol mapping."),
)
BY_ID = {p.id: p for p in PROTOCOLS}
BY_ELM_CODE = {p.elm_code: p for p in PROTOCOLS if p.elm_code is not None}

CANDIDATE_NOTICE = (
    "Candidates are regulation/era hints, never confirmed per model or ECU. "
    "Use adapter auto-detect and read-only identification first; cross-check VIN, "
    "region, vehicle class and detected ECU. No physical compatibility is guaranteed."
)


def all_protocols() -> list[dict[str, Any]]:
    return [p.to_dict() for p in PROTOCOLS]


def read_elm_detected_protocol(raw: str) -> dict[str, Any]:
    """Parse an observed ELM327 ATDPN reply: A6/6, A3/3, etc.

    This function does not communicate with hardware or send AT commands.
    No success claim is made from a configured setting without an observation.
    """
    normalized = raw.strip().upper().replace(" ", "").replace("\r", "").replace("\n", "")
    auto_selected = normalized.startswith("A")
    code = normalized[1:] if auto_selected else normalized
    protocol = BY_ELM_CODE.get(code) if len(code) == 1 else None
    return {
        "raw": raw,
        "adapter_observation": "ATDPN",
        "protocol_id": protocol.id if protocol else None,
        "auto_selected": auto_selected,
        "evidence": "adapter_reported" if protocol else "unrecognized",
        "confirmed_ecu_communication": False,
    }


def _add(target: list[str], *items: str) -> None:
    for item in items:
        if item not in target:
            target.append(item)


# This describes possible *OEM* diagnostic families, not proven emissions OBD
# transports. It is deliberately separate from ISO 15765/J1850 candidates.
OEM_HINTS = {
    "volkswagen": ("kwp1281", "kwp2000_oem", "vw_tp16", "vw_tp20", "uds_on_can"),
    "audi": ("kwp1281", "kwp2000_oem", "vw_tp16", "vw_tp20", "uds_on_can"),
    "skoda": ("kwp1281", "kwp2000_oem", "vw_tp16", "vw_tp20", "uds_on_can"),
    "seat": ("kwp1281", "kwp2000_oem", "vw_tp16", "vw_tp20", "uds_on_can"),
    "bmw": ("bmw_kbus", "bmw_dcan", "bmw_enet", "uds_on_can", "uds_on_doip"),
    "mini": ("bmw_dcan", "uds_on_can"),
    "mercedes-benz": ("mercedes_oem", "uds_on_can", "uds_on_doip"),
    "ford": ("ford_hs_can", "ford_ms_can", "uds_on_can"),
    "chevrolet": ("gm_gmlan", "single_wire_can", "uds_on_can"),
    "gmc": ("gm_gmlan", "single_wire_can", "uds_on_can"),
    "buick": ("gm_gmlan", "single_wire_can", "uds_on_can"),
    "nissan": ("nissan_consult", "uds_on_can"),
    "honda": ("honda_hds", "uds_on_can"),
    "acura": ("honda_hds", "uds_on_can"),
    "toyota": ("toyota_techstream", "uds_on_can"),
    "lexus": ("toyota_techstream", "uds_on_can"),
}


def oem_diagnostic_hints(make: str) -> list[dict[str, Any]]:
    """Manufacturer family research leads, never automatically detected ECUs."""
    return [
        {
            "id": id,
            "standard": BY_ID[id].standard,
            "support": BY_ID[id].support,
            "evidence": "manufacturer_family_hint_not_vehicle_fitment",
        }
        for id in OEM_HINTS.get(make.strip().lower(), ())
    ]


def assess_protocols(
    *, year: int, market: str = "unknown", make: str = "",
    fuel: str = "", vehicle_class: str = "passenger",
    detected_elm: str | None = None,
) -> dict[str, Any]:
    """Conservative compatibility HINTS, never make/model-to-ECU assertions."""
    market = market.strip().upper()
    vehicle_class = vehicle_class.strip().lower()
    fuel = fuel.strip().lower()
    make = make.strip().lower()
    candidates: list[str] = []
    warnings: list[str] = []
    if year < 1886 or year > 2100:
        raise ValueError("year outside supported range")
    heavy = vehicle_class in {"heavy", "heavy-duty", "truck-heavy", "bus", "commercial-heavy"}
    if heavy:
        _add(candidates, "j1939_250", "j1939_500", "wwh_obd")
        if year < 2006:
            _add(candidates, "j1708_j1587")
        # CARB's J1979-2 transition is model-year AND certification-specific.
        # Never assign it to every global truck in 2023 or later.
        if market in {"US", "USA", "CA", "CALIFORNIA"} and year >= 2027:
            _add(candidates, "obdonuds")
            warnings.append("2027+ CARB-certified heavy-duty engines transition to OBDonUDS; verify certification/VIN.")
        elif year >= 2024 and make in {"volvo", "mack"} and market in {"US", "USA", "CA", "CALIFORNIA"}:
            _add(candidates, "obdonuds")
            warnings.append("Only selected 2024+ Volvo/Mack CARB engine families adopted OBDonUDS early; VIN/engine certification required.")
        warnings.append("Commercial J1939/WWH-OBD depends on engine certification, region and vehicle OEM.")
    elif fuel in {"electric", "battery-electric", "bev", "ev"}:
        _add(candidates, "uds_on_can", "uds_on_doip")
        warnings.append("A BEV may not expose combustion-emissions OBD PIDs; OEM diagnostics are separate.")
    elif market in {"US", "USA", "CA", "CANADA"} and year >= 2008:
        _add(candidates, "iso15765_4_can11_500", "iso15765_4_can29_500")
        warnings.append("CAN-based emissions OBD is expected for covered 2008+ US vehicles; CAN ID format must be detected.")
        warnings.append("OBDonUDS availability cannot be determined from a passenger-vehicle year alone.")
    elif market in {"EU", "EEA", "UK"} and year >= 2008:
        _add(candidates, "iso15765_4_can11_500", "iso15765_4_can29_500",
             "iso15765_4_can11_250", "iso15765_4_can29_250",
             "iso9141_2", "iso14230_4_slow", "iso14230_4_fast")
        warnings.append("CAN is likely in 2008+ European passenger cars, but legacy EOBD K-Line remains a candidate until measured.")
        warnings.append("European EOBD regulation, fuel and registration categories vary; certification market is not owner's location.")
    elif year >= 2008:
        _add(candidates, "iso15765_4_can11_500", "iso15765_4_can29_500",
             "iso15765_4_can11_250", "iso15765_4_can29_250",
             "iso14230_4_fast", "iso9141_2")
        warnings.append("No OBD legal applicability can be assumed for an unspecified market.")
    elif year >= 1996:
        if market in {"US", "USA", "CA", "CANADA"} and make in {
            "ford", "lincoln", "mercury",
        }:
            _add(candidates, "j1850_pwm")
        elif market in {"US", "USA", "CA", "CANADA"} and make in {
            "chevrolet", "gmc", "buick", "cadillac", "pontiac", "oldsmobile",
        }:
            _add(candidates, "j1850_vpw")
        _add(candidates, "iso9141_2", "iso14230_4_slow", "iso14230_4_fast",
             "j1850_pwm", "j1850_vpw")
        if year >= 2003:
            _add(candidates, "iso15765_4_can11_500", "iso15765_4_can29_500")
        warnings.append("1996–2007 OBD interfaces may use J1850, K-Line, or later CAN; manufacturer is only a weak heuristic.")
    else:
        warnings.append("Pre-1996 standardized OBD-II is not assured. No universal connector or protocol can be inferred; inspect OEM documentation.")
    detected = read_elm_detected_protocol(detected_elm) if detected_elm is not None else None
    return {
        "year": year, "market": market.lower(), "vehicle_class": vehicle_class,
        "fuel": fuel, "make": make,
        "detection_command": "ATSP0",  # ELM auto mode (not a scan executed by this API).
        "readback_command": "ATDPN",
        "candidates": [
            {"id": id, "standard": BY_ID[id].standard, "support": BY_ID[id].support}
            for id in candidates
        ],
        "detected": detected,
        "oem_diagnostics": oem_diagnostic_hints(make),
        "verified_obd_support": False,
        "confidence": "adapter_reported" if detected and detected["protocol_id"] else "unverified_hint",
        "evidence_source": "market/year/class heuristic; adapter readback if supplied",
        "warnings": warnings,
        "notice": CANDIDATE_NOTICE,
    }
