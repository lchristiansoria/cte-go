from ctg_go.db.models import import_models
from ctg_go.seed.synthetic import seed_synthetic_data


def main() -> None:
    import_models()
    seed_synthetic_data()


if __name__ == "__main__":
    main()
