# tools/cli_summarize.py
import argparse, os, requests, pathlib, sys # Import sys for stderr

API = os.environ.get("API_BASE", "http://127.0.0.1:8000")
INFER = [".txt", ".md", ".csv", ".json", ".py", ".log"]

def summarize(path, outdir):
    print(f"Processing: {path} ...", file=sys.stderr) # Added progress indicator
    try:
        with open(path, "rb") as f:
            r = requests.post(f"{API}/api/summarize", files={"file": (os.path.basename(path), f)})
        r.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        # Check if response is JSON and contains 'summary'
        try:
            response_json = r.json()
            summary_text = response_json.get("summary", "")
            if not summary_text:
                print(f"Warning: API returned success but no 'summary' field for {path}. Response: {response_json}", file=sys.stderr)
        except requests.exceptions.JSONDecodeError:
            print(f"Error: API did not return valid JSON for {path}. Response text: {r.text}", file=sys.stderr)
            return # Skip writing if JSON is invalid

        outpath = os.path.join(outdir, os.path.basename(path) + ".summary.txt")
        pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)
        with open(outpath, "w", encoding="utf-8") as w:
            w.write(summary_text)
        print(f"Summarized to: {outpath}", file=sys.stderr)

    except requests.exceptions.RequestException as e: # Catching connection errors, timeouts, etc.
        print(f"Error processing {path}: API request failed - {e}", file=sys.stderr)
    except FileNotFoundError:
        print(f"Error: Input file not found at {path}", file=sys.stderr)
    except Exception as e: # Catch any other unexpected errors
        print(f"An unexpected error occurred while processing {path}: {e}", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="Summarize files using a remote API.")
    p.add_argument("--in", dest="inp", required=True, help="Input file path or directory.")
    p.add_argument("--out", dest="out", default="out", help="Output directory for summaries (default: 'out').")
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
