"""Media processing: fetch, normalise, diarise, align.

Runs as an OFFLINE pass, before the language model is loaded. The RTX 3090 has
24 GB and Qwen Q4_K_XL already occupies ~19 GB, so audio models and the LLM
cannot sit in VRAM together. Batch preprocessing anyway -- not the hot path.
"""
