<p align="center">
  <span style="display: inline-flex; align-items: center; justify-content: center;">
    <span style="font-size: 2.5em; font-weight: bold; margin-right: 15px;">Kotlin-Bench</span>
    <img src="firebender-logo.svg" width="50px" alt="Firebender Logo" />
  </span>
</p>

## 📰 News
* **[Apr. 3, 2025]**: Firebender introduces Kotlin Bench. Read the [blog post](https://firebender.com/blog/kotlin-bench).

## 👋 Overview

Kotlin-Bench is a spinoff of [SWE-Bench](https://www.swebench.com/) and is the first benchmark that evaluates Large Language Models (LLMs) and AI agents on 100 real-world Kotlin and Android software engineering tasks.

Given a *codebase* and an *issue*, a language model is tasked with generating a *patch* that resolves the described problem.

<img src="assets/teaser.png">

## 🚀 Set Up
To build Kotlin-Bench from source, follow these steps:
1. Clone this repository locally
2. `cd` into the repository.
3. Run `pipenv shell` to created a Python environment
4. Install dependencies `pip install -r requirements.txt`

## 💽 Usage
You can download the SWE-bench dataset directly from [HuggingFace](https://huggingface.co/datasets/princeton-nlp/SWE-bench).

To use Kotlin-Bench, you can:
*  Run Kotlin-Bench's [data collection procedure](tutorials/collection.md) on your own repositories, to make new Kotlin-Bench tasks. 
* [Evaluate](tutorials/evaluation.md) models against Kotlin-Bench. This is where you take a Kotlin-Bench task and a model-proposed solution and evaluate its correctness. 

## ⬇️ Downloads
| Datasets
| - 
| [🤗 Kotlin-Bench](https://huggingface.co/datasets/firebenders/Kotlin-Bench)
| [🤗 Kotlin-Bench w/ Full file rewrite + "Oracle" Retrieval Context](https://huggingface.co/datasets/firebenders/Kotlin-Bench__full_file_gen__fs-oracle)
| [🤗 Kotlin-Bench w/ Patch diff + "Oracle" Retrieval Context](https://huggingface.co/datasets/firebenders/Kotlin-Bench__style-3__fs-oracle)

## 💫 Contributions
We would love to hear from the Kotlin & Android community interested in contributing!

Join our [Discord](https://discord.gg/WB4VnjR4RA) community for fast responses.

Feel free to email me directly at aman@firebender.com

## Citations
```
@inproceedings{
    jimenez2024swebench,
    title={{SWE}-bench: Can Language Models Resolve Real-world Github Issues?},
    author={Carlos E Jimenez and John Yang and Alexander Wettig and Shunyu Yao and Kexin Pei and Ofir Press and Karthik R Narasimhan},
    booktitle={The Twelfth International Conference on Learning Representations},
    year={2024},
    url={https://openreview.net/forum?id=VTF8yNQM66}
}
```

## 🪪 License
MIT. Check `LICENSE.md`.
