import subprocess, requests, psutil, json, os

print("Fetching models...")
try:
    req = requests.get("https://raw.githubusercontent.com/Ne00n/llama.get/refs/heads/master/models.json", timeout=(5,5))
    if req.status_code != 200: raise Exception(req.status_code)
    modelList = req.json()
except Exception as e:
    exit(f"Unable to fetch/load models.json: {e}")

mapping = {}
availableMemory = int(psutil.virtual_memory().total) / 1024 / 1024 / 1024
for category, dataset in modelList.items():
    print(f"Checking {category}")
    settings = {}
    for entry, rows in dataset.items():
        if entry == "settings": 
            settings = rows
            continue
        for model, data in rows.items():
            if data['min'] > availableMemory: continue
            splitted = model.split("/")
            print(f"Getting {splitted[1]} from {splitted[0]}")
            try:
                req = requests.get(f"https://huggingface.co/api/models/{model}/tree/main", timeout=(5,5))
                if req.status_code != 200: raise Exception(req.status_code)
                files = req.json()
            except Exception as e:
                print(f"Unable to fetch file list for model {splitted[1]}")
            targets = ["Q6_K.gguf","Q6_K_XL.gguf","Q4_K_XL.gguf","Q4_K_M.gguf"]
            solutions = {"gguf":"","ggufSize":0,"mmproj":"","mmprojSize":0}
            for file in files:
                size = int(file['size'] / 1024**3)
                if size >= availableMemory: continue
                for target in targets:
                    if target in file['path']:
                        if solutions['ggufSize'] < int(file['size']):
                            solutions["gguf"] = file['path']
                            solutions['ggufSize'] = int(file['size'])
                            mapping[file['path']] = settings
                        break
                if "mmproj" in file['path'] and solutions['mmprojSize'] < int(file['size']):
                    solutions["mmproj"] = file['path']
                    solutions['mmprojSize'] = int(file['size'])
            if solutions['gguf']:
                print(f"Fetching {solutions['gguf']}")
                result = subprocess.getoutput(f'hf download --include "{solutions['gguf']}" --local-dir models/ {model}')

config = """[*]
c = 64000
"""
print("Generating config.ini")
models = os.listdir(f"models/")
for model in models:
    if not model.endswith(".gguf"): continue
    for profile, settings in mapping[model].items():
        config += f"""
[{model.replace('.gguf','')}:{profile}]
model = models/{model}
"""
        for key, value in settings.items():
            config += f"{key} = {value}\n"

with open("config.ini", 'w') as file: file.write(config)
