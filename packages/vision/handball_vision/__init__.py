"""Computer vision for the handball pipeline (BRIEF 7.2 stages 2 to 5).

Every component implements a small interface so models can be swapped by configuration
(BRIEF 6.5). The default implementations are classical computer vision and are marked
`source="heuristic"`; learned models plug in through the ONNX detector.
"""

__version__ = "0.1.0"
