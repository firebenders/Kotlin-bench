# Constants - Task Instance Version File
MAP_REPO_TO_VERSION_PATHS = {
    "wordpress-mobile/WordPress-Android": ["version.properties"],
    "pinterest/ktlint": ["gradle.properties"],
    "ankidroid/Anki-Android": ["AnkiDroid/build.gradle"],
    "thunderbird/thunderbird-android": ["app-thunderbird/build.gradle.kts"],
    "Kotlin/kotlinx.coroutines": ["gradle.properties"],
    "Kotlin/kotlinx-datetime": ["gradle.properties"]
}

# Cosntants - Task Instance Version Regex Pattern
MAP_REPO_TO_VERSION_PATTERNS = {
    "wordpress-mobile/WordPress-Android": [
        r'versionName=([^\r\n]+)',
        r'versionCode=(\d+)'
    ],
    "pinterest/ktlint": [r'VERSION_NAME=([^\r\n]+)'],
    "ankidroid/Anki-Android": [
        r'versionName="([^"]+)"',
        r'versionCode=(\d+)'
    ],
    "thunderbird/thunderbird-android": [
        r'versionName\s*=\s*"([^"]+)"',
        r'versionCode\s*=\s*(\d+)'
    ],
    "Kotlin/kotlinx.coroutines": [r'(?m)^version=([^\r\n]+)'],
    "Kotlin/kotlinx-datetime": [r'(?m)^version=([^\r\n]+)']
}

SWE_BENCH_URL_RAW = "https://raw.githubusercontent.com/"
