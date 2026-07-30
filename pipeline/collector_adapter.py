from pathlib import Path
import subprocess

BASE_DIR = Path(__file__).resolve().parent.parent


class CollectorAdapter:

    def __init__(self):
        self.collectors = []

    def register(self, name, script):

        self.collectors.append({
            "name": name,
            "script": BASE_DIR / script
        })

    def run(self):

        results = []

        for collector in self.collectors:

            print(f"\nRunning {collector['name']}...")

            result = subprocess.run(
                ["python", str(collector["script"])],
                capture_output=True,
                text=True,
                cwd=BASE_DIR
            )

            results.append(result)

            print(result.stdout)

            if result.returncode != 0:
                print(result.stderr)

        return results