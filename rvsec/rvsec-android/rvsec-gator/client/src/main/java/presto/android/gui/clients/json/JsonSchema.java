package presto.android.gui.clients.json;

/**
 * Canonical Java-side names for every key emitted by
 * {@link JsonReportWriter}. The Python parser keeps a mirror copy in
 * {@code rv_static_analysis.parser.static.static_analysis_parser._JK};
 * {@link JsonSchemaKeysDump} prints the values one per line so the
 * Python-side parity test can read them via subprocess without parsing
 * the Java source.
 *
 * <p>Values still use the gh57 MOP nomenclature ("reachesTarget",
 * "directlyReachesTarget", "targetMethods"). Group 6 (C1f) renames them
 * atomically across producer + consumers; the constant <em>names</em>
 * here ({@code REACHES_TARGET}, {@code DIRECTLY_REACHES_TARGET},
 * {@code TARGET_METHODS}) already use the target nomenclature so the
 * rename diff in C1f is value-only.
 */
public final class JsonSchema {

	private JsonSchema() {
		// utility
	}

	/** Nested holder so reflection can {@code getDeclaredFields()} cleanly. */
	public static final class Keys {

		// Top-level metadata
		public static final String PACKAGE = "package";
		public static final String MAIN_ACTIVITY = "mainActivity";
		public static final String COMPLETE = "complete";

		// gh111 (INV-ANA-66) — the run's scope provenance. The artefact must answer,
		// on its own, which key filtered its contents, where that key came from, and
		// how many compiled classes it covered; PACKAGE is the manifest package
		// whatever key was used, so it cannot stand in for any of the three.
		// CLASS_DEFS_UNDER_KEY is the NET count (after RvsecAnalysisClient.isAppClass).
		public static final String CODE_PACKAGE = "codePackage";
		public static final String CODE_PACKAGE_SOURCE = "codePackageSource";
		public static final String CLASS_DEFS_UNDER_KEY = "class_defs_under_key";

		// Top-level sections
		public static final String REACHABILITY = "reachability";
		public static final String WINDOWS = "windows";
		public static final String TRANSITIONS = "transitions";
		public static final String COMPONENTS = "components";

		// Reachability section — per-class
		public static final String CLASS_NAME = "className";
		public static final String COMPONENT_TYPE = "componentType";
		public static final String IS_MAIN = "isMain";
		public static final String METHODS = "methods";

		// Reachability section — per-method
		public static final String NAME = "name";
		public static final String SIGNATURE = "signature";
		public static final String REACHABLE = "reachable";
		public static final String REACHES_TARGET = "reachesTarget";
		public static final String DIRECTLY_REACHES_TARGET = "directlyReachesTarget";

		// Windows section
		public static final String ID = "id";
		public static final String TYPE = "type";
		public static final String WIDGETS = "widgets";

		// Widget fields
		public static final String WIDGET_ID = "widgetId";
		public static final String WIDGET_NAME = "widgetName";
		public static final String WIDGET_CLASS = "widgetClass";
		public static final String ID_NAME = "idName";
		public static final String TEXT = "text";
		public static final String HINT = "hint";
		public static final String INPUT_TYPE = "inputType";
		public static final String ENTRIES = "entries";
		public static final String PROMPT = "prompt";
		public static final String SPINNER_MODE = "spinnerMode";
		public static final String CONTENT_DESCRIPTION = "contentDescription";
		public static final String TOOLTIP_TEXT = "tooltipText";
		public static final String LISTENERS = "listeners";
		public static final String EVENT_TYPE = "eventType";
		public static final String HANDLER = "handler";

		// Transitions section
		public static final String SOURCE_ID = "sourceId";
		public static final String TARGET_ID = "targetId";
		public static final String EVENTS = "events";

		// Components section
		public static final String ACTIVITIES = "activities";
		public static final String RECEIVERS = "receivers";
		public static final String SERVICES = "services";
		public static final String PROVIDERS = "providers";
		public static final String INTENT_FILTERS = "intentFilters";
		public static final String ACTIONS = "actions";
		public static final String CATEGORIES = "categories";
		public static final String EXPORTED = "exported";
		public static final String AUTHORITIES = "authorities";
		public static final String TARGET_METHODS = "targetMethods";

		// D15 (2026-05-29) — intent-filter data block + permission
		// fields that let consumers construct an Intent capable of
		// triggering the component (deep links via scheme/host/path,
		// MIME-typed sends, security-gated calls).
		public static final String DATA = "data";
		public static final String SCHEMES = "schemes";
		public static final String HOSTS = "hosts";
		public static final String PORTS = "ports";
		public static final String PATHS = "paths";
		public static final String PATH_PREFIXES = "pathPrefixes";
		public static final String PATH_PATTERNS = "pathPatterns";
		public static final String MIME_TYPES = "mimeTypes";
		public static final String PERMISSION = "permission";
		public static final String READ_PERMISSION = "readPermission";
		public static final String WRITE_PERMISSION = "writePermission";

		private Keys() {
			// constants only
		}
	}
}
