from dataclasses import dataclass

@dataclass(frozen=True)
class OtaManifest:
    version: str
    artifact_url: str
    sha256: str
    min_app_version: str
    mandatory: bool = False

class OtaPolicy:
    """Validates metadata before a future downloader/verifier applies an update."""
    @staticmethod
    def validate(manifest: OtaManifest) -> None:
        if not manifest.version or not manifest.sha256 or len(manifest.sha256) != 64:
            raise ValueError("Invalid OTA manifest")
        if not manifest.artifact_url.startswith(("https://", "file://")):
            raise ValueError("OTA artifacts must use an approved transport")
