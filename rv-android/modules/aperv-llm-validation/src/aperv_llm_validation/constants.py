"""APE-RV pipeline constants — replicated from Java codebase (commit b2852dd)."""

# --- Image Processing (ImageProcessor.java) ---
MAX_EDGE_PX = 1000
JPEG_QUALITY = 80

# --- Qwen3-VL Vision Encoder ---
QWEN3_VL_PATCH_SIZE = 16
QWEN3_VL_MERGE_SIZE = 2
SMART_RESIZE_FACTOR = QWEN3_VL_PATCH_SIZE * QWEN3_VL_MERGE_SIZE  # 32
SMART_RESIZE_MIN_PIXELS = 3136  # 56 × 56
SMART_RESIZE_MAX_PIXELS = 10_035_200  # ~3169 × 3169

# --- Coordinate Normalization (CoordinateNormalizer.java) ---
QWEN_COORD_RANGE = 1000  # Qwen3-VL normalized coordinate range [0, 1000)

# --- Device Dimensions (standard Pixel emulator) ---
DEVICE_WIDTH = 1080
DEVICE_HEIGHT = 1920

# --- Boundary Rejection (LlmRouter.mapToModelAction) ---
BOUNDARY_TOP_RATIO = 0.05
BOUNDARY_BOTTOM_RATIO = 0.94

# --- Matching Algorithm (LlmRouter.mapToModelAction) ---
MIN_EUCLIDEAN_TOLERANCE = 50.0  # max(50, min(w,h)/2) — minimum Euclidean fallback tolerance

# --- No-Match Classification Thresholds ---
EDGE_MISS_THRESHOLD = 20  # max distance (px) to widget bound for edge_miss
TOLERANCE_MISS_MIN = 50  # min distance (px) from center for tolerance_miss
TOLERANCE_MISS_MAX = 100  # max distance (px) from center for tolerance_miss
GAP_THRESHOLD = 100  # min distance (px) for gap classification
FEW_WIDGETS_THRESHOLD = 2  # max clickable widgets for few_widgets

# --- Widget Class Names ---
INPUT_CLASS_NAMES = frozenset({
    "android.widget.EditText",
    "android.widget.AutoCompleteTextView",
    "android.widget.SearchView",
    "androidx.appcompat.widget.SearchView",
})

CONTAINER_CLASS_NAMES = frozenset({
    "android.widget.FrameLayout",
    "android.widget.LinearLayout",
    "android.widget.RelativeLayout",
    "androidx.constraintlayout.widget.ConstraintLayout",
    "android.view.ViewGroup",
})

# --- Quality Guardrail Thresholds ---
MAX_CONTAINER_RATE = 0.30
MIN_SEMANTIC_RATE = 0.50
MAX_BACK_RATE = 0.15
MAX_PER_APP_STD_DEV = 0.25

# --- Quality Score Weights ---
QUALITY_WEIGHT_MATCH = 0.60
QUALITY_WEIGHT_SEMANTIC = 0.20
QUALITY_WEIGHT_TYPE_TEXT = 0.10
QUALITY_WEIGHT_DIVERSITY = 0.10

# --- SGLang Defaults ---
DEFAULT_SGLANG_URL = "http://192.168.0.36:30000/v1"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MODEL = "default"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_RETRIES = 3

# --- Cache ---
CACHE_DB_NAME = "llm_responses.db"
