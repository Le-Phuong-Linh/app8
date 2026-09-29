import streamlit as st
import os
import re
import math
from pathlib import Path
import shutil

# =====================================================
# STREAMLIT UI CONFIGURATION
# =====================================================
st.set_page_config(page_title="Text Chapter Splitter & Renamer", page_icon="✂️", layout="centered")

st.title("✂️ Text Chapter Splitter & Renamer")
st.write("Upload your chapter text files, configure the maximum character size per part, and split/rename them automatically.")

# =====================================================
# SIDEBAR CONFIGURATION
# =====================================================
st.sidebar.header("Configuration")
max_chars = st.sidebar.slider("Max Characters per Part", 500, 5000, 2000, step=100)

# =====================================================
# FILE UPLOADER
# =====================================================
uploaded_files = st.file_uploader("Upload .txt chapter files", type=["txt"], accept_multiple_files=True)

# Regex patterns from original script
paragraph_splitter = re.compile(r'(?:\r?\n[\s ]*)+')
abstract_pattern = re.compile(r'(?:摘要|Abstract)[:：\s]?.*?(?=\n|$)', re.IGNORECASE)
filename_num_pattern = re.compile(r'(?:Глава|глава)\s*(\d+)(?:\.\s*(.*))?')
internal_chinese_num_pattern = re.compile(r'第\s*(\d+)\s*章')

def get_sort_key(filename):
    match = re.search(r'(?:Глава|глава)\s*(\d+)', filename)
    return int(match.group(1)) if match else 0

# =====================================================
# MAIN EXECUTION BUTTON
# =====================================================
if st.button("Process and Split Files"):
    if not uploaded_files:
        st.error("Please upload at least one chapter .txt file.")
    else:
        input_dir = Path("input")
        output_dir = Path("output")
        
        # Clean/recreate directories
        if input_dir.exists():
            shutil.rmtree(input_dir)
        if output_dir.exists():
            shutil.rmtree(output_dir)
            
        input_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)
        
        # Save uploaded files to input folder
        for uploaded_file in uploaded_files:
            file_path = input_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
        input_files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
        input_files.sort(key=get_sort_key)
        
        chapters_data = {}
        encoding = "utf-8"
        
        for filename in input_files:
            input_path = os.path.join(input_dir, filename)
            base_name_without_ext = os.path.splitext(filename)[0]
            name_match = filename_num_pattern.search(base_name_without_ext)
            fallback_title = name_match.group(2) if (name_match and name_match.group(2)) else ""

            try:
                with open(input_path, "r", encoding=encoding) as f:
                    text = f.read().strip()
            except Exception:
                with open(input_path, "r", encoding="latin-1") as f:
                    text = f.read().strip()

            if not text:
                continue

            text = abstract_pattern.sub('', text).strip()
            paragraphs = [p.strip() for p in paragraph_splitter.split(text) if p.strip()]
            if not paragraphs:
                continue

            internal_match = internal_chinese_num_pattern.search(text)
            if internal_match:
                ch_num = int(internal_match.group(1))
            elif name_match:
                ch_num = int(name_match.group(1))
            else:
                ch_num = 0

            if ch_num not in chapters_data:
                chapters_data[ch_num] = {"paragraphs": [], "title": fallback_title}
            
            for p in paragraphs:
                if p not in chapters_data[ch_num]["paragraphs"]:
                    chapters_data[ch_num]["paragraphs"].append(p)
                    
            if fallback_title and not chapters_data[ch_num]["title"]:
                chapters_data[ch_num]["title"] = fallback_title

        processed_count = 0
        for ch_num in sorted(chapters_data.keys()):
            chapter_paragraphs = chapters_data[ch_num]["paragraphs"]
            title_suffix = chapters_data[ch_num]["title"]
            
            title_str = f". {title_suffix}" if title_suffix else ""
            base_name = f"Глава {ch_num}{title_str}"
            
            total_length = sum(len(p) for p in chapter_paragraphs)
            if total_length == 0:
                continue

            parts_count = max(1, math.ceil(total_length / max_chars))
            equal_target = total_length / parts_count 

            parts = []
            current_part = []
            current_length = 0

            for p in chapter_paragraphs:
                p_len = len(p)
                
                if current_part and (current_length + p_len > equal_target):
                    overshoot_diff = (current_length + p_len) - equal_target
                    undershoot_diff = equal_target - current_length
                    
                    if (overshoot_diff > undershoot_diff) or (current_length + p_len > max_chars):
                        parts.append(current_part)
                        current_part = [p]
                        current_length = p_len
                        
                        remaining_parts = parts_count - len(parts)
                        if remaining_parts > 0:
                            remaining_len = total_length - sum(sum(len(para) for para in part) for part in parts)
                            equal_target = remaining_len / remaining_parts
                        continue

                current_part.append(p)
                current_length += p_len

            if current_part:
                parts.append(current_part)

            for part_idx, part in enumerate(parts, start=1):
                if len(parts) == 1:
                    output_filename = f"{base_name}.txt"
                else:
                    output_filename = f"{base_name}. Часть {part_idx}.txt"
                    
                output_path = os.path.join(output_dir, output_filename)
                
                with open(output_path, "w", encoding=encoding) as out:
                    out.write("\n\n".join(part) + "\n")
                processed_count += 1

        st.success(f"Successfully processed and split chapters into {processed_count} files!")

        # Create ZIP archive for downloading output files
        shutil.make_archive("split_chapters_output", "zip", output_dir)
        
        with open("split_chapters_output.zip", "rb") as fp:
            st.download_button(
                label="📦 Download Processed Files (ZIP)",
                data=fp,
                file_name="split_chapters.zip",
                mime="application/zip"
            )