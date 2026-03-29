#!/bin/bash

# =============================================
# Export full GSoC Learning Space codebase
# =============================================

OUTPUT_FILE="codebase_context.txt"

echo "Starting export of GSoC Learning Space codebase..."
echo "Output will be saved to: $OUTPUT_FILE"

# Remove old file if exists
[ -f "$OUTPUT_FILE" ] && rm "$OUTPUT_FILE"

# Header
cat > "$OUTPUT_FILE" << 'HEADER'
================================================================================
GSoC 2026 - MESA META AGENTS LEARNING SPACE
Full Codebase Context
================================================================================
Generated on: $(date)
Project Root: $(pwd)

This file contains the complete source code and documentation 
for review and context.

================================================================================

HEADER

echo "Collecting files..."

# Root files
echo -e "\n=== ROOT FILES ===" >> "$OUTPUT_FILE"
for file in README.md motivation.md LICENSE *.sh; do
    if [ -f "$file" ]; then
        echo -e "\n================================================================================\nFILE: $file\n================================================================================" >> "$OUTPUT_FILE"
        echo "=== BEGIN FILE ===" >> "$OUTPUT_FILE"
        cat "$file" >> "$OUTPUT_FILE"
        echo -e "\n=== END FILE ===\n" >> "$OUTPUT_FILE"
        echo "  → Added: $file"
    fi
done

# Docs
echo -e "\n=== DOCS ===" >> "$OUTPUT_FILE"
find docs -type f -name "*.md" | sort | while read -r file; do
    rel="${file#./}"
    echo -e "\n================================================================================\nFILE: $rel\n================================================================================" >> "$OUTPUT_FILE"
    echo "=== BEGIN FILE ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n=== END FILE ===\n" >> "$OUTPUT_FILE"
    echo "  → Added: $rel"
done

# mesa_llm_poc
echo -e "\n=== MESA_LLM_POC ===" >> "$OUTPUT_FILE"
find mesa_llm_poc -type f \( -name "*.py" -o -name "*.md" \) ! -path "*/__pycache__/*" | sort | while read -r file; do
    rel="${file#./}"
    echo -e "\n================================================================================\nFILE: $rel\n================================================================================" >> "$OUTPUT_FILE"
    echo "=== BEGIN FILE ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n=== END FILE ===\n" >> "$OUTPUT_FILE"
    echo "  → Added: $rel"
done

# All models (most important)
echo -e "\n=== MODELS ===" >> "$OUTPUT_FILE"
find models -type f \( -name "*.py" -o -name "*.md" \) ! -path "*/__pycache__/*" | sort | while read -r file; do
    rel="${file#./}"
    echo -e "\n================================================================================\nFILE: $rel\n================================================================================" >> "$OUTPUT_FILE"
    echo "=== BEGIN FILE ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n=== END FILE ===\n" >> "$OUTPUT_FILE"
    echo "  → Added: $rel"
done

# POC directory (your proposal core)
echo -e "\n=== POC (Proposal Core) ===" >> "$OUTPUT_FILE"
find poc -type f \( -name "*.py" -o -name "*.sh" \) ! -path "*/__pycache__/*" | sort | while read -r file; do
    rel="${file#./}"
    echo -e "\n================================================================================\nFILE: $rel\n================================================================================" >> "$OUTPUT_FILE"
    echo "=== BEGIN FILE ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n=== END FILE ===\n" >> "$OUTPUT_FILE"
    echo "  → Added: $rel"
done

# Final Summary
cat >> "$OUTPUT_FILE" << 'SUMMARY'

================================================================================
SUMMARY
================================================================================
Generated on: $(date)
Project root: $(pwd)

Python files : $(find . -name "*.py" ! -path "*/__pycache__/*" | wc -l)
Markdown files: $(find . -name "*.md" | wc -l)
Shell scripts : $(find . -name "*.sh" | wc -l)

Focus areas:
- models/meta_agents_proposal/ and poc/proposal_core/  → Core MetaAgentV2 + LLM + Spatial
- models/financial_market_coalition/                   → Main integration example
- models/llm_evaluation_demo/                          → Pillar 2 demo (currently failing)

Ready for code review and final report.
================================================================================
SUMMARY

echo "✅ Export completed successfully!"
echo "File created: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo "Total lines: $(wc -l < "$OUTPUT_FILE")"
echo ""
echo "View it with:"
echo "less $OUTPUT_FILE"
echo "or"
echo "code $OUTPUT_FILE"
