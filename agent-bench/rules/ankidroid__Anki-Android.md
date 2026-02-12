# Project Rules for AnkiDroid

## Scope your changes carefully

Before editing, list the files you plan to change and confirm each is necessary. A good fix typically touches 1-4 source files. If you're about to edit more than 5 files, pause and reconsider whether you're over-scoping.

Fix the root cause, not the symptom. Trace the bug to its origin before making changes. The fix belongs in the file with the underlying logic error, not in files that merely trigger or surface the bug.

## Do NOT modify build or Gradle files

Do not modify `build.gradle`, `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties`, or any file under `buildSrc/`. These files are managed separately and changes to them will break the build environment.

## Do NOT modify locale/translation resource files

Never modify localized resource files in directories matching `values-*/` (e.g., `values-fr/`, `values-de/`, `values-zh-rCN/`). If you need to change a string or array resource, only modify the default `values/` directory. Localized translations are managed by a separate localization system (Crowdin) and must never be edited directly.

## Do NOT modify existing test files

Do not modify, rename, or delete any existing test files (files under `src/test/` or `src/androidTest/`). Your task is to fix source code, not update tests.

## Do NOT update documentation or changelogs

Do not update `CHANGELOG.md`, `README.md`, `.editorconfig`, or files in `docs/` directories. Focus only on source code changes.

## AnkiDroid architecture notes

- The card viewer system has two main paths: `AbstractFlashcardViewer` (legacy) and the newer `CardViewerFragment`-based viewer. Check which one the issue references before editing.
- JavaScript bridge code lives in both Kotlin (`AnkiDroidJsAPI.kt`) and JS (`AnkiDroid/src/main/assets/scripts/`). Many card display bugs require changes in both Kotlin and JS files.
- Preferences are defined across multiple XML files (`preferences.xml`, `10-preferences.xml`, `11-arrays.xml`) and Kotlin fragments (`*SettingsFragment.kt`). A preference change often requires edits to both the XML definition and the Kotlin handler.
- `ViewerCommand` is an enum that maps to both UI actions and preference keys. Adding a new command typically requires changes to `ViewerCommand.kt`, `UsageAnalytics.kt`, the relevant preferences XML, and the reviewer UI.
