# Kotlin-bench Analysis Report

*Generated: 2026-01-07T09:14:59.778987*

*Total runs: 800*

## Executive Summary

- **Total Tasks**: 100
- **Total Models**: 8
- **Total Runs**: 800
- **Overall Pass Rate**: 32.9% (263/800)
- **Total Estimated Cost**: $77.18
- **Best Model**: Opus 4.5 (46.0%)
- **Lowest Cost/Success**: Gemini Flash 3

## 1. Core Success Metrics

### Model Rankings by Pass Rate

| Rank | Model | Passed | Total | Pass Rate |
|------|-------|--------|-------|-----------|
| 1 | Opus 4.5 | 46 | 100 | 46.0% |
| 2 | GPT-5.2 | 43 | 100 | 43.0% |
| 3 | Gemini Pro 3 | 41 | 100 | 41.0% |
| 4 | Gemini Flash 3 | 39 | 100 | 39.0% |
| 5 | Sonnet 4.5 | 37 | 100 | 37.0% |
| 6 | Sonnet 4 | 29 | 100 | 29.0% |
| 7 | GLM-4.7-FP8 | 15 | 100 | 15.0% |
| 8 | GLM-4.7 | 13 | 100 | 13.0% |

### Pass Rate by Repository

| Repository | Tasks | Passed | Total | Pass Rate |
|------------|-------|--------|-------|-----------|
| Kotlin/kotlinx.coroutines | 12 | 46 | 96 | 47.9% |
| pinterest/ktlint | 36 | 109 | 288 | 37.8% |
| Kotlin/kotlinx-datetime | 6 | 16 | 48 | 33.3% |
| ankidroid/Anki-Android | 22 | 45 | 176 | 25.6% |
| thunderbird/thunderbird-android | 6 | 12 | 48 | 25.0% |
| wordpress-mobile/WordPress-Android | 18 | 35 | 144 | 24.3% |

### Task Difficulty Distribution

- **Easy** (all models passed): 4 (4%)
- **Medium** (some models passed): 58 (58%)
- **Hard** (no model passed): 38 (38%)

## 2. Timing Analysis

### Speed Rankings

| Rank | Model | Avg Duration |
|------|-------|--------------|
| 1 | GLM-4.7 | 34.9s |
| 2 | Sonnet 4 | 226.2s |
| 3 | Gemini Flash 3 | 460.3s |
| 4 | GPT-5.2 | 473.4s |
| 5 | Opus 4.5 | 518.5s |
| 6 | Gemini Pro 3 | 550.0s |
| 7 | Sonnet 4.5 | 691.4s |
| 8 | GLM-4.7-FP8 | 976.1s |

### Duration by Outcome

| Model | Avg (Pass) | Avg (Fail) | Faster When |
|-------|------------|------------|-------------|
| Opus 4.5 | 518.1s | 518.7s | Passing |
| Sonnet 4 | 185.0s | 243.0s | Passing |
| Sonnet 4.5 | 646.3s | 717.9s | Passing |
| Gemini Flash 3 | 390.3s | 505.1s | Passing |
| Gemini Pro 3 | 562.1s | 541.6s | Failing |
| GPT-5.2 | 452.7s | 489.0s | Passing |
| GLM-4.7 | 50.2s | 32.6s | Failing |
| GLM-4.7-FP8 | 1024.5s | 960.0s | Failing |

## 3. Task Categorization

### Unique Solves (Tasks only one model solved)

- **Gemini Flash 3**: 4 unique solves
  - `Kotlin__kotlinx.coroutines-4038`
  - `ankidroid__Anki-Android-14859`
  - `wordpress-mobile__WordPress-Android-20103`
  - ... and 1 more
- **GPT-5.2**: 4 unique solves
  - `pinterest__ktlint-1996`
  - `wordpress-mobile__WordPress-Android-19424`
  - `wordpress-mobile__WordPress-Android-19574`
  - ... and 1 more
- **Opus 4.5**: 2 unique solves
  - `ankidroid__Anki-Android-15539`
  - `wordpress-mobile__WordPress-Android-19730`
- **Sonnet 4**: 1 unique solves
  - `Kotlin__kotlinx-datetime-472`
- **Gemini Pro 3**: 1 unique solves
  - `pinterest__ktlint-2107`

### High Variance Tasks (Some pass, some fail)

| Task | Passed By | Pass Count |
|------|-----------|------------|
| `Kotlin__kotlinx-datetime-472` | Sonnet 4 | 1/8 |
| `Kotlin__kotlinx.coroutines-4038` | Gemini Flash 3 | 1/8 |
| `ankidroid__Anki-Android-14859` | Gemini Flash 3 | 1/8 |
| `ankidroid__Anki-Android-15539` | Opus 4.5 | 1/8 |
| `pinterest__ktlint-1996` | GPT-5.2 | 1/8 |
| `pinterest__ktlint-2107` | Gemini Pro 3 | 1/8 |
| `wordpress-mobile__WordPress-Android-19424` | GPT-5.2 | 1/8 |
| `wordpress-mobile__WordPress-Android-19574` | GPT-5.2 | 1/8 |
| `wordpress-mobile__WordPress-Android-19730` | Opus 4.5 | 1/8 |
| `wordpress-mobile__WordPress-Android-20057` | GPT-5.2 | 1/8 |

## 4. Tool Usage Analysis

### Tool Calls by Model

| Model | Total Calls | Avg/Task | Top Tools |
|-------|-------------|----------|-----------|
| Opus 4.5 | 3360 | 33.6 | read:1194, run_terminal_cmd:662, grep:575 |
| Sonnet 4 | 3184 | 31.8 | read:963, grep:824, edit:644 |
| Sonnet 4.5 | 4674 | 46.7 | read:1301, run_terminal_cmd:1066, grep:793 |
| Gemini Flash 3 | 4572 | 45.7 | read:1390, run_terminal_cmd:896, grep:749 |
| Gemini Pro 3 | 2606 | 26.1 | read:771, run_terminal_cmd:563, edit:471 |
| GPT-5.2 | 3576 | 35.8 | read:1229, grep:958, edit:593 |
| GLM-4.7 | 1462 | 14.6 | read:675, grep:372, edit:125 |
| GLM-4.7-FP8 | 1703 | 17.0 | read:638, grep:476, edit:214 |

### IntelliJ Semantic Tools Usage

| Model | read_lints | go_to_def | find_usages | rename | delete | Total |
|-------|------------|-----------|-------------|--------|--------|-------|
| Opus 4.5 | 193 | 9 | 23 | 0 | 4 | 229 |
| Sonnet 4 | 347 | 13 | 20 | 0 | 3 | 383 |
| Sonnet 4.5 | 302 | 3 | 19 | 0 | 11 | 335 |
| Gemini Flash 3 | 84 | 48 | 57 | 1 | 5 | 195 |
| Gemini Pro 3 | 65 | 27 | 25 | 0 | 0 | 117 |
| GPT-5.2 | 233 | 27 | 5 | 1 | 4 | 270 |
| GLM-4.7 | 64 | 0 | 4 | 0 | 0 | 68 |
| GLM-4.7-FP8 | 140 | 3 | 2 | 0 | 0 | 145 |

### Tool-Success Correlation Patterns

*Comparing avg tool usage between passing and failing attempts on the same task.*

*Negative correlation = tool used MORE when failing (struggling models explore more)*

| Tool | Correlation | Tasks | Insight |
|------|-------------|-------|---------|
| run_terminal_cmd | -0.035 | 100 | Similar usage |
| delete_file | -0.106 | 80 | Slightly more when failing |
| edit | -0.136 | 100 | Slightly more when failing |
| write | -0.158 | 91 | Slightly more when failing |
| read_lints | -0.186 | 100 | Slightly more when failing |
| list_dir | -0.194 | 100 | Slightly more when failing |
| read | -0.213 | 100 | Overused when struggling |
| grep | -0.247 | 100 | Overused when struggling |
| delete_symbol | -0.262 | 9 | Overused when struggling |
| glob | -0.307 | 97 | Overused when struggling |
| go_to_definition | -0.316 | 53 | Overused when struggling |
| find_usages | -0.336 | 54 | Overused when struggling |

### High Tool-Variance Tasks

*Tasks where models used very different numbers of tools*

| Task | Min Tools | Max Tools | Std Dev | Pass/Fail |
|------|-----------|-----------|---------|-----------|
| `ankidroid__Anki-Android-14738` | 0 | 129 | 55.0 | 2/8 |
| `wordpress-mobile__WordPress-Android-1942...` | 0 | 138 | 52.1 | 1/8 |
| `pinterest__ktlint-2068` | 0 | 131 | 41.1 | 0/8 |
| `wordpress-mobile__WordPress-Android-1984...` | 0 | 122 | 38.1 | 0/8 |
| `thunderbird__thunderbird-android-8267` | 6 | 119 | 37.6 | 0/8 |
| `pinterest__ktlint-1923` | 0 | 95 | 34.1 | 5/8 |
| `thunderbird__thunderbird-android-8889` | 0 | 105 | 32.3 | 0/8 |
| `ankidroid__Anki-Android-15141` | 10 | 96 | 30.7 | 2/8 |
| `ankidroid__Anki-Android-16400` | 4 | 80 | 30.5 | 0/8 |
| `wordpress-mobile__WordPress-Android-2005...` | 0 | 107 | 30.1 | 1/8 |

### Example: Per-Task Tool Comparison

*Detailed tool usage for select high-variance tasks*

**ankidroid__Anki-Android-14738** (2/8 passed)

| Model | Tools Used | Passed | Top Tools |
|-------|------------|--------|-----------|
| Opus 4.5 | 114 | Yes | run_terminal_cmd:49, read:32, grep:15 |
| GPT-5.2 | 129 | Yes | read:40, grep:40, edit:18 |
| Gemini Pro 3 | 0 | No |  |
| Sonnet 4 | 0 | No |  |
| GLM-4.7 | 10 | No | read:7, grep:2, glob:1 |
| Sonnet 4.5 | 81 | No | read:35, grep:22, edit:14 |
| Gemini Flash 3 | 100 | No | read:31, grep:26, edit:23 |
| GLM-4.7-FP8 | 107 | No | grep:45, read:33, edit:12 |

**wordpress-mobile__WordPress-Android-19424** (1/8 passed)

| Model | Tools Used | Passed | Top Tools |
|-------|------------|--------|-----------|
| GPT-5.2 | 67 | Yes | edit:29, read:18, grep:16 |
| GLM-4.7-FP8 | 0 | No |  |
| GLM-4.7 | 8 | No | read:8 |
| Gemini Pro 3 | 10 | No | read:6, list_dir:3, grep:1 |
| Gemini Flash 3 | 83 | No | edit:28, read:19, grep:18 |
| Sonnet 4 | 88 | No | read:31, grep:22, edit:18 |
| Opus 4.5 | 113 | No | edit:35, read:32, grep:26 |
| Sonnet 4.5 | 138 | No | grep:39, read:28, run_terminal_cmd:28 |

**pinterest__ktlint-1923** (5/8 passed)

| Model | Tools Used | Passed | Top Tools |
|-------|------------|--------|-----------|
| Gemini Flash 3 | 34 | Yes | run_terminal_cmd:10, edit:10, read:7 |
| Gemini Pro 3 | 39 | Yes | edit:16, run_terminal_cmd:13, read:7 |
| GPT-5.2 | 40 | Yes | read:11, run_terminal_cmd:8, grep:6 |
| Sonnet 4.5 | 87 | Yes | run_terminal_cmd:28, edit:16, read:13 |
| Opus 4.5 | 95 | Yes | run_terminal_cmd:33, edit:23, read:17 |
| GLM-4.7-FP8 | 0 | No |  |
| Sonnet 4 | 14 | No | read:4, edit:4, read_lints:2 |
| GLM-4.7 | 16 | No | read:5, glob:4, list_dir:2 |

## 5. Linter Tool Analysis

### read_lints Effectiveness

| Model | Total Calls | Empty (no errors) | Productive (found errors) | Empty Rate |
|-------|-------------|-------------------|---------------------------|------------|
| Opus 4.5 | 193 | 183 | 10 | 95% |
| Sonnet 4 | 347 | 298 | 49 | 86% |
| Sonnet 4.5 | 302 | 288 | 14 | 95% |
| Gemini Flash 3 | 84 | 78 | 5 | 93% |
| Gemini Pro 3 | 65 | 63 | 2 | 97% |
| GPT-5.2 | 233 | 217 | 15 | 93% |
| GLM-4.7 | 64 | 57 | 7 | 89% |
| GLM-4.7-FP8 | 140 | 124 | 14 | 89% |

## 6. Conversation Metrics

### Average Metrics by Model

| Model | Avg Messages | Avg Turns | Avg Input Tokens | Avg Output Tokens |
|-------|--------------|-----------|------------------|-------------------|
| Opus 4.5 | 63 | 29 | 34968 | 8785 |
| Sonnet 4 | 66 | 33 | 22385 | 6843 |
| Sonnet 4.5 | 91 | 44 | 31948 | 11537 |
| Gemini Flash 3 | 93 | 46 | 53381 | 4687 |
| Gemini Pro 3 | 53 | 26 | 38456 | 2943 |
| GPT-5.2 | 66 | 29 | 34276 | 6128 |
| GLM-4.7 | 27 | 11 | 18902 | 1703 |
| GLM-4.7-FP8 | 32 | 14 | 15270 | 1970 |

## 7. Code Change Metrics

### Patch Size by Model

| Model | Avg Lines Added | Avg Lines Removed | Avg Files Changed |
|-------|-----------------|-------------------|-------------------|
| Opus 4.5 | 89.8 | 24.0 | 4.4 |
| Sonnet 4 | 96.7 | 18.3 | 4.5 |
| Sonnet 4.5 | 155.7 | 18.8 | 5.6 |
| Gemini Flash 3 | 60.3 | 21.3 | 5.4 |
| Gemini Pro 3 | 47.0 | 14.8 | 3.0 |
| GPT-5.2 | 65.3 | 17.1 | 4.0 |
| GLM-4.7 | 17.5 | 7.7 | 2.0 |
| GLM-4.7-FP8 | 26.8 | 8.7 | 2.2 |

### Patch Size: Pass vs Fail

| Model | Avg Lines (Pass) | Avg Lines (Fail) |
|-------|------------------|------------------|
| Opus 4.5 | 92.2 | 132.3 |
| Sonnet 4 | 70.3 | 133.2 |
| Sonnet 4.5 | 161.5 | 182.2 |
| Gemini Flash 3 | 81.2 | 81.8 |
| Gemini Pro 3 | 56.1 | 65.8 |
| GPT-5.2 | 61.1 | 98.4 |
| GLM-4.7 | 48.8 | 21.7 |
| GLM-4.7-FP8 | 43.1 | 34.2 |

## 8. Cost Analysis

*Cost estimates include prompt caching: cached input tokens priced at 10-25% of normal input rate*

### Cost by Model

| Model | Total Cost | Avg/Task | Cost/Success | Cache Hit Rate |
|-------|------------|----------|--------------|----------------|
| Opus 4.5 | $26.15 | $0.26 | $0.57 | 84% |
| Sonnet 4 | $11.86 | $0.12 | $0.41 | 85% |
| Sonnet 4.5 | $19.59 | $0.20 | $0.53 | 85% |
| Gemini Flash 3 | $2.04 | $0.02 | $0.05 | 85% |
| Gemini Pro 3 | $5.44 | $0.05 | $0.13 | 84% |
| GPT-5.2 | $10.01 | $0.10 | $0.23 | 85% |
| GLM-4.7 | $1.12 | $0.01 | $0.09 | 68% |
| GLM-4.7-FP8 | $0.97 | $0.01 | $0.06 | 82% |

### Token Breakdown by Model

| Model | Total Input | Cached | Uncached | Output |
|-------|-------------|--------|----------|--------|
| Opus 4.5 | 3,496,782 | 2,955,738 | 541,044 | 878,522 |
| Sonnet 4 | 2,238,493 | 1,895,112 | 343,381 | 684,262 |
| Sonnet 4.5 | 3,194,813 | 2,704,569 | 490,244 | 1,153,685 |
| Gemini Flash 3 | 5,338,076 | 4,533,038 | 805,038 | 468,666 |
| Gemini Pro 3 | 3,845,602 | 3,210,600 | 635,002 | 294,292 |
| GPT-5.2 | 3,427,566 | 2,899,042 | 528,524 | 612,837 |
| GLM-4.7 | 1,890,206 | 1,285,247 | 604,959 | 170,337 |
| GLM-4.7-FP8 | 1,527,022 | 1,252,681 | 274,341 | 196,977 |

### Cost per Success Rankings

*Lower is better - cost to achieve one successful task*

| Rank | Model | Cost/Success |
|------|-------|--------------|
| 1 | Gemini Flash 3 | $0.05 |
| 2 | GLM-4.7-FP8 | $0.06 |
| 3 | GLM-4.7 | $0.09 |
| 4 | Gemini Pro 3 | $0.13 |
| 5 | GPT-5.2 | $0.23 |
| 6 | Sonnet 4 | $0.41 |
| 7 | Sonnet 4.5 | $0.53 |
| 8 | Opus 4.5 | $0.57 |

## Appendix: Unsolved Tasks

The following 38 tasks were not solved by any model:

- `Kotlin__kotlinx-datetime-360`
- `Kotlin__kotlinx-datetime-367`
- `Kotlin__kotlinx.coroutines-3719`
- `Kotlin__kotlinx.coroutines-3731`
- `ankidroid__Anki-Android-14182`
- `ankidroid__Anki-Android-14360`
- `ankidroid__Anki-Android-14388`
- `ankidroid__Anki-Android-14652`
- `ankidroid__Anki-Android-14769`
- `ankidroid__Anki-Android-15557`
- `ankidroid__Anki-Android-16400`
- `ankidroid__Anki-Android-17125`
- `ankidroid__Anki-Android-17867`
- `pinterest__ktlint-1766`
- `pinterest__ktlint-1849`
- `pinterest__ktlint-1853`
- `pinterest__ktlint-1920`
- `pinterest__ktlint-1944`
- `pinterest__ktlint-1997`
- `pinterest__ktlint-2060`
- ... and 18 more
