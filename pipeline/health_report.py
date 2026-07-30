def print_pipeline_summary(results):

    print("\n")

    print("=" * 70)

    print("PIPELINE SUMMARY")

    print("=" * 70)

    for result in results:

        if result["success"]:

            print(f"✅ {result['step']}")

        else:

            print(f"❌ {result['step']}")

            print(result["error"])

    print("=" * 70)