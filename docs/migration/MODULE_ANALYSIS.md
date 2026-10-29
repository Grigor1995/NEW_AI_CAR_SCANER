# Source runtime module analysis

Every runtime Python module in main is listed below. Symbols are static inventory, not proof of successful execution. Backend/device/vehicle/shared modules are preserved in services/platform_engine; the old desktop presentation is replaced by Qt Quick.

| Source module | Lines | Classes / top-level functions |
|---|---:|---|
| backend/__init__.py | 0 |  |
| backend/acquisition/__init__.py | 4 |  |
| backend/acquisition/models.py | 25 | AcquisitionStartRequest, AcquisitionStatus, SimulatorParameters |
| backend/acquisition/service.py | 234 | AcquisitionSourceType, AcquisitionRecord, _AcquisitionState, AcquisitionApiService |
| backend/ai/__init__.py | 0 |  |
| backend/ai/embeddings/__init__.py | 13 |  |
| backend/ai/embeddings/providers.py | 111 | HashEmbeddingProvider, SentenceTransformerEmbeddingProvider, FastEmbedEmbeddingProvider, create_embedding_provider |
| backend/ai/evaluation/golden.py | 46 | GoldenCase, GoldenResult, GoldenCaseEvaluator, _normalize_claim_text |
| backend/ai/evaluation/grounding.py | 29 | GroundingResult, GroundingEvaluator |
| backend/ai/ingestion/__init__.py | 11 |  |
| backend/ai/ingestion/chunker.py | 88 | ChunkingConfig, SemanticChunker, _overlaps_page |
| backend/ai/ingestion/dataset.py | 33 | RetrievalExample, RetrievalDatasetBuilder |
| backend/ai/ingestion/models.py | 90 | DocumentMetadata, ParsedPage, ParsedDocument, IngestedDocument, KnowledgeChunk, IngestionResult, stable_document_id, stable_chunk_id |
| backend/ai/ingestion/parsers.py | 94 | SupportsParser, TextParser, JsonParser, YamlParser, _HTMLTextExtractor, HtmlParser, PdfParser, DocumentParserRegistry |
| backend/ai/ingestion/pipeline.py | 80 | IngestionConfig, KnowledgeIngestionPipeline |
| backend/ai/interfaces.py | 13 | LLMResponse, LLMProvider, LocalLLMProvider, EmbeddingProvider |
| backend/ai/live_analysis.py | 134 | _recent_signal_context, build_live_context, add_live_evidence, analyze_live_session |
| backend/ai/llm/__init__.py | 3 |  |
| backend/ai/llm/factory.py | 22 | build_llm_provider |
| backend/ai/llm/interfaces_guard.py | 32 | SafePromptContext |
| backend/ai/llm/llama_cpp.py | 12 |  |
| backend/ai/llm/llama_server.py | 287 | LlamaServerConfig, LlamaServerLLMProvider |
| backend/ai/llm/ollama.py | 43 | OllamaConfig, OllamaLLMProvider |
| backend/ai/llm/openai_compatible.py | 108 | OpenAICompatibleConfig, HttpOpenAICompatibleProvider |
| backend/ai/llm/orchestrator.py | 28 | DiagnosticLLMOrchestrator |
| backend/ai/ml/__init__.py | 3 |  |
| backend/ai/ml/anomaly.py | 24 | AnomalyResult, NumericAnomalyDetector |
| backend/ai/rag/__init__.py | 4 |  |
| backend/ai/rag/evaluation.py | 81 | RetrievalCase, RetrievalEvaluation, RetrievalQualityGate, RetrievalEvaluator, reciprocal_rank, ndcg_at_k |
| backend/ai/rag/evaluator.py | 19 | RagEvalCase, RagEvalResult, RagEvaluator |
| backend/ai/rag/hybrid.py | 104 | RetrievedChunk, QueryRewriter, HybridFusion, tokenize, lexical_score, metadata_matches |
| backend/ai/rag/pgvector_hybrid.py | 149 | PgVectorConfig, PgVectorHybridRepository |
| backend/ai/rag/quality.py | 45 | CorpusQualitySummary, RetrievalQualityRunner |
| backend/ai/rag/reranker.py | 84 | RerankedHit, LexicalReranker, CrossEncoderReranker, create_reranker |
| backend/ai/rag/retrieval.py | 57 | RetrievalResponse, DiagnosticRAGRetriever |
| backend/ai/rag/store.py | 40 | KnowledgeDocument, RetrievalHit, HybridKnowledgeStore |
| backend/ai/rag/vector_store.py | 47 | VectorHit, PgVectorKnowledgeRepository |
| backend/ai/reasoning/__init__.py | 3 |  |
| backend/ai/reasoning/engine.py | 227 | DiagnosticIntelligenceEngine |
| backend/ai/reasoning/evidence_extractor.py | 37 | StructuredEvidenceExtractor |
| backend/ai/reasoning/pipeline.py | 29 | DiagnosticIntelligenceResult, DiagnosticIntelligencePipeline |
| backend/api/__init__.py | 10 |  |
| backend/api/acquisition_routes.py | 63 | start_acquisition, stop_acquisition, acquisition_status, acquisition_records, simulator_parameters |
| backend/api/active_discovery_routes.py | 36 | ActiveProbeRequest, active_probe, active_map |
| backend/api/advanced_obd_routes.py | 104 | DoipRead, J1939Frame, J1939Capture, J1708Packet, ElmUdsRead, read_doip, decode_j1939, decode_j1939_bam, decode_j1708, read_elm_uds |
| backend/api/ai_routes.py | 61 | KnowledgeRequest, SearchRequest, add_knowledge, search_knowledge, build_ai_context, provider_info |
| backend/api/client_features_routes.py | 125 | VehicleProfileRow, ProfileRequest, _engine, list_profiles, _save_profile, create_profile, update_profile, delete_profile, private_report, report |
| backend/api/decision_routes.py | 40 | ConfirmTestRequest, decision_plan, refresh_decision_plan, select_test |
| backend/api/device_routes.py | 166 | WifiProbeRequest, DeviceConnectRequest, ScanRequest, _json, list_devices, scan_devices, wifi_probe, add_simulator, connect_device, reconnect_device, disconnect_device, device_status, read_vin, read_dtcs, read_live_data, read_device_obd_protocol, diagnostic_discovery |
| backend/api/global_data_routes.py | 17 | get_global_data, get_global_case |
| backend/api/intelligence_routes.py | 57 | IngestTextRequest, TestResultRequest, ingest_text, analyze, add_test_result |
| backend/api/knowledge_routes.py | 50 | IngestTextRequest, ingest_text, ingest_file |
| backend/api/main.py | 278 | lifespan, persist_diagnostic_sessions, health, create_session, list_sessions, read_session, get_session, update_vehicle, add_symptom, update_symptom, delete_symptom, _invalidate_analysis, add_dtc, update_dtc, delete_dtc, _analyze_session, analyze, analyze_compat |
| backend/api/multi_bus_routes.py | 82 | CanBusRequest, GatewayRouteRequest, MultiBusConnectRequest, connect, topology, identify_all, read_dtcs |
| backend/api/multi_ecu_routes.py | 95 | connect, disconnect, topology, identify_all, read_all_dtcs, trace, _status |
| backend/api/network_discovery_routes.py | 65 | DiscoveredFrameRequest, DiscoveryBatchRequest, _frame, ingest_frames, discover_map, reset_discovery |
| backend/api/obd_routes.py | 88 | RawSnapshot, protocols, plan, observed_plan, decode, detected, discovery_plan, discovery_decode |
| backend/api/platform_routes.py | 15 | roles, audit |
| backend/api/rag_routes.py | 55 | RAGSearchRequest, rag_config, rag_search |
| backend/api/state.py | 70 | GlobalSessionRegistry, load_persisted_sessions, persist_sessions |
| backend/api/telemetry_routes.py | 75 | TelemetryBatch, append_samples, telemetry_summary, analyze_telemetry, ai_analyze_live |
| backend/api/vehicle_catalog_routes.py | 287 | CatalogEntry, _ensure_catalog_table, _run_all, _catalog_rows, _require_make_model, list_entries, list_makes, list_models, list_chassis, list_years, list_engines, list_ecus, resolve_variant |
| backend/api/vehicle_diagnostic_routes.py | 219 | _is_simulated_diagnostic_runtime, connect, disconnect, status, identify_ecu, read_dtcs, trace, bind_device, device_binding, sync_obd_to_session |
| backend/api/vehicle_reference_routes.py | 46 | list_reference, profile, image, selected_image |
| backend/api/vehicle_registry_routes.py | 186 | VinLookupRequest, _slug, stats, global_makes, global_models, global_fitments, vehicle_profile, vpic_makes, vpic_models, protocols, compatibility, detected_elm, vin_lookup, local_portrait, photo |
| backend/catalog_sources/__init__.py | 1 |  |
| backend/catalog_sources/wikimedia.py | 61 | fetch_json, clean_text, image_metadata, fetch_image |
| backend/device/__init__.py | 0 |  |
| backend/device/manager.py | 173 | DeviceConnectionError, DeviceStatus, DeviceCapabilities, DeviceDescriptor, VCIConnectionManager, _build_vci_manager |
| backend/diagnostic/__init__.py | 0 |  |
| backend/diagnostic/database.py | 17 | database_engine |
| backend/diagnostic/db_models.py | 27 | Base, VehicleRow, DiagnosticSessionRow, EvidenceRow, VehicleCatalogEntryRow |
| backend/diagnostic/decision.py | 393 | DecisionCandidate, DiagnosticDecisionPlan, TestSpec, DiagnosticDecisionEngine |
| backend/diagnostic/intelligence.py | 3 |  |
| backend/diagnostic/local_database.py | 28 | prepare_local_database |
| backend/diagnostic/localization.py | 667 | _localized_evidence_status, _localized_event, _localized_test_result_fact, _localized_hypothesis_targets, _localized_prerequisite, _localized_safety_note, _localized_safety_note, _localized_evidence_fact, normalize_language, _localized_status, _localized_question, _localized_dtc_description, _localized_rationale, localize_session_analysis, localize_decision_plan |
| backend/diagnostic/models.py | 70 | SessionState, EvidenceSource, EvidenceStatus, Vehicle, Symptom, DTC, Evidence, Hypothesis, DiagnosticTest, TestResult, DiagnosticSession |
| backend/diagnostic/rules.py | 327 | DiagnosticReasoningEngine |
| backend/diagnostic/session_persistence.py | 122 | SessionStateBase, DiagnosticSessionStateRow, DiagnosticSessionPersistence |
| backend/global_data.py | 58 | GlobalDataSnapshot, GlobalDataStore |
| backend/multi_ecu/__init__.py | 4 |  |
| backend/multi_ecu/models.py | 32 | EcuNodeRequest, GatewayNodeRequest, MultiEcuConnectRequest, MultiEcuStatusResponse |
| backend/multi_ecu/multibus_runtime.py | 111 | RoutedEcuRuntime, MultiBusDiagnosticRuntime |
| backend/multi_ecu/service.py | 220 | EcuNode, GatewayNode, VehicleNetworkTopology, SimDtc, SimIdentity, TraceEvent, MultiEcuRuntime, MultiEcuDiagnosticService |
| backend/network_discovery/__init__.py | 3 |  |
| backend/network_discovery/active_service.py | 61 | ActiveNetworkDiscoveryService |
| backend/network_discovery/service.py | 42 | VehicleNetworkDiscoveryService |
| backend/network_discovery/state.py | 6 |  |
| backend/obd/__init__.py | 1 |  |
| backend/obd/catalog.py | 58 | project_root, reference_vehicles, selector_entries, compatibility |
| backend/obd/decoding.py | 83 | Pid, polling_plan, supported_polling_plan, decode_snapshot |
| backend/obd/j1587.py | 40 | decode_packet |
| backend/obd/j1939.py | 68 | decode_diagnostic_frame, decode_bam_capture |
| backend/obd/protocols.py | 68 | Protocol, initialization, detected_protocol, protocol_catalog |
| backend/observability/__init__.py | 1 |  |
| backend/observability/metrics.py | 12 | Counter, MetricsRegistry |
| backend/observability/tracing.py | 15 | Span, span |
| backend/professional_platform/__init__.py | 1 |  |
| backend/professional_platform/analytics.py | 18 | summarize_events |
| backend/professional_platform/audit.py | 12 | AuditLog |
| backend/professional_platform/models.py | 74 | Role, SubscriptionPlan, Organization, Membership, Fleet, FleetVehicle, Subscription, AuditEvent, UsageSnapshot |
| backend/professional_platform/rbac.py | 21 | AuthorizationError, require_role, can_read, can_modify_diagnostics, can_manage_workshop |
| backend/professional_platform/reporting.py | 8 | build_session_report |
| backend/professional_platform/service.py | 50 | WorkshopPlatform |
| backend/scripts/__init__.py | 1 |  |
| backend/scripts/seed_vehicle_catalog.py | 87 | stable_id, expand_years, build_rows, main |
| backend/security/__init__.py | 1 |  |
| backend/security/audit_security.py | 14 | SecurityAuditEvent, event |
| backend/security/auth.py | 35 | Principal, TokenError, _b64, _unb64, issue_token, verify_token |
| backend/security/rate_limit.py | 13 | SlidingWindowRateLimiter |
| backend/security/rbac.py | 9 | allowed |
| backend/simulator/__init__.py | 1 |  |
| backend/simulator/vehicle.py | 22 | SimulatedVehicle, SimulatedAdapter |
| backend/telemetry/__init__.py | 4 |  |
| backend/telemetry/analysis.py | 94 | _sorted_valid, _stddev, compute_stats, detect_events |
| backend/telemetry/channels.py | 20 | channel_name |
| backend/telemetry/definitions.py | 26 | SignalDefinition |
| backend/telemetry/evidence.py | 24 | events_to_evidence |
| backend/telemetry/models.py | 77 | SampleQuality, TelemetrySample, SignalStats, SignalEventType, SignalEvent, TelemetrySummary |
| backend/telemetry/service.py | 50 | TelemetryService |
| backend/tools/import_check.py | 52 | module_exists, check |
| backend/vehicle/__init__.py | 15 |  |
| backend/vehicle/adapters/__init__.py | 0 |  |
| backend/vehicle/adapters/can_simulator.py | 11 | SimulatedCanBus |
| backend/vehicle/adapters/uds_simulator.py | 5 | UdsEcuSimulator |
| backend/vehicle/can/__init__.py | 0 |  |
| backend/vehicle/can/models.py | 13 | CanFrame |
| backend/vehicle/interfaces.py | 30 | DeviceCapabilities, DiagnosticAdapter, VehicleInterface, ObdInterface, CanInterface, UdsInterface |
| backend/vehicle/isotp/__init__.py | 0 |  |
| backend/vehicle/isotp/stack.py | 5 | IsoTpStack |
| backend/vehicle/network/__init__.py | 0 |  |
| backend/vehicle/network/active_discovery.py | 31 | ActiveProbePolicy, ActiveProbeTarget, ActiveProbeResult, ActiveEcuDiscoveryEngine |
| backend/vehicle/network/discovery.py | 37 | CanIdObservation, DiscoveredEcuCandidate, VehicleNetworkDiscoveryResult, VehicleNetworkDiscoveryEngine |
| backend/vehicle/network/models.py | 44 | EcuNode, GatewayNode, GatewayRoute, VehicleNetworkTopology |
| backend/vehicle/network/multibus.py | 28 | CanBusConfig, GatewayRoutingEngine, MultiBusDemultiplexer |
| backend/vehicle/obd/__init__.py | 0 |  |
| backend/vehicle/obd/client.py | 6 | GenericObdClient |
| backend/vehicle/obd/service.py | 9 | ObdDiagnosticService |
| backend/vehicle/protocol/__init__.py | 0 |  |
| backend/vehicle/protocol/trace.py | 17 | ProtocolTraceRecorder, TracedCanBus |
| backend/vehicle/uds/__init__.py | 0 |  |
| backend/vehicle/uds/client.py | 3 | UdsClient |
| backend/vehicle/uds/diagnostics.py | 20 | UdsIdentity, UdsDtcRecord, UdsDiagnosticSession |
| backend/vehicle_diagnostic/__init__.py | 4 |  |
| backend/vehicle_diagnostic/models.py | 54 | DiagnosticConnectRequest, DiagnosticRuntimeStatus, EcuIdentityResponse, UdsDtcResponse, SessionDeviceBindRequest, SessionDeviceBindingResponse, SessionObdSyncResponse |
| backend/vehicle_diagnostic/service.py | 143 | _TraceEvent, _SimDtc, _Runtime, VehicleDiagnosticService |
| device/android-diagnostic-device/__init__.py | 1 |  |
| device/android-diagnostic-device/core/__init__.py | 0 |  |
| device/android-diagnostic-device/core/device.py | 23 | DeviceMode, DeviceStateMachine |
| device/android-diagnostic-device/health/__init__.py | 0 |  |
| device/android-diagnostic-device/health/monitor.py | 24 | HealthLevel, DeviceHealth, HealthMonitor |
| device/android-diagnostic-device/ota/__init__.py | 0 |  |
| device/android-diagnostic-device/ota/manifest.py | 18 | OtaManifest, OtaPolicy |
| device/android-diagnostic-device/storage/__init__.py | 0 |  |
| device/android-diagnostic-device/storage/local_store.py | 29 | LocalDiagnosticStore |
| device/android-diagnostic-device/sync/__init__.py | 0 |  |
| device/android-diagnostic-device/sync/queue.py | 23 | SyncOperation, SyncQueue |
| device/android-diagnostic-device/transport/__init__.py | 0 |  |
| device/android-diagnostic-device/transport/custom_vci.py | 23 | VciPacket, CustomVciCodec |
| vehicle/__init__.py | 0 |  |
| vehicle/acquisition/__init__.py | 11 |  |
| vehicle/acquisition/factory.py | 23 | build_obd_transport, build_obd_source |
| vehicle/acquisition/manager.py | 111 | AcquisitionManager, _record_to_dict |
| vehicle/acquisition/models.py | 49 | AcquisitionState, AcquisitionSourceType, ReconnectPolicy, AcquisitionRecord |
| vehicle/acquisition/offline_queue.py | 55 | OfflineQueue |
| vehicle/acquisition/sources.py | 98 | AcquisitionSource, ObdPollingSource, CanStreamSource, UdsDidPollingSource |
| vehicle/adapters/__init__.py | 0 |  |
| vehicle/adapters/base.py | 16 | DiagnosticAdapter |
| vehicle/adapters/can_simulator.py | 38 | SimulatedCanBus |
| vehicle/adapters/j2534.py | 15 | J2534Adapter |
| vehicle/adapters/simulator.py | 11 | VciSimulatorAdapter |
| vehicle/adapters/uds_simulator.py | 87 | UdsEcuSimulator |
| vehicle/adapters/vendor.py | 26 | VendorSdkAdapter |
| vehicle/can/__init__.py | 0 |  |
| vehicle/can/bus.py | 14 | CanBus |
| vehicle/can/models.py | 21 | CanFrame |
| vehicle/catalog_registry.py | 191 | global_catalog, curated_fitments, makes, models, fitments, registry_stats, vehicle_protocol_profile |
| vehicle/devices/connection.py | 259 | ManagedConnection, DeviceConnectionError, VCIConnectionManager |
| vehicle/devices/models.py | 32 | DeviceStatus, DeviceCapabilities, DeviceDescriptor |
| vehicle/devices/registry.py | 9 | DeviceRegistry |
| vehicle/diagnostic_discovery.py | 86 | vin_from_response, responding_modules, identify, collect |
| vehicle/doip/__init__.py | 1 |  |
| vehicle/doip/client.py | 95 | DoipError, DoipClient |
| vehicle/external_registry.py | 235 | RemoteRegistryUnavailable, _PlainText, _plain, _get_json, nhtsa_available_makes, nhtsa_models_for_make, nhtsa_decode_vin, _permissive_license, commons_photo_candidate |
| vehicle/interfaces.py | 36 | DeviceCapabilities, DiagnosticAdapter, VehicleInterface, ObdInterface, CanInterface, UdsInterface |
| vehicle/isotp/__init__.py | 0 |  |
| vehicle/isotp/models.py | 11 | IsoTpError, IsoTpTimeout, IsoTpProtocolError, FlowStatus |
| vehicle/isotp/stack.py | 69 | IsoTpStack |
| vehicle/j2534/constants.py | 6 |  |
| vehicle/j2534/interface.py | 22 | J2534Message, J2534PassThru |
| vehicle/j2534/windows.py | 25 | J2534Windows |
| vehicle/network/__init__.py | 3 |  |
| vehicle/network/active_discovery.py | 131 | ActiveProbePolicy, ActiveProbeTarget, ActiveProbeResult, ActiveEcuDiscoveryEngine |
| vehicle/network/discovery.py | 250 | CanIdObservation, CanIdProfile, InferredUdsPair, DiscoveredEcuCandidate, VehicleNetworkDiscoveryResult, VehicleNetworkDiscoveryEngine |
| vehicle/network/models.py | 58 | GatewayRoute, GatewayNode, EcuNode, VehicleNetworkTopology |
| vehicle/network/multibus.py | 80 | CanBusConfig, GatewayRoutingEngine, MultiBusDemultiplexer |
| vehicle/network/multiplexer.py | 72 | RoutedCanChannel, CanBusDemultiplexer |
| vehicle/network/runtime.py | 117 | EcuRuntime, MultiEcuRuntime |
| vehicle/obd/__init__.py | 3 |  |
| vehicle/obd/adapters/__init__.py | 0 |  |
| vehicle/obd/adapters/ble.py | 31 | ObdBleTransport |
| vehicle/obd/adapters/simulator.py | 59 | SimulatorTransport |
| vehicle/obd/adapters/tcp_wifi.py | 25 | ObdWifiTransport |
| vehicle/obd/adapters/usb_serial.py | 31 | ObdUsbSerialTransport |
| vehicle/obd/client.py | 163 | GenericObdClient |
| vehicle/obd/pid_catalog.py | 10 | ObdPid |
| vehicle/obd/protocols/__init__.py | 0 |  |
| vehicle/obd/protocols/elm327.py | 145 | OBDProtocolError, OBDResponse, ELM327Protocol |
| vehicle/obd/transport.py | 18 | TransportError, DiagnosticTransport |
| vehicle/protocol/__init__.py | 3 |  |
| vehicle/protocol/elm327_probe.py | 72 | is_obd_mode_01_supported_pids_reply, discover_elm_obd_protocol |
| vehicle/protocol/registry.py | 222 | Protocol, all_protocols, read_elm_detected_protocol, _add, oem_diagnostic_hints, assess_protocols |
| vehicle/protocol/trace.py | 101 | ProtocolTraceEvent, ProtocolTraceRecorder, TracedCanBus |
| vehicle/uds/__init__.py | 9 |  |
| vehicle/uds/client.py | 38 | UdsError, UdsResponse, UdsClient |
| vehicle/uds/decoder.py | 47 | UdsDtcRecord, format_uds_dtc, parse_dtc_information |
| vehicle/uds/diagnostics.py | 71 | EcuIdentity, UdsDiagnosticSession |
| vehicle/uds/read_only.py | 30 | read_request, validate_read_request, validate_positive |
| shared/environment.py | 47 | environment_values, apply_environment |
| shared/reporting.py | 76 | render_diagnostic_pdf |
| apps/desktop/__init__.py | 1 |  |
| apps/desktop/api_client.py | 286 | ApiError, DiagnosticApiClient |
| apps/desktop/backend_recovery.py | 131 | BackendProcess, BackendRecoverySupervisor |
| apps/desktop/backend_worker.py | 47 | main |
| apps/desktop/channel_labels.py | 4 |  |
| apps/desktop/client_workspace.py | 204 | tr, shared_vehicles, edit_inputs, export_backend_report |
| apps/desktop/dashboard_translations.py | 334 |  |
| apps/desktop/debug_runtime_hook.py | 36 |  |
| apps/desktop/demo_ui.py | 591 | Panel, CountCard, Trace, AnalogGauge, SignalCard, SignalGrid, DemoDashboard, DTCPage, HypothesesPage, ReportsPage, TeachPage, label, action |
| apps/desktop/edge_resize.py | 86 | EdgeResizablePanel |
| apps/desktop/main.py | 520 | _close_backend_log, _close_llm_log, _is_port_open, _json_health, _backend_healthy, _llm_healthy, _appdata_log, _resolve_llama_server, _resolve_model_path, start_llama_server, stop_llama_server, _log_path, _backend_log_path, start_backend, stop_backend, run |
| apps/desktop/measurement_units.py | 17 | convert, display_records |
| apps/desktop/models.py | 84 | Vehicle, Session, TestCandidate, fuel_values, user_report_data |
| apps/desktop/prepare_windows_icon.py | 43 | main |
| apps/desktop/qt_early_runtime_hook.py | 13 |  |
| apps/desktop/qt_freeze_probe.py | 41 | stage |
| apps/desktop/stage_windows_icons.py | 71 | stage_icons, main |
| apps/desktop/storage.py | 26 | VehicleStore |
| apps/desktop/test_smoke.py | 12 | test_desktop_source_syntax |
| apps/desktop/tests/test_api_client.py | 187 | FakeResponse, client, test_request_normalizes_base_url_and_sets_timeout, test_default_backend_uses_local_fastapi_and_short_timeout, test_backend_port_is_shared_with_desktop_launcher, test_explicit_backend_url_overrides_local_port, test_empty_response_returns_empty_object, test_non_json_error_response_is_reported, test_json_detail_error_response_is_reported, test_request_exception_is_wrapped, test_public_api_methods_route_correctly, test_shutdown_releases_blocked_http_wait_and_prevents_new_requests, test_analysis_timeout_can_be_configured_without_slowing_health_checks, test_dtc_edit_preserves_measured_source_and_description |
| apps/desktop/tests/test_backend_worker_coverage.py | 100 | test_backend_worker_routes_to_uvicorn_with_explicit_config, test_backend_worker_fails_explicitly_for_invalid_backend_port, test_local_database_preparation_precedes_server_and_failures_block_startup |
| apps/desktop/tests/test_frozen_hook_contract.py | 67 | test_debug_runtime_hook_is_inert_when_not_opted_in, test_debug_runtime_hook_records_frozen_boot_environment, test_debug_runtime_hook_early_qtcore_diagnostic, test_production_early_qtcore_hook_never_requires_project_venv_changes |
| apps/desktop/tests/test_full_flow.py | 73 | Response, test_diagnostic_happy_path_sends_expected_payloads_and_order, test_diagnostic_flow_surfaces_backend_not_found_without_fake_success |
| apps/desktop/tests/test_gauge_bands.py | 34 | qapp, test_coolant_reference_and_fahrenheit, test_intake_temperature_does_not_use_coolant_reference |
| apps/desktop/tests/test_http_mock_integration.py | 121 | local_api, test_real_http_complete_manual_diagnostic_and_test_result, test_real_http_rejected_test_result_never_becomes_pass, test_real_http_offline_status_is_controlled_error, test_real_http_unknown_session_fails_explicitly |
| apps/desktop/tests/test_main_coverage_edges.py | 411 | test_json_health_handles_non_200_and_url_or_os_errors, test_llama_server_resolution_and_model_override, test_start_llama_server_respects_disable_health_missing_model_and_busy_port, test_appdata_and_backend_log_helpers_create_directory, test_run_handles_local_llm_start_error_then_runs_ui_and_cleanup, test_health_helpers_use_the_configured_health_urls, test_frozen_module_bootstrap_resolves_bundle_and_skips_inaccessible_candidates, _prepare_llama_server_test, test_llama_startup_adds_no_webui_and_waits_until_health_is_ready, test_llama_startup_timeout_swallows_failure_of_both_cleanup_attempts, test_frozen_backend_launches_bundled_executable_and_retries_health, test_backend_timeout_swallows_failure_of_both_cleanup_attempts, test_run_falls_back_to_absolute_ui_import_when_relative_import_fails, test_main_script_entrypoint_runs_without_starting_local_services, test_no_backend_never_starts_recovery_or_any_local_service, test_external_ai_runtime_does_not_launch_competing_llama_server, test_local_ai_flag_overrides_external_provider_for_managed_backend, test_local_ai_flag_rejects_external_backend_lifecycle, test_local_ai_flag_rejects_remotely_managed_llm_endpoint, test_remote_llm_endpoint_never_starts_a_local_model_process |
| apps/desktop/tests/test_main_helpers.py | 115 | test_is_port_open_closes_socket, test_json_health_returns_status_and_handles_network_errors, test_appdata_log_creates_app_directory, test_resolve_model_path_honors_environment_override, test_resolve_llama_server_uses_configured_existing_path, test_resolve_llama_server_ignores_missing_configured_path, test_start_llama_server_can_return_while_model_loads, test_start_llama_server_respects_disabled_flag, test_start_llama_server_skips_when_already_healthy, test_start_llama_server_skips_missing_model |
| apps/desktop/tests/test_main_lifecycle.py | 368 | isolate_process_state, _prepare_local_backend, test_start_backend_skips_remote_backend, test_start_backend_skips_when_health_check_passes, test_start_backend_reports_unhealthy_port_conflict, test_start_backend_starts_source_mode_and_waits_for_health, test_start_backend_wraps_uvicorn_missing_from_environment, test_start_backend_wraps_other_process_creation_errors, test_start_backend_reports_frozen_build_without_bundled_service, test_start_backend_reports_process_exit_during_startup, test_start_backend_times_out_and_terminates_process, test_stop_backend_terminates_running_process_and_closes_log, test_stop_backend_kills_process_when_graceful_stop_times_out, test_stop_backend_does_not_signal_already_exited_process, test_start_llama_server_skips_missing_executable, test_start_llama_server_skips_busy_unhealthy_port, test_start_llama_server_reports_spawn_error_and_closes_log, test_start_llama_server_returns_process_when_health_arrives, test_start_llama_server_reports_early_exit_and_closes_log, test_start_llama_server_times_out_and_terminates_process, test_stop_llama_server_kills_after_timeout_and_cleans_log, test_stop_llama_server_closes_log_even_without_process, test_run_always_stops_services_when_ui_returns, test_run_reports_backend_start_error_after_ui_and_cleanup, test_launcher_storage_selection_is_explicit, test_with_backend_flag_selects_local_sqlite_before_ui, test_no_backend_flag_does_not_spawn_services |
| apps/desktop/tests/test_models.py | 75 | test_vehicle_round_trip_preserves_all_fields, test_vehicle_missing_fields_use_safe_defaults, test_vehicle_accepts_numeric_year_string, test_vehicle_rejects_invalid_year, test_session_defaults_and_vehicle_reference, test_test_candidate_accepts_aliases_and_converts_types, test_test_candidate_defaults_when_optional_values_missing, test_user_report_removes_nested_session_ids_without_mutating_internal_data |
| apps/desktop/tests/test_negative_api_contract.py | 122 | ResponseStub, api, test_negative_http_status_is_never_reported_as_success, test_negative_non_object_error_body_does_not_raise_attribute_error, test_negative_html_error_body_falls_back_to_server_text, test_negative_network_errors_become_user_facing_api_errors, test_negative_malformed_success_payload_raises_controlled_api_error, test_language_parameter_has_safe_fallback, test_negative_record_limit_is_clamped, test_negative_connection_failure_cannot_create_session, test_negative_result_submission_does_not_mask_backend_failure |
| apps/desktop/tests/test_negative_storage.py | 68 | store, test_negative_corrupted_vehicle_storage_is_never_loaded, test_negative_file_permission_error_on_load_falls_back_safely, test_negative_failed_save_reports_error_and_does_not_fabricate_success, test_negative_empty_storage_data_does_not_create_fake_vehicle |
| apps/desktop/tests/test_prepare_windows_icon_coverage.py | 136 | test_icon_builder_requires_android_launcher_asset, test_icon_builder_resizes_small_source_and_creates_all_desktop_formats, test_icon_builder_rejects_missing_generated_output, test_icon_builder_rejects_invalid_ico_header, test_icon_script_entrypoint_runs_in_an_isolated_project_tree |
| apps/desktop/tests/test_qt_freeze_probe_coverage.py | 100 | test_qt_startup_probe_runs_main_path_and_reports_icon_state |
| apps/desktop/tests/test_real_backend_diagnostic_e2e.py | 226 | _CompatibleResponse, desktop_with_real_backend, _assert_no_unproven_hardware_diagnosis, test_w211_real_api_full_diagnostic_result_reanalysis_and_persistence, test_negative_real_backend_rejects_unknown_session_and_invalid_result, test_negative_real_backend_requires_analysis_before_decision_candidates, test_shared_registry_contract_reaches_real_backend |
| apps/desktop/tests/test_stage_windows_icons.py | 101 | test_stage_preserves_user_png_and_generates_consistent_assets, test_stage_does_not_modify_source_when_upscaling, test_stage_rejects_missing_source_and_source_inside_output, test_staging_accepts_tiny_but_valid_lossless_webp, test_stage_cli_respects_explicit_paths_without_touching_source, test_stage_invalid_png_does_not_overwrite_source |
| apps/desktop/tests/test_storage.py | 49 | test_load_returns_empty_when_file_does_not_exist, test_save_and_load_round_trip, test_load_handles_corrupt_json_and_invalid_shape, test_load_handles_missing_fields_in_vehicle_records |
| apps/desktop/tests/test_ui_pom.py | 2642 | DashboardPO, VehiclesPO, DiagnosticPO, LiveDataPO, ResultsPageObject, DevicesPO, NetworkPO, MemorySettings, FakeStore, qapp, vehicle, fake_api, window_factory, test_main_window_builds_reference_navigation_pages, test_top_navigation_and_main_menu_tiles_reach_all_13_pages, test_symptoms_and_diagnostic_results_have_separate_pages, test_navigation_selects_pages_and_live_data_request_is_guarded, test_dashboard_page_object_displays_online_vehicle_session_and_ecus, test_vehicles_page_object_lists_selects_and_displays_vehicle, test_vehicle_dialog_page_object_filters_catalog_and_converts_form, test_diagnostic_page_object_renders_evidence_hypotheses_and_questions, test_diagnostic_empty_hypotheses_are_explicit, test_live_data_page_object_handles_empty_and_populated_telemetry, test_tests_page_object_keeps_result_codes_canonical, test_devices_page_object_selects_device_and_builds_connection_config, test_devices_page_handles_no_selected_device, test_network_page_object_formats_passive_and_active_ecu_data, test_language_switch_translates_window_and_navigation, test_analyze_input_rejects_empty_evidence_and_dtc, test_analyze_input_worker_sends_symptom_and_dtc, test_main_window_selected_device_validation_does_not_start_worker, test_worker_run_emits_success_and_failure_signals, test_sparkline_handles_empty_constant_and_long_series, test_metric_card_initial_and_updated_values, test_translation_round_trips_dynamic_session_state_between_languages, test_new_session_offline_reports_error_without_starting_worker, test_new_session_online_runs_api_call_and_handles_result, test_refresh_telemetry_updates_current_session_and_ignores_stale_result, test_refresh_telemetry_reports_api_error_and_releases_in_flight_flag, test_record_selected_test_applies_recalculated_session_without_second_analysis, test_record_selected_test_requires_session_and_selection, test_live_ai_callback_formats_unavailable_provider_result, test_device_action_callback_replaces_device_and_updates_status, test_translation_helpers_preserve_non_string_values_and_unknown_language, test_vehicle_dialog_falls_back_when_offline_catalog_is_unreadable, test_vehicle_dialog_ignores_invalid_offline_rows_and_non_list_payload, test_settings_dialog_saves_language_and_theme, test_settings_dialog_cancel_does_not_change_preferences, test_add_vehicle_cancel_does_not_persist_or_start_session, test_add_vehicle_replaces_duplicate_profile_and_starts_new_session, test_delete_vehicle_reports_missing_selection_and_stale_index, test_delete_vehicle_respects_cancel_confirmation, test_delete_vehicle_removes_confirmed_profile_and_clears_active_vehicle, test_refresh_health_success_and_offline_callbacks, test_refresh_pages_isolates_a_page_refresh_failure, test_scan_devices_and_device_added_callbacks, test_probe_wifi_rejects_blank_host_and_runs_with_trimmed_host, test_device_connection_actions_dispatch_and_refresh, test_device_read_callbacks_render_results, test_session_created_resets_analysis_state_and_opens_diagnostic_page, test_analyze_input_supports_dtc_only_and_decision_callback, test_new_session_without_profiles_opens_vehicle_dialog, test_simulator_and_telemetry_actions_are_guarded_by_session, test_live_ai_success_and_defaults_update_page, test_active_probe_only_sends_known_ecu_identifiers, test_live_data_request_refresh_gates_and_loads_details, test_live_data_request_refresh_handles_provider_and_status_errors, test_live_data_poll_running_refreshes_telemetry_and_stops_when_stopped, test_resource_path_supports_source_and_frozen_layouts, test_ui_run_starts_without_optional_icon_assets, test_ui_run_applies_first_existing_icon_to_app_window_and_handle, test_windows_taskbar_icon_returns_early_for_null_icon, test_vehicle_dialog_handles_api_failure_and_malformed_offline_catalog, test_refresh_telemetry_handles_error_stale_session_and_success, test_live_ai_analysis_guards_missing_session_and_renders_fallback_or_success, test_close_waits_for_active_api_workers_before_destroying_qthreads, test_run_worker_rejects_new_background_jobs_after_shutdown_requested, test_shutdown_trace_is_opt_in_and_records_event_loop_stages, test_shutdown_trace_ignores_unwritable_report_directory, test_worker_finished_waits_then_releases_strong_reference, test_demo_dashboard_quick_actions_open_real_diagnostic_pages, test_demo_signals_never_mix_independent_channels, test_report_export_escapes_session_content, test_native_pdf_export_hides_session_id_and_preserves_diagnostic_content, test_pdf_export_surfaces_failure_without_success_message, test_history_open_clears_previous_vehicle_telemetry, test_live_details_from_previous_session_cannot_overwrite_current_session, test_refresh_preserves_vehicle_selection_and_cached_artwork, test_edit_dialog_keeps_custom_vehicle_and_uses_cached_catalog, test_edit_saved_vehicle_persists_replacement, test_language_refresh_requests_localized_data_and_discards_stale_response, test_empty_current_plan_does_not_count_historical_results, test_dashboard_labels_and_dynamic_lists_translate_after_refresh, test_dashboard_presentation_strings_have_hy_and_ru_translations, test_async_status_messages_use_selected_language_immediately, test_history_language_switch_rebuilds_labels_without_network_or_losing_selection, test_session_id_stays_internal_in_dashboard_diagnostics_and_history, test_backend_health_autoreconnect_is_non_modal, test_fastapi_health_timer_reconnects_without_modal_failures, test_backend_recovery_refreshes_provider_on_actual_live_data_navigation, test_connected_adapter_button_dispatches_backend_acquisition, test_test_results_have_one_visible_submission_path, test_backend_channel_labels_replace_hex_titles_but_keep_selection_ids, test_live_ai_response_refreshes_recommended_tests, test_generate_tests_action_uses_backend_analysis_and_plan, test_units_convert_display_without_mutating_evidence, test_live_simulator_inputs_switch_units_and_keep_physical_values, test_channel_order_does_not_shift_when_record_window_rotates, test_usb_selection_and_connect_send_serial_port_not_wifi_number, test_vehicle_selection_during_list_replacement_ignores_stale_index, test_added_widget_populates_names_and_renders_analog_values, test_backend_label_arriving_after_raw_samples_updates_selector, test_offline_channel_labels_match_backend_registry, test_window_closes_promptly_during_blocked_session_request, test_analog_widgets_fit_inside_cards_in_short_live_data_window, test_border_drag_grows_and_shrinks_card_and_restores_without_controls, test_settings_selects_display_for_all_widgets_and_preserves_size, test_ford_diesel_selection_does_not_split_fuel_into_letters, test_saved_diesel_profiles_load_as_one_fuel, test_diagnostic_vin_discovery_uses_backend_and_displays_measured_modules, test_launcher_uses_shared_3d_icons_and_compact_top_toolbar, test_launcher_3d_icons_resize_and_keep_all_tiles_without_scrollbars, test_every_workflow_has_3d_section_header, test_navigation_has_no_settings_buttons_or_scrollbars_in_all_languages, test_live_controls_wrap_without_horizontal_scroll, test_launcher_order_persists_and_keeps_workflow_links, test_launcher_keyboard_move_and_cancelled_external_drop, test_launcher_repairs_invalid_saved_order_without_losing_sections, test_launcher_drag_reorders_but_does_not_activate_the_dragged_tile, test_shared_vehicle_dialog_uses_backend_profiles_without_deleting_sessions, test_recorded_input_editor_updates_and_deletes_through_shared_api, test_common_backend_pdf_export_preserves_downloaded_bytes, test_shared_vehicle_profile_edit_and_confirmed_delete, _exercise_input_editor, test_save_analyze_auto_selects_and_preserves_selection_for_repeat_save, test_save_analyze_real_worker_has_busy_feedback_retry_and_session_ownership, test_save_analyze_empty_editor_is_explicitly_disabled, test_save_analyze_preserves_dtc_metadata_and_uses_fresh_recommendations_if_plan_fails |
| apps/desktop/tests/test_ui_widgets.py | 460 | FakeApp, qapp, test_ui_translation_covers_pages_and_switches_languages, test_desktop_icon_stage_preserves_input_and_generates_matching_formats, test_sparkline_limits_values_and_paints, test_metric_card_updates_displayed_value, test_vehicle_dialog_fallback_and_vehicle_conversion, test_vehicle_dialog_filters_catalog_and_selects_matching_vehicle, test_vehicle_dialog_handles_catalog_api_failure, test_dashboard_refresh_updates_metrics, test_vehicles_page_renders_and_selects_local_vehicles, test_diagnostic_page_formats_summary_and_refreshes_session, test_tests_page_builds_candidates_from_decision_payload, test_test_result_labels_are_localized_but_keep_canonical_values, test_devices_page_refresh_config_and_selection, test_network_page_formats_inferred_and_active_ecus, test_live_data_page_refresh_does_not_block_on_api_calls, test_refresh_telemetry_deduplicates_requests_and_discards_stale_sessions, test_live_data_poll_ignores_absent_session_and_reports_backend_error, test_diagnostic_summary_empty_hypotheses_are_explicit, test_live_data_reports_endpoint_state_not_global_backend_health, test_live_data_backend_offline_status_is_not_mislabeled_as_acquisition, test_acquisition_errors_follow_selected_ui_language, test_live_data_has_numeric_fields_without_sliders_and_tracks_units |
| apps/desktop/tests/test_vehicle_artwork.py | 205 | test_catalog_portraits_are_transparent_and_packaged_for_each_native_client, test_unknown_model_cannot_resolve_to_a_different_vehicle, test_native_portrait_and_fallback_render_with_requested_bounds, test_legacy_svg_assets_remain_valid_without_replacing_png_portraits, test_svg_is_used_only_when_matching_png_is_missing, test_backend_photo_is_async_cached_and_keeps_credit, test_real_qt_network_reply_loads_portrait_and_attribution, test_catalog_neon_manifest_covers_all_generations_and_replaced_originals, test_vehicle_neon_studio_preview_preserves_original_photo_pixels |
| apps/desktop/tests/test_verify_icons_negative.py | 138 | icon_assets, test_verify_staged_icon_pack_succeeds_without_real_windows_executable, test_negative_missing_staged_icon_fails_with_named_error, test_negative_bad_image_bytes_are_rejected, test_negative_small_png_is_rejected, test_negative_webp_size_mismatch_is_rejected, test_negative_webp_alpha_mismatch_is_rejected, test_negative_webp_visible_colors_mismatch_is_rejected, test_negative_icon_without_256_frame_is_rejected, test_windows_native_exe_icon_count_is_validated_when_available, test_negative_qt_fails_to_decode_icon, test_negative_invalid_json_report_target_fails_safely |
| apps/desktop/ui.py | 2358 | Worker, Sparkline, MetricCard, VehicleDialog, DashboardPage, VehiclesPage, SymptomsPage, CompactNavigation, AdaptiveMenuTile, MovableMenuTile, LauncherPage, DiagnosticPage, ResponsiveControls, LiveDataPage, TestsPage, DevicesPage, NetworkPage, MainWindow, _translation_patterns, _translated_text, _translate_ui_text, _translate_ui_block, _translate_known_ui_line, _navigation_icon, _menu_atlas, _page_icon, _resource_path, _set_windows_taskbar_icon, _trace_shutdown, run |
| apps/desktop/vehicle_artwork.py | 113 | NeonVehiclePreview, slug_piece, _root, artwork_path, _portrait_image, vehicle_pixmap, load_backend_portrait |
| apps/desktop/verify_icons.py | 164 | _resource_root, _embedded_icon_count, verify_icons |
