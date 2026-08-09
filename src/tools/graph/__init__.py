"""Graph extraction tools for P&ID and engineering diagram processing [BLK-110].

Tools:
- detect_symbols: VLM-based symbol detection
- classify_symbol: VLM-based symbol classification
- detect_connections: VLM + OpenCV connection detection
- trace_line: OpenCV line tracing
- read_tag: OCR + ISA-5.1 tag parsing
- build_graph: deterministic graph construction
- validate_topology: deterministic topology validation
- serialize_graph: multi-format graph serialization
"""
