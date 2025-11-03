# tools/cli_summarize.py
import argparse, os, requests, pathlib

API = os.environ.get("API_BASE", "http://127.0.0.1:8000")
INFER = [".txt", ".md", ".csv", ".json", ".py", ".log"]

def summarize(path, outdir):
    with open(path, "rb") as f:
        r = requests.post(f"{API}/api/summarize", files={"file": (os.path.basename(path), f)})
    r.raise_for_status()
    outpath = os.path.join(outdir, os.path.basename(path) + ".summary.txt")
    pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as w:
        w.write(r.json().get("summary", "")) 

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", dest="out", default="out")
    args = p.parse_args()
    pth = args.inp
    if os.path.isdir(pth):
        for root, _, files in os.walk(pth):
            for fn in files:
                if any(fn.lower().endswith(ext) for ext in INFER):
                    summarize(os.path.join(root, fn), args.out)
    else:
        summarize(pth, args.out)

if __name__ == "__main__":
    main()