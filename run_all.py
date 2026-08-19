# import subprocess
# import sys

# scripts = {
#     'a' : "C:/Users/pavan/Documents/Python/Marketbot/analytics/factor_builder.py",
#     'b' : "C:/Users/pavan/Documents/Python/Marketbot/research/forward_returns.py",
#     # "earning.weight_optimizer"
# }

# for script in scripts:
#     print("/n" + "=" * 70)
#     print(f"RUNNING: {script}")
#     print("=" * 70)

#     result = subprocess.run(
#         [sys.executable, script],
#         capture_output=False
#     )

#     # if result.returncode != 0:
#     #     print(f"/nFAILED: {script}")
#     #     sys.exit(result.returncode)

# print("/n" + "=" * 70)
# print("ALL SCRIPTS COMPLETED SUCCESSFULLY")
# print("=" * 70)







import subprocess
import sys

scripts = [
    "analytics/factor_builder.py",
    "C:/Users/pavan/Documents/Python/Marketbot/research/forward_returns.py",
    # "earning.weight_optimizer"
]

for v in scripts:
    print("/n" + "=" * 70)
    print(f"RUNNING: {v}")
    print("=" * 70)

    result = subprocess.run(
        [sys.executable, v],
        capture_output=False
    )

    if result.returncode != 0:
        print(f"/nFAILED: {v}")
        sys.exit(result.returncode)

print("/n" + "=" * 70)
print("ALL SCRIPTS COMPLETED SUCCESSFULLY")
print("=" * 70)