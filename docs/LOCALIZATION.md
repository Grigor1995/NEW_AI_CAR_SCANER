# Localization

Exactly four application catalogs: English(en), Armenian(hy), Russian(ru), French(fr). Qt Linguist TS files compile to resource-bundled QM files; QTranslator plus QQmlEngine::retranslate changes the live UI. English is the fallback. Measurement values use QLocale number formatting. The current source catalog is tested for complete nonempty translations and matching contexts; the UI self-test verifies runtime language switches.

Protocol identifiers, provenance enums and engineering unit symbols remain stable machine-readable values. New screens/errors must add translated source messages before completion. Native device/OS error text and full provider-generated reports are not certified translations. Professional linguistic review, screen-reader testing and all localized narrow-layout visual cases remain release checks.
