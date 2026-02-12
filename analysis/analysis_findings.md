# Kotlin-bench Analysis Report

*Generated: 2026-02-05T13:57:12.232905*

*Total runs: 1600*

## Executive Summary

- **Total Tasks**: 100
- **Total Models**: 16
- **Total Runs**: 1600
- **Overall Pass Rate**: 27.2% (435/1600)
- **Total Estimated Cost**: $129.73
- **Best Model**: Opus 4.6 (48.0%)
- **Lowest Cost/Success**: Gemini Flash 3

## 1. Core Success Metrics

### Model Rankings by Pass Rate

| Rank | Model | Passed | Total | Pass Rate |
|------|-------|--------|-------|-----------|
| 1 | Opus 4.6 | 48 | 100 | 48.0% |
| 2 | Opus 4.5 | 46 | 100 | 46.0% |
| 3 | GPT-5.2 | 43 | 100 | 43.0% |
| 4 | Gemini Pro 3 | 41 | 100 | 41.0% |
| 5 | GPT-5.1-Codex | 41 | 100 | 41.0% |
| 6 | Gemini Flash 3 | 39 | 100 | 39.0% |
| 7 | GPT-5.2-Codex | 39 | 100 | 39.0% |
| 8 | Sonnet 4.5 | 37 | 100 | 37.0% |
| 9 | Sonnet 4 | 29 | 100 | 29.0% |
| 10 | kimi-k2.5 | 23 | 100 | 23.0% |
| 11 | GLM-4.7 | 22 | 100 | 22.0% |
| 12 | GLM-4.7-FP8 | 15 | 100 | 15.0% |
| 13 | GPT-4.1 | 12 | 100 | 12.0% |
| 14 | claude-3.5-sonn | 0 | 100 | 0.0% |
| 15 | claude-3.7-sonn | 0 | 100 | 0.0% |
| 16 | gemini-2.5-pro | 0 | 100 | 0.0% |

### Pass Rate by Repository

| Repository | Tasks | Passed | Total | Pass Rate |
|------------|-------|--------|-------|-----------|
| Kotlin/kotlinx.coroutines | 12 | 74 | 192 | 38.5% |
| pinterest/ktlint | 36 | 178 | 576 | 30.9% |
| Kotlin/kotlinx-datetime | 6 | 29 | 96 | 30.2% |
| ankidroid/Anki-Android | 22 | 79 | 352 | 22.4% |
| thunderbird/thunderbird-android | 6 | 19 | 96 | 19.8% |
| wordpress-mobile/WordPress-Android | 18 | 56 | 288 | 19.4% |

### Task Difficulty Distribution

- **Easy** (all models passed): 0 (0%)
- **Medium** (some models passed): 67 (67%)
- **Hard** (no model passed): 33 (33%)

## 2. Timing Analysis

### Speed Rankings

| Rank | Model | Avg Duration |
|------|-------|--------------|
| 1 | gemini-2.5-pro | 0.5s |
| 2 | claude-3.5-sonn | 0.6s |
| 3 | claude-3.7-sonn | 0.7s |
| 4 | GPT-4.1 | 34.0s |
| 5 | GPT-5.2-Codex | 182.9s |
| 6 | Sonnet 4 | 226.2s |
| 7 | GPT-5.1-Codex | 352.7s |
| 8 | kimi-k2.5 | 393.4s |
| 9 | Opus 4.6 | 421.0s |
| 10 | Gemini Flash 3 | 460.3s |
| 11 | GPT-5.2 | 473.4s |
| 12 | Opus 4.5 | 518.5s |
| 13 | Gemini Pro 3 | 550.0s |
| 14 | Sonnet 4.5 | 691.4s |
| 15 | GLM-4.7-FP8 | 976.1s |
| 16 | GLM-4.7 | 1008.1s |

### Duration by Outcome

| Model | Avg (Pass) | Avg (Fail) | Faster When |
|-------|------------|------------|-------------|
| claude-3.5-sonn | 0.0s | 0.6s | Failing |
| claude-3.7-sonn | 0.0s | 0.7s | Failing |
| Opus 4.5 | 518.1s | 518.7s | Passing |
| Opus 4.6 | 337.5s | 498.0s | Passing |
| Sonnet 4 | 185.0s | 243.0s | Passing |
| Sonnet 4.5 | 646.3s | 717.9s | Passing |
| gemini-2.5-pro | 0.0s | 0.5s | Failing |
| Gemini Flash 3 | 390.3s | 505.1s | Passing |
| Gemini Pro 3 | 562.1s | 541.6s | Failing |
| GPT-4.1 | 19.3s | 36.0s | Passing |
| GPT-5.1-Codex | 305.3s | 388.6s | Passing |
| GPT-5.2 | 452.7s | 489.0s | Passing |
| GPT-5.2-Codex | 110.6s | 229.2s | Passing |
| kimi-k2.5 | 418.0s | 385.8s | Failing |
| GLM-4.7 | 1070.1s | 990.6s | Failing |
| GLM-4.7-FP8 | 1024.5s | 960.0s | Failing |

## 3. Task Categorization

### Unique Solves (Tasks only one model solved)

- **Gemini Flash 3**: 2 unique solves
  - `Kotlin__kotlinx.coroutines-4038`
  - `wordpress-mobile__WordPress-Android-20756`
- **Opus 4.6**: 2 unique solves
  - `ankidroid__Anki-Android-14652`
  - `ankidroid__Anki-Android-16400`
- **GPT-5.2**: 2 unique solves
  - `wordpress-mobile__WordPress-Android-19574`
  - `wordpress-mobile__WordPress-Android-20057`
- **GPT-5.1-Codex**: 1 unique solves
  - `ankidroid__Anki-Android-17867`
- **GLM-4.7**: 1 unique solves
  - `pinterest__ktlint-2126`
- **Opus 4.5**: 1 unique solves
  - `wordpress-mobile__WordPress-Android-19730`

### High Variance Tasks (Some pass, some fail)

| Task | Passed By | Pass Count |
|------|-----------|------------|
| `Kotlin__kotlinx.coroutines-4038` | Gemini Flash 3 | 1/16 |
| `ankidroid__Anki-Android-14652` | Opus 4.6 | 1/16 |
| `ankidroid__Anki-Android-16400` | Opus 4.6 | 1/16 |
| `ankidroid__Anki-Android-17867` | GPT-5.1-Codex | 1/16 |
| `pinterest__ktlint-2126` | GLM-4.7 | 1/16 |
| `wordpress-mobile__WordPress-Android-19574` | GPT-5.2 | 1/16 |
| `wordpress-mobile__WordPress-Android-19730` | Opus 4.5 | 1/16 |
| `wordpress-mobile__WordPress-Android-20057` | GPT-5.2 | 1/16 |
| `wordpress-mobile__WordPress-Android-20756` | Gemini Flash 3 | 1/16 |
| `Kotlin__kotlinx-datetime-472` | Opus 4.6, Sonnet 4 | 2/16 |

## 4. Tool Usage Analysis

### Tool Calls by Model

| Model | Total Calls | Avg/Task | Top Tools |
|-------|-------------|----------|-----------|
| claude-3.5-sonn | 0 | 0.0 |  |
| claude-3.7-sonn | 0 | 0.0 |  |
| Opus 4.5 | 3360 | 33.6 | read:1194, run_terminal_cmd:662, grep:575 |
| Opus 4.6 | 4406 | 44.1 | read:1533, run_terminal_cmd:1040, grep:914 |
| Sonnet 4 | 3184 | 31.8 | read:963, grep:824, edit:644 |
| Sonnet 4.5 | 4674 | 46.7 | read:1301, run_terminal_cmd:1066, grep:793 |
| gemini-2.5-pro | 0 | 0.0 |  |
| Gemini Flash 3 | 4572 | 45.7 | read:1390, run_terminal_cmd:896, grep:749 |
| Gemini Pro 3 | 2606 | 26.1 | read:771, run_terminal_cmd:563, edit:471 |
| GPT-4.1 | 1353 | 13.5 | read:714, grep:338, edit:125 |
| GPT-5.1-Codex | 3218 | 32.2 | read:1022, grep:906, edit:691 |
| GPT-5.2 | 3576 | 35.8 | read:1229, grep:958, edit:593 |
| GPT-5.2-Codex | 1935 | 19.4 | read:751, grep:474, edit:404 |
| kimi-k2.5 | 2897 | 29.0 | read:1145, run_terminal_cmd:622, grep:461 |
| GLM-4.7 | 4523 | 45.2 | read:1478, run_terminal_cmd:982, grep:760 |
| GLM-4.7-FP8 | 1703 | 17.0 | read:638, grep:476, edit:214 |

### IntelliJ Semantic Tools Usage

| Model | read_lints | go_to_def | find_usages | rename | delete | Total |
|-------|------------|-----------|-------------|--------|--------|-------|
| claude-3.5-sonn | 0 | 0 | 0 | 0 | 0 | 0 |
| claude-3.7-sonn | 0 | 0 | 0 | 0 | 0 | 0 |
| Opus 4.5 | 193 | 9 | 23 | 0 | 4 | 229 |
| Opus 4.6 | 106 | 53 | 24 | 0 | 2 | 185 |
| Sonnet 4 | 347 | 13 | 20 | 0 | 3 | 383 |
| Sonnet 4.5 | 302 | 3 | 19 | 0 | 11 | 335 |
| gemini-2.5-pro | 0 | 0 | 0 | 0 | 0 | 0 |
| Gemini Flash 3 | 84 | 48 | 57 | 1 | 5 | 195 |
| Gemini Pro 3 | 65 | 27 | 25 | 0 | 0 | 117 |
| GPT-4.1 | 103 | 5 | 2 | 0 | 0 | 110 |
| GPT-5.1-Codex | 126 | 50 | 5 | 0 | 2 | 183 |
| GPT-5.2 | 233 | 27 | 5 | 1 | 4 | 270 |
| GPT-5.2-Codex | 122 | 49 | 4 | 0 | 14 | 189 |
| kimi-k2.5 | 50 | 5 | 11 | 0 | 5 | 71 |
| GLM-4.7 | 172 | 5 | 8 | 0 | 3 | 188 |
| GLM-4.7-FP8 | 140 | 3 | 2 | 0 | 0 | 145 |

### Tool-Success Correlation Patterns

*Comparing avg tool usage between passing and failing attempts on the same task.*

*Negative correlation = tool used MORE when failing (struggling models explore more)*

| Tool | Correlation | Tasks | Insight |
|------|-------------|-------|---------|
| run_terminal_cmd | -0.005 | 100 | Similar usage |
| edit | -0.062 | 100 | Slightly more when failing |
| delete_file | -0.089 | 80 | Slightly more when failing |
| read | -0.109 | 100 | Slightly more when failing |
| grep | -0.116 | 100 | Slightly more when failing |
| read_lints | -0.126 | 100 | Slightly more when failing |
| write | -0.127 | 100 | Slightly more when failing |
| go_to_definition | -0.158 | 77 | Slightly more when failing |
| list_dir | -0.160 | 100 | Slightly more when failing |
| glob | -0.171 | 98 | Slightly more when failing |
| find_usages | -0.260 | 58 | Overused when struggling |
| delete_symbol | -0.272 | 13 | Overused when struggling |

### High Tool-Variance Tasks

*Tasks where models used very different numbers of tools*

| Task | Min Tools | Max Tools | Std Dev | Pass/Fail |
|------|-----------|-----------|---------|-----------|
| `ankidroid__Anki-Android-14738` | 0 | 167 | 59.7 | 2/16 |
| `wordpress-mobile__WordPress-Android-1942...` | 0 | 138 | 48.8 | 3/16 |
| `pinterest__ktlint-2068` | 0 | 131 | 46.6 | 0/16 |
| `ankidroid__Anki-Android-14652` | 0 | 146 | 44.0 | 1/16 |
| `ankidroid__Anki-Android-15597` | 0 | 124 | 39.9 | 3/16 |
| `ankidroid__Anki-Android-15539` | 0 | 121 | 39.4 | 2/16 |
| `thunderbird__thunderbird-android-8267` | 0 | 119 | 37.2 | 0/16 |
| `pinterest__ktlint-1851` | 0 | 111 | 37.1 | 7/16 |
| `ankidroid__Anki-Android-16400` | 0 | 103 | 37.0 | 1/16 |
| `pinterest__ktlint-1920` | 0 | 108 | 33.6 | 0/16 |

### Example: Per-Task Tool Comparison

*Detailed tool usage for select high-variance tasks*

**ankidroid__Anki-Android-14738** (2/16 passed)

| Model | Tools Used | Passed | Top Tools |
|-------|------------|--------|-----------|
| Opus 4.5 | 114 | Yes | run_terminal_cmd:49, read:32, grep:15 |
| GPT-5.2 | 129 | Yes | read:40, grep:40, edit:18 |
| Gemini Pro 3 | 0 | No |  |
| gemini-2.5-pro | 0 | No |  |
| Sonnet 4 | 0 | No |  |
| claude-3.7-sonn | 0 | No |  |
| claude-3.5-sonn | 0 | No |  |
| GPT-4.1 | 5 | No | read:5 |
| GLM-4.7 | 44 | No | read:21, grep:13, list_dir:4 |
| GPT-5.2-Codex | 74 | No | read:26, grep:25, edit:16 |
| Sonnet 4.5 | 81 | No | read:35, grep:22, edit:14 |
| GPT-5.1-Codex | 99 | No | grep:45, read:27, edit:17 |
| Gemini Flash 3 | 100 | No | read:31, grep:26, edit:23 |
| GLM-4.7-FP8 | 107 | No | grep:45, read:33, edit:12 |
| kimi-k2.5 | 148 | No | read:58, grep:36, run_terminal_cmd:28 |
| Opus 4.6 | 167 | No | run_terminal_cmd:73, read:52, grep:25 |

**wordpress-mobile__WordPress-Android-19424** (3/16 passed)

| Model | Tools Used | Passed | Top Tools |
|-------|------------|--------|-----------|
| kimi-k2.5 | 59 | Yes | read:23, grep:13, run_terminal_cmd:12 |
| GPT-5.2 | 67 | Yes | edit:29, read:18, grep:16 |
| Opus 4.6 | 93 | Yes | grep:37, read:30, run_terminal_cmd:10 |
| gemini-2.5-pro | 0 | No |  |
| GLM-4.7-FP8 | 0 | No |  |
| claude-3.7-sonn | 0 | No |  |
| claude-3.5-sonn | 0 | No |  |
| Gemini Pro 3 | 10 | No | read:6, list_dir:3, grep:1 |
| GPT-4.1 | 17 | No | read:14, delete_file:3 |
| GPT-5.2-Codex | 71 | No | edit:20, grep:17, read:16 |
| Gemini Flash 3 | 83 | No | edit:28, read:19, grep:18 |
| GLM-4.7 | 87 | No | read:33, run_terminal_cmd:13, grep:11 |
| Sonnet 4 | 88 | No | read:31, grep:22, edit:18 |
| Opus 4.5 | 113 | No | edit:35, read:32, grep:26 |
| GPT-5.1-Codex | 129 | No | grep:53, edit:38, read:22 |
| Sonnet 4.5 | 138 | No | grep:39, read:28, run_terminal_cmd:28 |

**ankidroid__Anki-Android-14652** (1/16 passed)

| Model | Tools Used | Passed | Top Tools |
|-------|------------|--------|-----------|
| Opus 4.6 | 146 | Yes | run_terminal_cmd:78, grep:33, read:21 |
| gemini-2.5-pro | 0 | No |  |
| GPT-4.1 | 0 | No |  |
| claude-3.7-sonn | 0 | No |  |
| claude-3.5-sonn | 0 | No |  |
| Gemini Pro 3 | 5 | No | read:5 |
| Sonnet 4 | 36 | No | grep:15, read:12, edit:6 |
| GPT-5.2 | 42 | No | read:15, grep:13, edit:9 |
| GPT-5.2-Codex | 48 | No | grep:19, read:17, edit:8 |
| Opus 4.5 | 58 | No | read:21, grep:18, edit:8 |
| kimi-k2.5 | 63 | No | read:23, grep:19, write:6 |
| GLM-4.7-FP8 | 65 | No | read:22, grep:21, edit:9 |
| Sonnet 4.5 | 69 | No | read:30, grep:13, edit:7 |
| Gemini Flash 3 | 80 | No | read:24, grep:22, edit:15 |
| GPT-5.1-Codex | 80 | No | grep:29, read:26, edit:19 |
| GLM-4.7 | 120 | No | read:38, run_terminal_cmd:36, grep:16 |

## 5. Linter Tool Analysis

### read_lints Effectiveness

| Model | Total Calls | Empty (no errors) | Productive (found errors) | Empty Rate |
|-------|-------------|-------------------|---------------------------|------------|
| claude-3.5-sonn | 0 | 0 | 0 | 0% |
| claude-3.7-sonn | 0 | 0 | 0 | 0% |
| Opus 4.5 | 193 | 183 | 10 | 95% |
| Opus 4.6 | 106 | 0 | 0 | 0% |
| Sonnet 4 | 347 | 298 | 49 | 86% |
| Sonnet 4.5 | 302 | 288 | 14 | 95% |
| gemini-2.5-pro | 0 | 0 | 0 | 0% |
| Gemini Flash 3 | 84 | 78 | 5 | 93% |
| Gemini Pro 3 | 65 | 63 | 2 | 97% |
| GPT-4.1 | 103 | 70 | 31 | 68% |
| GPT-5.1-Codex | 126 | 111 | 14 | 88% |
| GPT-5.2 | 233 | 217 | 15 | 93% |
| GPT-5.2-Codex | 122 | 113 | 9 | 93% |
| kimi-k2.5 | 50 | 0 | 0 | 0% |
| GLM-4.7 | 172 | 0 | 0 | 0% |
| GLM-4.7-FP8 | 140 | 124 | 14 | 89% |

## 6. Conversation Metrics

### Average Metrics by Model

| Model | Avg Messages | Avg Turns | Avg Input Tokens | Avg Output Tokens |
|-------|--------------|-----------|------------------|-------------------|
| claude-3.5-sonn | 1 | 0 | 1150 | 0 |
| claude-3.7-sonn | 1 | 0 | 1150 | 0 |
| Opus 4.5 | 63 | 29 | 34968 | 8785 |
| Opus 4.6 | 85 | 39 | 31677 | 11819 |
| Sonnet 4 | 66 | 33 | 22385 | 6843 |
| Sonnet 4.5 | 91 | 44 | 31948 | 11537 |
| gemini-2.5-pro | 1 | 0 | 1150 | 0 |
| Gemini Flash 3 | 93 | 46 | 53381 | 4687 |
| Gemini Pro 3 | 53 | 26 | 38456 | 2943 |
| GPT-4.1 | 27 | 12 | 17732 | 1327 |
| GPT-5.1-Codex | 66 | 33 | 33491 | 3984 |
| GPT-5.2 | 66 | 29 | 34276 | 6128 |
| GPT-5.2-Codex | 39 | 18 | 22535 | 2737 |
| kimi-k2.5 | 54 | 25 | 29674 | 6015 |
| GLM-4.7 | 88 | 42 | 34776 | 9729 |
| GLM-4.7-FP8 | 32 | 14 | 15270 | 1970 |

## 7. Code Change Metrics

### Patch Size by Model

| Model | Avg Lines Added | Avg Lines Removed | Avg Files Changed |
|-------|-----------------|-------------------|-------------------|
| claude-3.5-sonn | 1.8 | 4.2 | 1.1 |
| claude-3.7-sonn | 1.8 | 4.2 | 1.1 |
| Opus 4.5 | 89.8 | 24.0 | 4.4 |
| Opus 4.6 | 31.8 | 16.0 | 3.7 |
| Sonnet 4 | 96.7 | 18.3 | 4.5 |
| Sonnet 4.5 | 155.7 | 18.8 | 5.6 |
| gemini-2.5-pro | 1.8 | 4.2 | 1.1 |
| Gemini Flash 3 | 60.3 | 21.3 | 5.4 |
| Gemini Pro 3 | 47.0 | 14.8 | 3.0 |
| GPT-4.1 | 8.8 | 22.6 | 1.9 |
| GPT-5.1-Codex | 57.9 | 30.9 | 4.8 |
| GPT-5.2 | 65.3 | 17.1 | 4.0 |
| GPT-5.2-Codex | 31.0 | 17.9 | 3.4 |
| kimi-k2.5 | 45.1 | 10.4 | 2.8 |
| GLM-4.7 | 156.1 | 29.8 | 5.0 |
| GLM-4.7-FP8 | 26.8 | 8.7 | 2.2 |

### Patch Size: Pass vs Fail

| Model | Avg Lines (Pass) | Avg Lines (Fail) |
|-------|------------------|------------------|
| claude-3.5-sonn | 0.0 | 6.0 |
| claude-3.7-sonn | 0.0 | 6.0 |
| Opus 4.5 | 92.2 | 132.3 |
| Opus 4.6 | 44.2 | 51.1 |
| Sonnet 4 | 70.3 | 133.2 |
| Sonnet 4.5 | 161.5 | 182.2 |
| gemini-2.5-pro | 0.0 | 6.0 |
| Gemini Flash 3 | 81.2 | 81.8 |
| Gemini Pro 3 | 56.1 | 65.8 |
| GPT-4.1 | 11.2 | 34.2 |
| GPT-5.1-Codex | 56.7 | 111.2 |
| GPT-5.2 | 61.1 | 98.4 |
| GPT-5.2-Codex | 29.1 | 61.5 |
| kimi-k2.5 | 42.4 | 59.4 |
| GLM-4.7 | 69.9 | 218.6 |
| GLM-4.7-FP8 | 43.1 | 34.2 |

## 8. Cost Analysis

*Cost estimates include prompt caching: cached input tokens priced at 10-25% of normal input rate*

### Cost by Model

| Model | Total Cost | Avg/Task | Cost/Success | Cache Hit Rate |
|-------|------------|----------|--------------|----------------|
| claude-3.5-sonn | $0.12 | $0.00 | N/A | 0% |
| claude-3.7-sonn | $0.12 | $0.00 | N/A | 0% |
| Opus 4.5 | $26.15 | $0.26 | $0.57 | 84% |
| Opus 4.6 | $33.29 | $0.33 | $0.69 | 85% |
| Sonnet 4 | $11.86 | $0.12 | $0.41 | 85% |
| Sonnet 4.5 | $19.59 | $0.20 | $0.53 | 85% |
| gemini-2.5-pro | $0.12 | $0.00 | N/A | 0% |
| Gemini Flash 3 | $2.04 | $0.02 | $0.05 | 85% |
| Gemini Pro 3 | $5.44 | $0.05 | $0.13 | 84% |
| GPT-4.1 | $2.74 | $0.03 | $0.23 | 76% |
| GPT-5.1-Codex | $4.98 | $0.05 | $0.12 | 85% |
| GPT-5.2 | $10.01 | $0.10 | $0.23 | 85% |
| GPT-5.2-Codex | $4.83 | $0.05 | $0.12 | 83% |
| kimi-k2.5 | $4.13 | $0.04 | $0.18 | 83% |
| GLM-4.7 | $3.35 | $0.03 | $0.15 | 84% |
| GLM-4.7-FP8 | $0.97 | $0.01 | $0.06 | 82% |

### Token Breakdown by Model

| Model | Total Input | Cached | Uncached | Output |
|-------|-------------|--------|----------|--------|
| claude-3.5-sonn | 114,962 | 0 | 114,962 | 0 |
| claude-3.7-sonn | 114,962 | 0 | 114,962 | 0 |
| Opus 4.5 | 3,496,782 | 2,955,738 | 541,044 | 878,522 |
| Opus 4.6 | 3,167,739 | 2,687,511 | 480,228 | 1,181,887 |
| Sonnet 4 | 2,238,493 | 1,895,112 | 343,381 | 684,262 |
| Sonnet 4.5 | 3,194,813 | 2,704,569 | 490,244 | 1,153,685 |
| gemini-2.5-pro | 114,962 | 0 | 114,962 | 0 |
| Gemini Flash 3 | 5,338,076 | 4,533,038 | 805,038 | 468,666 |
| Gemini Pro 3 | 3,845,602 | 3,210,600 | 635,002 | 294,292 |
| GPT-4.1 | 1,773,173 | 1,340,166 | 433,007 | 132,695 |
| GPT-5.1-Codex | 3,349,136 | 2,833,681 | 515,455 | 398,407 |
| GPT-5.2 | 3,427,566 | 2,899,042 | 528,524 | 612,837 |
| GPT-5.2-Codex | 2,253,499 | 1,869,938 | 383,561 | 273,663 |
| kimi-k2.5 | 2,967,353 | 2,461,536 | 505,817 | 601,523 |
| GLM-4.7 | 3,477,580 | 2,924,733 | 552,847 | 972,905 |
| GLM-4.7-FP8 | 1,527,022 | 1,252,681 | 274,341 | 196,977 |

### Cost per Success Rankings

*Lower is better - cost to achieve one successful task*

| Rank | Model | Cost/Success |
|------|-------|--------------|
| 1 | Gemini Flash 3 | $0.05 |
| 2 | GLM-4.7-FP8 | $0.06 |
| 3 | GPT-5.1-Codex | $0.12 |
| 4 | GPT-5.2-Codex | $0.12 |
| 5 | Gemini Pro 3 | $0.13 |
| 6 | GLM-4.7 | $0.15 |
| 7 | kimi-k2.5 | $0.18 |
| 8 | GPT-4.1 | $0.23 |
| 9 | GPT-5.2 | $0.23 |
| 10 | Sonnet 4 | $0.41 |
| 11 | Sonnet 4.5 | $0.53 |
| 12 | Opus 4.5 | $0.57 |
| 13 | Opus 4.6 | $0.69 |

## Appendix: Unsolved Tasks

The following 33 tasks were not solved by any model:

- `Kotlin__kotlinx-datetime-360`
- `Kotlin__kotlinx-datetime-367`
- `Kotlin__kotlinx.coroutines-3719`
- `Kotlin__kotlinx.coroutines-3731`
- `ankidroid__Anki-Android-14182`
- `ankidroid__Anki-Android-14360`
- `ankidroid__Anki-Android-14769`
- `ankidroid__Anki-Android-15557`
- `ankidroid__Anki-Android-17125`
- `pinterest__ktlint-1766`
- `pinterest__ktlint-1849`
- `pinterest__ktlint-1853`
- `pinterest__ktlint-1920`
- `pinterest__ktlint-1944`
- `pinterest__ktlint-1997`
- `pinterest__ktlint-2060`
- `pinterest__ktlint-2068`
- `pinterest__ktlint-2087`
- `pinterest__ktlint-2116`
- `pinterest__ktlint-2132`
- ... and 13 more
