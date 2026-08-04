import os
import glob

directory = 'd:/Zepto_Delhi_inventory'
extensions = ['*.sql', '*.py', '*.ps1']
files_to_check = []

for ext in extensions:
    files_to_check.extend(glob.glob(os.path.join(directory, '**', ext), recursive=True))

for file_path in files_to_check:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'zepto_inventory' in content and 'zepto_inventory' not in content:
            new_content = content.replace('zepto_inventory', 'zepto_inventory')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated: {file_path}")
    except Exception as e:
        pass
print("Done renaming database.")
