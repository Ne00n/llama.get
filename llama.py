import subprocess, requests, psutil, json, sys, os

def fetch(url):
    try:
        req = requests.get(url, timeout=(5,5))
        if req.status_code != 200: raise Exception(req.status_code)
        return req.json()
    except Exception as e:
        exit(f"Unable to fetch {url}: {e}")

print("Fetching models...")
modelList = fetch("https://raw.githubusercontent.com/Ne00n/llama.get/refs/heads/master/models.json")

wantedTags = []
for index, param in enumerate(sys.argv[1:]):
    if "--tags" in param:
        wantedTags = sys.argv[index +2].split(",")

mapping = {}
targets = ["Q6_K.gguf","Q6_K_XL.gguf","Q4_K_XL.gguf","Q4_K_M.gguf","UD-Q3_K_XL.gguf","IQ3_XXS.gguf",
           "APEX-I-Quality.gguf","APEX-I-Balanced.gguf","APEX-I-Compact.gguf","APEX-I-Mini.gguf"]
availableMemory = (int(psutil.virtual_memory().total) / 1024 / 1024 / 1024) - 2
for category, dataset in modelList.items():
    print(f"Checking {category}")
    settings = dataset['settings']
    for model, data in dataset['models'].items():
        if data['min'] > availableMemory: continue
        files = fetch(f"https://huggingface.co/api/models/{model}/tree/main")
        files = sorted(files, key=lambda item: item['size'], reverse=True)
        solutions = {"gguf":"","mmproj":""}
        for file in files:
            size = int(file['size'] / 1024**3)
            if size >= availableMemory: continue
            for target in targets:
                if target in file['path'] and not solutions['gguf']:
                    solutions["gguf"] = file['path']
                    break
            if "mmproj" in file['path'] and not solutions['mmproj']:
                solutions["mmproj"] = file['path']
                break
        modelTags = data['tags'].split(",")
        if solutions['gguf']:
            mapping[solutions['gguf']] = {"settings":settings,"mmproj":None}
            if not os.path.isfile(f"models/{solutions['gguf']}"):
                if wantedTags and not any(item in wantedTags for item in modelTags): continue
                print(f"Fetching {solutions['gguf']}")
                result = subprocess.getoutput(f'hf download --include "{solutions['gguf']}" --local-dir models/ {model}')
        if solutions['mmproj']:
            mmprojFile = solutions['gguf'].replace(".gguf",f"-{solutions['mmproj']}")
            mapping[solutions['gguf']]['mmproj'] = mmprojFile
            if not os.path.isfile(f"models/{mmprojFile}"):
                if wantedTags and not any(item in wantedTags for item in modelTags): continue
                print(f"Fetching {solutions['mmproj']}")
                result = subprocess.getoutput(f'hf download --include "{solutions['mmproj']}" --local-dir models/ {model}')
                os.rename(f"models/{solutions['mmproj']}",f"models/{mmprojFile}")

config = """[*]
c = 64000
"""
print("Generating config.ini")
models = os.listdir(f"models/")
for model in models:
    if not model.endswith(".gguf") or "mmproj" in model: continue
    if not model in mapping:
        print(f"{model} not in mapping! Skipping.")
        continue
    for profile, settings in mapping[model]['settings'].items():
        config += f"""
[{model.replace('.gguf','')}:{profile}]
model = models/{model}
"""
        if mapping[model]['mmproj']:
            config += f"mmproj = models/{mapping[model]['mmproj']}\n"
        if "Instruct" in profile:
            config += 'chat-template-kwargs = {"enable_thinking": false}\n'
        for key, value in settings.items():
            config += f"{key} = {value}\n"

with open("config.ini", 'w') as file: file.write(config)
