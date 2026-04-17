"""
多层 LLM 流水线：classifier → source_digest → experts → editor

替代原 llm_analyzer 的单次大 prompt，解决深度不足问题。
每一层专注单一职责，结构化 JSON 在层间传递。
"""
