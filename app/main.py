from app.core.env import require_env


def main() -> None:
    print(f"Running {require_env('APP_NAME')}")


if __name__ == "__main__":
    main()