"""Protocol capabilities are adapter capabilities, never a model-name guarantee.

ELM selection numbers are facts from the ELM327 command interface. Additional
families are listed explicitly without claiming an implemented wire driver.
"""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Protocol:
    id: str
    standard: str
    elm_code: str | None
    bitrate: int | None = None
    id_bits: int | None = None
    status: str = "elm_adapter_required"


PROTOCOLS = (
    Protocol("auto", "ELM automatic protocol detection", "0"),
    Protocol("j1850-pwm", "SAE J1850 PWM", "1", 41600),
    Protocol("j1850-vpw", "SAE J1850 VPW", "2", 10400),
    Protocol("iso9141-2", "ISO 9141-2", "3", 10400),
    Protocol("kwp-5baud", "ISO 14230-4 KWP, 5-baud initialization", "4", 10400),
    Protocol("kwp-fast", "ISO 14230-4 KWP, fast initialization", "5", 10400),
    Protocol("can-11-500", "ISO 15765-4 CAN", "6", 500000, 11),
    Protocol("can-29-500", "ISO 15765-4 CAN", "7", 500000, 29),
    Protocol("can-11-250", "ISO 15765-4 CAN", "8", 250000, 11),
    Protocol("can-29-250", "ISO 15765-4 CAN", "9", 250000, 29),
    Protocol("j1939", "SAE J1939 CAN (heavy-duty; not generic Mode 01 decoding)", "A", 250000, 29, "passive_dm1_dm2_and_tp_bam_decoder"),
    Protocol("uds-can", "ISO 14229 UDS over ISO 15765-2", None, status="read_only_addressed_elm_can_and_isotp_library"),
    Protocol("doip", "ISO 13400 diagnostic transport over IP", None, status="read_only_tcp_routing_and_uds_22_19"),
    Protocol("can-fd", "ISO 11898-1 CAN FD / ISO 15765-2", None, status="not_implemented"),
    Protocol("obdonuds", "SAE J1979-2 OBDonUDS", None, status="requires_regulatory_did_profile_not_implemented"),
    Protocol("wwh-obd", "ISO 27145 worldwide harmonized OBD", None, status="not_implemented"),
    Protocol("j1708-j1587", "SAE J1708/J1587 legacy heavy-duty", None, status="passive_checksum_and_parameter_framing_decoder"),
    Protocol("oem-diagnostics", "Manufacturer-specific diagnostics/security/OBD-I", None, status="oem_documentation_and_driver_required"),
)
BY_ID = {p.id: p for p in PROTOCOLS}
BY_ELM = {p.elm_code: p for p in PROTOCOLS if p.elm_code is not None}
SOURCES = [
    "https://www.elmelectronics.com/wp-content/uploads/2016/07/ELM327DS.pdf",
    "https://github.com/brendan-w/python-OBD/tree/a378bdd81d58c67d08050e4244173a9a7dbda73d/obd/protocols",
    "https://en.wikipedia.org/wiki/On-board_diagnostics",
]


def initialization(protocol_id: str = "auto") -> list[str]:
    protocol = BY_ID.get(protocol_id)
    if protocol is None or protocol.elm_code is None or protocol.elm_code == "A":
        raise ValueError("Protocol is not supported by the generic ELM OBD-II reader")
    # Headers off, ISO-TP formatting on; the adapter owns link-layer framing.
    return ["ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATCAF1", f"ATSP{protocol.elm_code}"]


def detected_protocol(raw: str) -> dict:
    value = raw.replace(">", "").strip().upper()
    automatic = value.startswith("A") and len(value) == 2
    code = value[1:] if automatic else value
    protocol = BY_ELM.get(code)
    if protocol is None or code == "0":
        raise ValueError("Unknown or unnegotiated ATDPN response")
    return asdict(protocol) | {"automatic": automatic, "observed": True}


def protocol_catalog() -> dict:
    return {"protocols": [asdict(p) for p in PROTOCOLS], "sources": SOURCES,
            "selection_policy": "Use auto; confirm with 0100 and ATDPN. A model reference is not detected ECU support."}
