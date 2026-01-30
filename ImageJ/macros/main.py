import subprocess
from sys import platform
from pathlib import Path

current_dir = Path(__file__).parent.resolve()

fiji_path = current_dir.parent / "ImageJ-win64.exe"
fiji_path_mac = Path("/Users/pguerra/Library/CloudStorage/OneDrive-UniversityofNorthCarolinaatChapelHill/Desktop/Fiji")
script_path = current_dir / "macro_moj.py"
# input_dir = r"image_dir"
# output_dir = r"output_dir"

print(current_dir)
print(fiji_path)
print(fiji_path_mac)
print(script_path)

if platform == "win32":
    print("Windows detected")
    cmd = [
        fiji_path,
        # "--headless",
        "--console",
        "-macro", 
        script_path,
        # f"{input_dir}|{output_dir}"
    ]
elif platform == "darwin":  # macOS
    print("macOS detected")
    cmd = [
        fiji_path_mac,
        # "--headless",
        "--console",
        "-macro", 
        script_path,
        # f"{input_dir}|{output_dir}"
    ]

if __name__ == "__main__":
    subprocess.run(cmd, check=True)