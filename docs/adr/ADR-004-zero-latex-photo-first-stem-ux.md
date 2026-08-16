# ADR 004: Zero-LaTeX Photo-First STEM User Experience

## Status
Accepted

## Context
Requiring high school students to type algebraic formulas or chemical equations using raw LaTeX syntax (`\frac{-b \pm \sqrt{\Delta}}{2a}`) creates a severe usability barrier. Students solve mathematical and physical tasks with pen and paper.

## Decision
The STEM Workspace (Mathematics, Physics, Chemistry) implements a **Photo-First workflow**. Students work in their paper notebooks and paste images/screenshots directly into the app (`Ctrl + V`, Drag & Drop, or File Upload). Multimodal Vision LLMs perform OCR, line-by-line step transcription, and algebraic verification. For quick text entry, a clickable visual palette provides intuitive math symbols without requiring LaTeX knowledge.

## Consequences
### Positive
* Natural, friction-free student experience mirroring real exam conditions.
* Eliminates the LaTeX learning curve.
* Direct compatibility with the Windows Snipping Tool (`Win + Shift + S` -> `Ctrl + V`).

### Negative / Trade-offs
* Requires a multimodal vision-capable model (e.g., `gpt-4o`, `gemini-1.5-flash`, `llama-3.2-11b-vision`).