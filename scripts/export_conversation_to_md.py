#!/usr/bin/env python3
"""
Conversation History Exporter
Extracts the complete chronological conversation history from transcript_full.jsonl
into a beautifully formatted, structured, and comprehensive Markdown (.md) document.
"""

import json
import os
import re
from datetime import datetime

TRANSCRIPT_PATH = r"C:\Users\Harshith\.gemini\antigravity-ide\brain\78ada1e9-fe64-4b38-9784-da3bfbfc6233\.system_generated\logs\transcript_full.jsonl"
OUT_MD_ROOT = r"c:\Users\Harshith\OneDrive\Desktop\major_project_py\CONVERSATION_HISTORY.md"
OUT_MD_DOCS = r"c:\Users\Harshith\OneDrive\Desktop\major_project_py\zeroeth review\docs\CONVERSATION_HISTORY.md"


def clean_user_prompt(raw_content: str) -> str:
    """Extract clean user prompt from raw content containing XML tags."""
    if not raw_content:
        return ""
    # Extract <USER_REQUEST>...</USER_REQUEST> if present
    match = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw_content, re.DOTALL)
    if match:
        prompt = match.group(1).strip()
    else:
        # Fallback: remove <ADDITIONAL_METADATA>...</ADDITIONAL_METADATA>
        cleaned = re.sub(r"<ADDITIONAL_METADATA>.*?</ADDITIONAL_METADATA>", "", raw_content, flags=re.DOTALL)
        cleaned = re.sub(r"<USER_SETTINGS_CHANGE>.*?</USER_SETTINGS_CHANGE>", "", cleaned, flags=re.DOTALL)
        prompt = cleaned.strip()
    return prompt


def format_timestamp(ts_str: str) -> str:
    """Formats ISO timestamp string to readable format."""
    if not ts_str:
        return ""
    try:
        # Handle '2026-08-11T14:12:18Z' or with offset
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts_str


def parse_transcript(transcript_path: str):
    """Parses transcript entries into structured conversation turns."""
    with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
        entries = [json.loads(line) for line in f]

    user_indices = [i for i, e in enumerate(entries) if e.get("type") == "USER_INPUT"]
    turns = []

    for i, u_idx in enumerate(user_indices):
        next_u_idx = user_indices[i + 1] if i + 1 < len(user_indices) else len(entries)
        turn_entries = entries[u_idx:next_u_idx]

        user_entry = turn_entries[0]
        user_ts = user_entry.get("created_at", "")
        raw_user_content = user_entry.get("content", "")
        user_prompt = clean_user_prompt(raw_user_content)

        assistant_replies = []
        tool_summaries = []

        for e in turn_entries[1:]:
            etype = e.get("type")
            content = e.get("content", "")
            ts = e.get("created_at", "")

            # Capture tool calls
            tool_calls = e.get("tool_calls", [])
            for tc in tool_calls:
                if isinstance(tc, dict):
                    fname = tc.get("function", {}).get("name") or tc.get("tool_name") or tc.get("name")
                    args = tc.get("function", {}).get("arguments") or tc.get("args") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            pass
                    summary = tc.get("toolSummary") or tc.get("toolAction")
                    if summary:
                        tool_summaries.append(f"`{fname}`: {summary}")
                    elif fname:
                        # Extract key argument if available
                        detail = ""
                        if isinstance(args, dict):
                            if "CommandLine" in args:
                                cmd = args["CommandLine"]
                                detail = f" ({cmd[:50]}...)" if len(cmd) > 50 else f" ({cmd})"
                            elif "TargetFile" in args:
                                tf = os.path.basename(args["TargetFile"])
                                detail = f" ({tf})"
                            elif "AbsolutePath" in args:
                                ap = os.path.basename(args["AbsolutePath"])
                                detail = f" ({ap})"
                        tool_summaries.append(f"`{fname}`{detail}")

            # Capture assistant substantive text response
            if etype == "PLANNER_RESPONSE" and content and content.strip():
                assistant_replies.append({
                    "timestamp": ts,
                    "content": content.strip()
                })

        turns.append({
            "turn_number": i + 1,
            "timestamp": format_timestamp(user_ts),
            "user_prompt": user_prompt,
            "tools": tool_summaries,
            "assistant_replies": assistant_replies
        })

    return turns


def generate_markdown(turns, output_file: str):
    """Generates a complete, beautiful markdown document from turns."""
    md_lines = []
    
    # Document Header
    md_lines.append("# AstroFlyer HEO — Complete Engineering Conversation History")
    md_lines.append("")
    md_lines.append("> **Project:** Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)")  
    md_lines.append("> **Institution:** ACS College of Engineering, Dept. of Aerospace Engineering (Affiliated to VTU, Belagavi)")  
    md_lines.append("> **Candidates:** Girish Gowda S (`1AH23AS019`), Gowtham N (`1AH23AS020`), Harshith S Purohith (`1AH23AS021`)")  
    md_lines.append(f"> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | **Total Conversation Turns:** {len(turns)}")  
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # Table of Contents
    md_lines.append("## Table of Contents")
    md_lines.append("")
    for t in turns:
        tnum = t["turn_number"]
        prompt_snippet = t["user_prompt"].split("\n")[0].strip()
        # Clean special chars for TOC link
        clean_snippet = re.sub(r"[`*_{}\[\]()#+\-.!]", "", prompt_snippet)
        clean_snippet = clean_snippet[:70] + ("..." if len(clean_snippet) > 70 else "")
        if not clean_snippet:
            clean_snippet = f"Turn {tnum}"
        anchor = f"turn-{tnum}"
        md_lines.append(f"- [Turn {tnum}: {clean_snippet}](#{anchor})")
    
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    # Turn-by-Turn Dialogue
    for t in turns:
        tnum = t["turn_number"]
        ts = t["timestamp"]
        prompt = t["user_prompt"]
        tools = t["tools"]
        replies = t["assistant_replies"]

        md_lines.append(f"## <a id=\"turn-{tnum}\"></a>Turn {tnum} — User Request")
        if ts:
            md_lines.append(f"*Timestamp: {ts}*")
        md_lines.append("")

        # User Request Block
        md_lines.append("### 👤 User")
        md_lines.append("")
        md_lines.append("```text")
        md_lines.append(prompt if prompt else "(No text content)")
        md_lines.append("```")
        md_lines.append("")

        # Tools executed summary (if any)
        if tools:
            # Deduplicate or group tool summaries
            dedup_tools = []
            seen = set()
            for tool in tools:
                if tool not in seen:
                    seen.add(tool)
                    dedup_tools.append(tool)
            
            md_lines.append("<details>")
            md_lines.append(f"<summary>🛠️ <b>System Execution & Tool Actions ({len(tools)} operations)</b></summary>")
            md_lines.append("")
            for tool_str in dedup_tools[:25]:
                md_lines.append(f"- {tool_str}")
            if len(dedup_tools) > 25:
                md_lines.append(f"- *... and {len(dedup_tools) - 25} more operations*")
            md_lines.append("")
            md_lines.append("</details>")
            md_lines.append("")

        # Assistant Response Block
        md_lines.append("### 🤖 Assistant (Antigravity AI)")
        md_lines.append("")
        if replies:
            for r_idx, rep in enumerate(replies):
                content = rep["content"]
                if len(replies) > 1:
                    md_lines.append(f"#### Response Part {r_idx + 1}")
                    md_lines.append("")
                md_lines.append(content)
                md_lines.append("")
        else:
            md_lines.append("*(Tool execution and automated background processing completed with no direct textual response)*")
            md_lines.append("")

        md_lines.append("---")
        md_lines.append("")

    full_text = "\n".join(md_lines)
    
    # Write to primary target
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"[+] Successfully wrote conversation history to: {output_file} ({len(full_text):,} bytes)")

    return full_text


def main():
    print(f"[*] Parsing transcript from: {TRANSCRIPT_PATH}")
    turns = parse_transcript(TRANSCRIPT_PATH)
    print(f"[*] Extracted {len(turns)} conversation turns.")
    
    # Generate root markdown
    print(f"[*] Writing Root Markdown to: {OUT_MD_ROOT}")
    full_text = generate_markdown(turns, OUT_MD_ROOT)
    
    # Generate docs copy
    print(f"[*] Writing Docs Markdown to: {OUT_MD_DOCS}")
    os.makedirs(os.path.dirname(os.path.abspath(OUT_MD_DOCS)), exist_ok=True)
    with open(OUT_MD_DOCS, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"[+] Successfully wrote docs copy to: {OUT_MD_DOCS}")
    print("[*] Complete conversation export finished!")


if __name__ == "__main__":
    main()
